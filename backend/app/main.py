import asyncio
import copy
import io
import os
import re
import secrets
import threading
from contextlib import asynccontextmanager, redirect_stdout
from typing import NamedTuple

import requests
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .fetch_stock_images import SINGLE_IMAGE_TEMPLATES, fetch_images
from .images import PEXELS_ACCESS_KEY, UNSPLASH_ACCESS_KEY, _is_reachable, is_allowed_image_url
from .models import Page
from .schemas import PageOut, PageSummary
from .seed_templates import resync_content, seed


def _revalidate_frontend() -> bool:
    """Nudges the frontend to drop its 1h page cache right after new stock
    photos are written, instead of leaving an already-cached page (fetched
    before the image existed) to keep showing its stale "no photo" snapshot
    until that cache entry naturally expires on its own schedule. Hits the
    frontend's own /admin-equivalent /api/revalidate endpoint, which is
    itself inert unless REVALIDATION_TOKEN is set there too -- so this is a
    freshness nudge, not something image fetching should ever depend on:
    any failure (missing token here, network error, frontend not
    configured) is swallowed rather than surfacing as an error to callers
    of fetch_images().

    Returns True if a request was actually sent (REVALIDATION_TOKEN is set
    on this service) -- not whether the frontend accepted it, since that
    would mean blocking on a cross-service network round trip that no
    caller here needs to wait on.
    """
    token = os.environ.get("REVALIDATION_TOKEN")
    if not token:
        return False
    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
    try:
        requests.get(f"{frontend_origin}/api/revalidate", params={"token": token}, timeout=10)
    except requests.RequestException as e:
        print(f"Frontend revalidation request failed: {e}")
    return True


# Holds a reference to the background image-fetch task for as long as the
# app is running -- asyncio only keeps a weak reference to a task created
# via create_task(), so a "fire and forget" task with nothing else holding
# it can get garbage-collected mid-run, silently killing the fetch partway
# through with no error anywhere. This set is that "something else."
_background_tasks: set[asyncio.Task] = set()


# How long to wait between backfill passes. Not tunable to "run constantly"
# -- fetch_images() already stops a single pass early the moment any
# provider rate-limits it (see fetch_stock_images.py's rate_limited
# short-circuit), so a pass that starts again immediately would just get
# rate-limited on its very first request again, uselessly. That
# short-circuit is exactly what makes a shorter interval safe to try
# rather than risky, though: a pass that starts before Pexels' window has
# actually recovered just fails fast on its first request and goes back to
# sleep, at negligible cost, rather than hammering an API that's still
# throttling it. Lowered from 3600 to 900 given the real backlog (~1,000
# pages, one hour between attempts) was visibly too slow -- still purely a
# guess at Pexels' real window (never confirmed, see fetch_stock_images.py
# for the same admission), just a less conservative one now that there's a
# cheap way to find out if it's wrong. Configurable via env var for the
# same reason.
IMAGE_FETCH_INTERVAL_SECONDS = int(os.environ.get("IMAGE_FETCH_INTERVAL_SECONDS", 900))


async def _run_periodic_image_fetch() -> None:
    """Backfills real stock photos for any page still missing one, on a
    recurring schedule, off the request-serving path -- see lifespan()'s
    docstring for why this runs as a background task instead of inline at
    startup, and CONCURRENCY's docstring in fetch_stock_images.py for the
    real incident behind starting conservative on concurrency.

    Used to run exactly once, at startup, which meant fully backfilling a
    large backlog (Pexels' rate limit only allows a small batch through
    per pass) needed a human to keep manually hitting /admin/fetch-images
    every so often -- not a real process. This loops for as long as the
    app process is alive instead, sleeping IMAGE_FETCH_INTERVAL_SECONDS
    between passes so each new pass gets a real shot at a recovered rate
    limit rather than immediately re-hitting the same wall. Each pass is
    cheap for pages that already have an image (a plain dict check, no
    network call -- see fetch_images()'s _needs_fetch), so a pass that
    finds nothing new to do finishes fast, not on a timer of its own.

    fetch_images() is synchronous (blocking `requests` calls) so each pass
    runs in a worker thread via asyncio.to_thread rather than blocking the
    event loop that's also serving real requests -- confirmed non-blocking
    locally (see 32b9c62)."""
    while True:
        db = SessionLocal()
        try:
            pages_updated, images_written = await asyncio.to_thread(fetch_images, db)
            if images_written:
                print(f"Background image fetch: {pages_updated} page(s) updated, {images_written} image(s) written.")
                _revalidate_frontend()
        except Exception as e:
            # A crash here must never take the loop (or the process) down
            # with it -- this is best-effort backfill, not request-critical
            # path. Logged and retried on the next scheduled pass rather
            # than propagating, which would silently end the loop for the
            # rest of the process's life with no error anywhere visible.
            print(f"Background image fetch failed: {e}")
        finally:
            db.close()
        await asyncio.sleep(IMAGE_FETCH_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Render's free-tier disk is ephemeral (resets on redeploy) -- but
    # DATABASE_URL is set to a real, persistent Postgres instance in
    # production, so this seed/resync step is what keeps a *local* SQLite
    # dev setup self-healing, not a workaround for data loss in production.
    db = SessionLocal()
    try:
        seed(db)
        # Unlike seed(), this DOES touch pages that already exist -- see its
        # docstring for why a copy edit or a corrected stock-photo query
        # needs to reach already-seeded pages, not just freshly inserted
        # ones, without wiping out any photo already fetched for them.
        resync_content(db)
    finally:
        db.close()

    # Backfills real stock photos for any page still missing one --
    # previously only reachable via the standalone script or the
    # /admin/fetch-images endpoint, which meant every new batch of content
    # needed a human to keep manually re-triggering it, repeatedly, until
    # Pexels' rate limit let a whole backlog through. Runs as a recurring
    # background task (see _run_periodic_image_fetch) off the
    # request-serving path instead, specifically to avoid blocking the app
    # from accepting requests -- including Render's own health check --
    # while it runs. That non-blocking property is confirmed sound on its
    # own (see 32b9c62's local verification).
    #
    # This was disabled entirely for a while after two Render free-tier
    # (0.1 CPU/512MB) memory-limit crashes in one afternoon: the first
    # during the original 8-way-concurrent version (fixed in 8558669,
    # dropped to 1 worker + a rate-limit short-circuit), the second even
    # after that fix -- at the site's size that day (~2,000 pages, having
    # 5x'd in a few hours) it was genuinely unclear whether the free tier
    # had headroom for *any* extra concurrent work at all. The instance has
    # since been upgraded to Render's 1 CPU/2GB tier specifically to give
    # this task real headroom (10x the CPU, 4x the RAM of the tier that
    # crashed), so it's back on by default -- see CONCURRENCY's docstring
    # in fetch_stock_images.py for how that headroom translates into a
    # concurrency value. Set RUN_STARTUP_IMAGE_FETCH=false to disable if a
    # future crash ever points back at this task specifically;
    # /admin/fetch-images still works as a manual override in the meantime.
    if (UNSPLASH_ACCESS_KEY or PEXELS_ACCESS_KEY) and os.environ.get("RUN_STARTUP_IMAGE_FETCH", "true") == "true":
        task = asyncio.create_task(_run_periodic_image_fetch())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    yield


app = FastAPI(title="Tulo API", lifespan=lifespan)

# The frontend runs on a different origin than the backend, so browser-side
# requests need CORS enabled. FRONTEND_ORIGIN should be set to the deployed
# frontend's URL (e.g. https://tulo.com); it defaults to the local Next.js
# dev server for local development.
frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


class _PageRecord(NamedTuple):
    """A plain, session-independent snapshot of one page's slug/title/content
    -- deliberately not a live Page ORM instance. get_db() closes its session
    at the end of every request, so anything meant to be cached and reused
    across requests can't be a raw ORM object still bound to that session
    (whether that would actually break depends on undefined,
    driver-specific behavior around already-loaded columns on a detached
    instance -- not something worth betting production correctness on when
    a plain tuple sidesteps the question entirely)."""

    slug: str
    title: str
    content: dict


# Every relatedness/cross-linking computation below (recipe_slugs on an
# ingredient hub, related_recipe_slugs, related_ingredient_slugs, a
# category's linked-back recipes, a technique glossary's demonstrating
# recipes) works by scanning *every* recipe_or_dish (or ingredient_hub)
# page's content once per call -- fine at the "dozens to low hundreds" of
# pages this was written against (see _recipe_slugs_using_ingredient's own
# docstring), a genuine problem now that content has grown to real scale
# (929 recipe_or_dish pages, 953 ingredient_hub pages as of the batch run
# that shipped the 2,000-title queue). A single ingredient_hub page view
# used to trigger two independent full scans of every recipe_or_dish page's
# full content (_recipe_slugs_using_ingredient and _related_ingredients
# each ran their own); a single recipe_or_dish page view triggered its own
# full scan (_related_recipes) plus one extra DB round-trip per
# ingredient with a resolved hub_slug. All of that runs synchronously, on
# Render's single-CPU instance, on literally every page view -- the
# frontend fetches every page with cache: "no-store" (see
# frontend/lib/api.ts), so there is no caching layer anywhere upstream
# absorbing this. Confirmed as the real cause behind 20+ second page loads
# reported the same day the 2,000-title batch went live.
#
# The fix: cache each template_type's (slug, title, content) snapshot once
# per process instead of re-querying and re-deserializing it on every
# request. This is safe with no TTL or invalidation logic at all -- not a
# staleness tradeoff, a genuine non-issue -- because nothing in this
# codebase ever mutates a recipe's ingredients/instructions/category_link/
# technique_link (the only fields any function below reads) after startup.
# The only fields that DO change at runtime are image_url/image_attribution
# (fetch_stock_images.py's _apply_result, and resync_content()'s runtime
# image key exclusions -- see _RUNTIME_IMAGE_KEYS), and no function cached
# through here ever reads those. Any content edit at all only ever reaches
# a running process via seed()/resync_content() at startup, which already
# means a fresh process (and therefore a cold, correct cache) either way.
_page_cache_lock = threading.Lock()
_page_cache: dict[str, list[_PageRecord]] = {}


def _cached_pages(db: Session, template_type: str) -> list[_PageRecord]:
    """Every page of this template_type, as plain (slug, title, content)
    snapshots -- computed once per process and reused for its lifetime, see
    the block comment above for why that's safe here. The lock only
    guards against redundant (not incorrect -- recomputing is idempotent)
    duplicate work from concurrent requests racing to populate a cold
    entry; sync endpoints like this run in FastAPI's threadpool, not the
    single-threaded event loop, so that race is real, just benign without
    it."""
    cached = _page_cache.get(template_type)
    if cached is not None:
        return cached
    with _page_cache_lock:
        cached = _page_cache.get(template_type)
        if cached is not None:
            return cached
        rows = db.query(Page.slug, Page.title, Page.content).filter(Page.template_type == template_type).all()
        records = [_PageRecord(slug=r.slug, title=r.title, content=r.content) for r in rows]
        _page_cache[template_type] = records
        return records


def _ingredient_hub_slugs_by_title(db: Session) -> dict[str, str]:
    """Lowercased ingredient hub title -> that hub's slug. Lets a recipe
    ingredient resolve to its hub page by plain name matching when nobody's
    hand-tagged it with hub_slug yet, so a brand new ingredient hub page
    lights up links from every recipe that already mentions it -- past and
    future -- without a backfill step. Deliberately exact-match only (plus a
    trailing-s strip for the common singular/plural case, e.g. "eggs" ->
    "egg"): a looser substring/fuzzy match was tried by hand during content
    backfill and produced real false positives ("cream cheese" matching
    "feta cheese", "rice vinegar" matching "balsamic vinegar"), so this
    stays conservative and only ever creates a link a reader would recognize
    as obviously correct.
    """
    return {page.title.strip().lower(): page.slug for page in _cached_pages(db, "ingredient_hub")}


def _resolve_hub_slug(name: str, explicit: str | None, hub_titles: dict[str, str]) -> str | None:
    """An ingredient's effective hub_slug: whatever's hand-set on it wins
    (an author can always override or deliberately leave one unmatched),
    otherwise an exact name match against a known hub title, see
    _ingredient_hub_slugs_by_title."""
    if explicit:
        return explicit
    key = name.strip().lower()
    if key in hub_titles:
        return hub_titles[key]
    if key.endswith("s") and key[:-1] in hub_titles:
        return hub_titles[key[:-1]]
    return None


def _recipe_slugs_using_ingredient(db: Session, hub_slug: str, hub_titles: dict[str, str]) -> list[str]:
    """Every recipe_or_dish page with an ingredient whose (explicit or
    name-matched, see _resolve_hub_slug) hub_slug matches this ingredient
    hub, computed live rather than hand-curated. The hand-curated version of
    this (a plain content field an author fills in) is exactly what went
    stale on 10 of 11 hub pages -- new recipes kept shipping without anyone
    remembering to go back and add themselves to every relevant hub's list.
    Deriving it means a new recipe lights up here the moment it's published,
    with nothing left to forget, and a brand new hub page immediately picks
    up every recipe that already mentions that ingredient by name.

    Iterates the process-lifetime page cache (see _cached_pages) rather than
    re-querying and re-deserializing every recipe_or_dish page's content on
    every call -- this genuinely is a full scan either way (there are
    thousands of recipes now, not the "dozens to low hundreds" this was
    first written against), but reusing the cached snapshot means paying
    that cost once per process instead of once per page view.
    """
    slugs = []
    for page in _cached_pages(db, "recipe_or_dish"):
        for ing in page.content.get("ingredients", []):
            if _resolve_hub_slug(ing.get("name", ""), ing.get("hub_slug"), hub_titles) == hub_slug:
                slugs.append(page.slug)
                break
    return slugs


def _normalize_dish_title(title: str) -> str:
    """Lowercases and strips a trailing "recipe" before comparing a
    collection card's title against a real recipe page's title -- every
    standalone recipe_or_dish page's title carries that suffix by
    convention ("Baba Ganoush Recipe"), while a collection card never
    does ("Baba Ganoush"), so a bare .strip().lower() comparison would
    never match the two for the exact same dish. Confirmed as a real
    miss: dip-recipes' "Baba Ganoush" card sat unlinked to the
    already-published baba-ganoush recipe until this was added, even
    though nothing about the dish itself was actually missing."""
    title = title.strip().lower()
    return re.sub(r"\s+recipe$", "", title)


def _recipes_linking_to(db: Session, field: str, target_slug: str) -> list[_PageRecord]:
    """recipe_or_dish pages whose content[field] (a singular LinkRef, e.g.
    category_link or technique_link) points at target_slug -- the reverse of
    a recipe's own forward link, computed live so a collection or a how-to
    guide always reflects every recipe that already points at it rather
    than needing a second, hand-maintained copy of the same fact."""
    matches = []
    for page in _cached_pages(db, "recipe_or_dish"):
        link = page.content.get(field)
        if link and link.get("slug") == target_slug:
            matches.append(page)
    return matches


# Cap on how many *computed* related-content suggestions get merged into a
# hand-curated related_* list (see _fill_related below). Keeps these lists
# the same "a small, deliberate handful" size they'd be if an editor had
# picked them, rather than dumping in every loose match.
_RELATED_LIMIT = 4


def _fill_related(curated: list[str], computed: list[str]) -> list[str]:
    """Hand-picked entries always come first and are never dropped or
    reordered -- a curator's specific pairing (this cocktail goes with that
    dessert, say) can reflect a judgment call no similarity score would
    reproduce. Computed suggestions only fill the remaining slots, and only
    with slugs not already present. Recomputed on every request against the
    full current catalog (not a stored, one-time snapshot), so an empty or
    thin list left over from when there were only a couple of candidates to
    choose from keeps discovering better matches as new content ships --
    with nothing to run and no batch job to remember, "curation" naturally
    improves as the pool of things to curate from grows.
    """
    filled = list(curated)
    for slug in computed:
        if len(filled) >= _RELATED_LIMIT:
            break
        if slug not in filled:
            filled.append(slug)
    return filled


def _related_recipes(db: Session, page: Page, hub_titles: dict[str, str]) -> list[str]:
    """Other recipes worth surfacing as "you might also like," scored by
    concrete overlap rather than guessed at: sharing a cuisine collection
    (category_link) or a headline technique (technique_link) is a strong
    signal, sharing one or more real ingredients (via the same hub_slug
    resolution used everywhere else) is a weaker one. Scores are summed and
    ranked highest-first; recipes with a score of 0 (no signal at all)
    never show up, since two recipes sharing nothing in common shouldn't be
    called "related" just to fill a slot."""
    content = page.content
    category_slug = (content.get("category_link") or {}).get("slug")
    technique_slug = (content.get("technique_link") or {}).get("slug")
    my_hubs = {
        _resolve_hub_slug(ing.get("name", ""), ing.get("hub_slug"), hub_titles)
        for ing in content.get("ingredients", [])
    }
    my_hubs.discard(None)

    scored: list[tuple[int, str]] = []
    for other in _cached_pages(db, "recipe_or_dish"):
        if other.slug == page.slug:
            continue
        oc = other.content
        score = 0
        if category_slug and (oc.get("category_link") or {}).get("slug") == category_slug:
            score += 2
        if technique_slug and (oc.get("technique_link") or {}).get("slug") == technique_slug:
            score += 2
        other_hubs = {
            _resolve_hub_slug(ing.get("name", ""), ing.get("hub_slug"), hub_titles)
            for ing in oc.get("ingredients", [])
        }
        other_hubs.discard(None)
        score += min(len(my_hubs & other_hubs), 3)
        if score > 0:
            scored.append((score, other.slug))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [slug for _, slug in scored]


def _related_ingredients(db: Session, hub_slug: str, hub_titles: dict[str, str]) -> list[str]:
    """Other ingredient hubs worth cross-linking, ranked by how often they
    actually appear in the same recipe as this one -- ingredients cooked
    together are the ones a reader shopping for this one would plausibly
    also need, which is a more grounded notion of "related" here than any
    property of the ingredients themselves."""
    counts: dict[str, int] = {}
    for page in _cached_pages(db, "recipe_or_dish"):
        hubs_in_recipe = {
            _resolve_hub_slug(ing.get("name", ""), ing.get("hub_slug"), hub_titles)
            for ing in page.content.get("ingredients", [])
        }
        hubs_in_recipe.discard(None)
        if hub_slug not in hubs_in_recipe:
            continue
        for other_hub in hubs_in_recipe:
            if other_hub != hub_slug:
                counts[other_hub] = counts.get(other_hub, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [slug for slug, _ in ranked]


def _bare_term_from_definition_title(title: str) -> str:
    """Mirrors frontend/lib/linkTerms.ts's bareTermFromDefinitionTitle: a
    "What Is X?" title reduced to the bare term X, used as a fallback when a
    definition page has no explicit link_terms of its own."""
    return re.sub(r"\?.*$", "", re.sub(r"^What Is ", "", title, flags=re.IGNORECASE))


def _recipes_demonstrating_terms(db: Session, terms: list[str]) -> list[str]:
    """recipe_or_dish pages whose instructions actually contain one of these
    terms (case-insensitive, whole-word) -- the same literal-term matching
    LinkifiedText already does client-side to auto-link prose, reused here
    server-side to find which recipes are worth surfacing as "see it in
    action" from a technique's own glossary page."""
    if not terms:
        return []
    patterns = [re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE) for term in terms]
    slugs = []
    for page in _cached_pages(db, "recipe_or_dish"):
        text = " ".join(page.content.get("instructions", []))
        if any(p.search(text) for p in patterns):
            slugs.append(page.slug)
    return slugs


def _ingredient_hub_pages_by_slug(db: Session) -> dict[str, _PageRecord]:
    """ingredient_hub pages keyed by slug, from the same process-lifetime
    cache as _cached_pages -- lets a recipe page's per-ingredient hub_slug
    lookup (_swappable_substitutes_for) be a plain dict access instead of
    its own DB round trip per ingredient. A recipe with a dozen ingredients
    used to mean a dozen single-row queries on every page view; this is one
    dict built from the already-cached hub list instead."""
    return {page.slug: page for page in _cached_pages(db, "ingredient_hub")}


def _swappable_substitutes_for(hub: _PageRecord | None) -> list[dict]:
    """`hub`'s own substitutes -- name, display ratio, and the numeric
    ratio_multiplier that lets the swap be pure client-side math -- for the
    ingredient swap tool on a recipe page. Only substitutes with a
    ratio_multiplier are returned: an additive combo or a deliberately
    vague ratio ("slightly more") can't be swapped in by a multiply, so
    offering it as a one-click option would just be wrong."""
    if hub is None:
        return []
    return [sub for sub in hub.content.get("substitutes", []) if sub.get("ratio_multiplier") is not None]


def _page_out(page: Page, content: dict) -> PageOut:
    """A PageOut built from an enriched content dict -- a copy, not a
    mutation of page.content itself, since every enrichment below is
    response-only and must never get persisted back onto the stored row."""
    return PageOut(
        slug=page.slug,
        template_type=page.template_type,
        title=page.title,
        status=page.status,
        batch_number=page.batch_number,
        content=content,
        created_at=page.created_at,
    )


@app.get("/pages/{slug}", response_model=PageOut)
def get_page(slug: str, db: Session = Depends(get_db)):
    page = db.query(Page).filter(Page.slug == slug).first()
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")

    if page.template_type == "ingredient_hub":
        content = copy.deepcopy(page.content)
        hub_titles = _ingredient_hub_slugs_by_title(db)
        content["recipe_slugs"] = _recipe_slugs_using_ingredient(db, page.slug, hub_titles)
        content["related_ingredient_slugs"] = _fill_related(
            content.get("related_ingredient_slugs", []),
            _related_ingredients(db, page.slug, hub_titles),
        )
        return _page_out(page, content)

    if page.template_type == "recipe_or_dish":
        # Same live-derivation pattern as ingredient_hub above: embed each
        # swappable ingredient's own hub's substitute data directly into the
        # recipe payload so the frontend's swap tool needs no second fetch
        # (still just a data lookup, not a generation step, per the "no LLM
        # in the personalization path" constraint), and resolve hub_slug by
        # name match (see _resolve_hub_slug) for any ingredient nobody's
        # hand-tagged yet, so the ingredient-hub link and swap tool both
        # light up the moment a matching hub page exists -- not only after
        # someone remembers to go back and tag this recipe.
        content = copy.deepcopy(page.content)
        hub_titles = _ingredient_hub_slugs_by_title(db)
        hubs_by_slug = _ingredient_hub_pages_by_slug(db)
        for ing in content.get("ingredients", []):
            hub_slug = _resolve_hub_slug(ing.get("name", ""), ing.get("hub_slug"), hub_titles)
            if hub_slug:
                ing["hub_slug"] = hub_slug
                substitutes = _swappable_substitutes_for(hubs_by_slug.get(hub_slug))
                if substitutes:
                    ing["available_substitutes"] = substitutes
        content["related_recipe_slugs"] = _fill_related(
            content.get("related_recipe_slugs", []),
            _related_recipes(db, page, hub_titles),
        )
        return _page_out(page, content)

    if page.template_type == "category_roundup":
        # recipe_cards is hand-curated editorial content -- it deliberately
        # includes aspirational cards for dishes the site hasn't written yet
        # (slug: None), which a purely computed list would wipe out. So this
        # only ever adds or fills in, never removes or reorders:
        #
        # - A real recipe whose own category_link already points here and
        #   whose title matches an existing aspirational card (an editor
        #   already described "Carne Asada Tacos" by name before it existed
        #   as a page) fills that card in -- its slug and photo, so the
        #   card becomes clickable -- rather than appending a second,
        #   duplicate "Carne Asada Tacos" card next to the still-unlinked
        #   placeholder. This is what actually makes an aspirational card
        #   "come true" once its recipe is written; without it, publishing
        #   the matching recipe alone wouldn't be enough, the placeholder
        #   would sit there dead forever unless someone remembered to go
        #   back and hand-edit this page too.
        # - Any other real recipe whose category_link points here (no
        #   matching placeholder title) is appended as a new card, same as
        #   before.
        content = copy.deepcopy(page.content)
        cards = content.setdefault("recipe_cards", [])
        existing_slugs = {c.get("slug") for c in cards if c.get("slug")}
        cards_by_title = {_normalize_dish_title(c.get("title", "")): c for c in cards}
        # _recipes_linking_to reads recipe_or_dish pages from the process
        # cache (see _cached_pages) -- fine for category_link, title, and
        # why_it_works, which never change once a process starts, but NOT
        # for image_url/image_attribution, which the background image-fetch
        # loop writes at runtime. So this loop deliberately leaves a new or
        # newly-filled card's image fields unset rather than copying a
        # cached (and potentially long-stale) rc.get("image_url") -- the
        # cards_needing_image pass right below already does a fresh,
        # uncached lookup for exactly that, for any card missing one.
        for recipe in _recipes_linking_to(db, "category_link", page.slug):
            if recipe.slug in existing_slugs:
                continue
            rc = recipe.content
            placeholder = cards_by_title.get(_normalize_dish_title(recipe.title))
            if placeholder is not None and not placeholder.get("slug"):
                placeholder["slug"] = recipe.slug
                continue
            why = (rc.get("why_it_works") or "").strip()
            description = why.split(". ")[0].rstrip(".") + "." if why else ""
            cards.append(
                {
                    "title": recipe.title,
                    "slug": recipe.slug,
                    "description": description,
                    "image_query": rc.get("hero_image_query", recipe.title),
                    "image_url": None,
                    "image_attribution": None,
                }
            )
        # A card can already carry a real slug from the moment it's authored
        # (every card generated by the content pipeline does -- see
        # generate_companion_recipes.py/integrate_batch_results.py, which
        # both write a recipe's real slug directly rather than leaving a
        # None placeholder for the loop above to fill in later), which
        # skips that loop's image-copy step entirely: it only runs for a
        # card that *starts* slug-less and gets matched to a recipe later.
        # A real bug -- char-siu's card on chinese-recipes had a real slug,
        # a real published recipe with its own real photo, and no image on
        # the card, because fetch_stock_images.py's separate per-card
        # search (see fetch_images()) had simply never been run against it.
        # Rather than depend on that offline job (or on remembering to run
        # it) for the common case where a linked card's dish already has
        # its own recipe page and photo, this second pass backfills any
        # slug-bearing card's image directly from its own recipe on every
        # request -- the same "compute it live so nobody has to remember a
        # manual step" pattern already used for recipe_slugs/related_*
        # elsewhere in this file. fetch_images()'s independent card search
        # still matters for a genuinely aspirational card with no recipe.
        cards_needing_image = [c for c in cards if c.get("slug") and not c.get("image_url")]
        if cards_needing_image:
            recipes_by_slug = {
                r.slug: r
                for r in db.query(Page)
                .filter(Page.slug.in_({c["slug"] for c in cards_needing_image}))
                .all()
            }
            for card in cards_needing_image:
                recipe = recipes_by_slug.get(card["slug"])
                if recipe is not None and recipe.content.get("image_url"):
                    card["image_url"] = recipe.content.get("image_url")
                    card["image_attribution"] = recipe.content.get("image_attribution")
        return _page_out(page, content)

    if page.template_type == "howto_technique":
        # recipe_slugs is a bare slug list (no aspirational placeholders to
        # preserve, unlike category_roundup's recipe_cards), so any recipe
        # whose technique_link already points here is simply unioned in --
        # a hand-curated pick stays first, a newly-published recipe that
        # links here shows up without anyone having to remember to add it.
        content = copy.deepcopy(page.content)
        linked = [r.slug for r in _recipes_linking_to(db, "technique_link", page.slug)]
        content["recipe_slugs"] = list(dict.fromkeys(content.get("recipe_slugs", []) + linked))
        return _page_out(page, content)

    if page.template_type == "definition":
        # A glossary page's "related recipes" is filled the same way its own
        # inline auto-linking already works (see frontend/lib/linkTerms.ts):
        # any recipe whose instructions actually contain one of this term's
        # link_terms (or, absent those, the bare term derived from the
        # title) is a recipe that genuinely demonstrates the technique, not
        # a guess.
        content = copy.deepcopy(page.content)
        terms = content.get("link_terms") or [_bare_term_from_definition_title(page.title)]
        content["related_recipe_slugs"] = _fill_related(
            content.get("related_recipe_slugs", []),
            _recipes_demonstrating_terms(db, terms),
        )
        return _page_out(page, content)

    if page.template_type == "substitute":
        # A substitute guide's "recipes using this ingredient" is the same
        # fact as its ingredient hub's recipe_slugs (see
        # _recipe_slugs_using_ingredient) -- hub_page_slug already says
        # which hub this substitute page corresponds to, so this reuses that
        # derivation instead of hand-maintaining a second copy of it.
        content = copy.deepcopy(page.content)
        hub_page_slug = content.get("hub_page_slug")
        if hub_page_slug:
            hub_titles = _ingredient_hub_slugs_by_title(db)
            derived = _recipe_slugs_using_ingredient(db, hub_page_slug, hub_titles)
            content["recipe_slugs"] = list(dict.fromkeys(content.get("recipe_slugs", []) + derived))
        return _page_out(page, content)

    return page


def _summary_image(content: dict) -> tuple[str | None, dict | None, str | None, str | None]:
    """image_url, image_attribution, hero_image_query, image_alt for a
    page's summary thumbnail. Category Roundup pages have no hero image of
    their own (only per-card images on recipe_cards), so this falls back to
    the first card's image (and that card's own image_alt) as a
    representative thumbnail for the collection."""
    if content.get("image_url"):
        return (
            content["image_url"],
            content.get("image_attribution"),
            content.get("hero_image_query"),
            content.get("image_alt"),
        )
    cards = content.get("recipe_cards")
    if cards:
        first = cards[0]
        return first.get("image_url"), first.get("image_attribution"), first.get("image_query"), first.get("image_alt")
    return None, None, content.get("hero_image_query"), content.get("image_alt")


@app.get("/pages", response_model=list[PageSummary])
def list_pages(
    template_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    slugs: str | None = Query(
        default=None,
        description=(
            "Comma-separated slugs to restrict the result to. For a caller "
            "that already knows exactly which pages it wants (RelatedLinks "
            "resolving a handful of related_recipe_slugs, say) -- fetching "
            "every page of a template_type just to filter it down client-"
            "side used to mean a full scan of up to ~950 rows to find 4."
        ),
    ),
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    # Ordered explicitly so pagination is stable across requests -- without
    # an order_by, a database is free to return rows in whatever order it
    # finds convenient, which could reshuffle between one "load more" call
    # and the next. Callers that want everything (the homepage carousels,
    # the sitemap, RelatedLinks) just omit limit/offset and get the full,
    # still-ordered list, unchanged from before this was added.
    #
    # Descending by id (newest page first): id is an auto-increment primary
    # key, so this is equivalent to newest-published-first without adding a
    # separate timestamp column. Newest-first reads better on the homepage
    # carousels and the section landing pages ("Load more" surfaces the
    # freshest content first, not whatever happened to seed the site
    # originally) and costs nothing on the sitemap/RelatedLinks callers,
    # which don't care about order.
    query = db.query(Page).order_by(Page.id.desc())
    if template_type is not None:
        query = query.filter(Page.template_type == template_type)
    if slugs is not None:
        query = query.filter(Page.slug.in_([s for s in slugs.split(",") if s]))
    if q:
        # Title-only for now: ilike() is portable across SQLite/Postgres,
        # unlike JSON-field queries (Postgres' ->> operator has no SQLite
        # equivalent SQLAlchemy can compile the same way). Matches real
        # queries fine at the current content scale; a real search index
        # (Postgres full-text search, or an external service) is the
        # right upgrade once page count and traffic justify it.
        #
        # The single "Homepage" row matches a text search for "home" (and
        # similar) the same as any other page's title, but a search result
        # that navigates to the site's own homepage is never useful -- it's
        # already one click away from everywhere. Excluded here rather than
        # in each frontend caller, since both the search results page and
        # the header's autocomplete dropdown go through this same query.
        query = query.filter(Page.title.ilike(f"%{q}%"), Page.template_type != "homepage")

    if limit is not None:
        query = query.offset(offset).limit(limit)

    summaries = []
    for page in query.all():
        image_url, image_attribution, hero_image_query, image_alt = _summary_image(page.content)
        summaries.append(
            PageSummary(
                slug=page.slug,
                template_type=page.template_type,
                title=page.title,
                image_url=image_url,
                image_attribution=image_attribution,
                hero_image_query=hero_image_query,
                image_alt=image_alt,
                link_terms=page.content.get("link_terms") if page.template_type == "definition" else None,
            )
        )
    return summaries


@app.get("/recipes/match")
def match_recipes(ingredients: str = Query(...), db: Session = Depends(get_db)):
    """Backs the Custom Recipe Generator tool. There's no LLM wired into
    this stack to actually generate a new recipe from scratch, so instead
    of faking that, this matches the ingredients someone has on hand
    against real recipes already in the database and ranks them by
    overlap -- a genuinely working recommendation, not a placeholder, that
    gets more useful as more recipes get published rather than needing a
    rebuild later. `ingredients` is a comma-separated list, e.g.
    "chicken thighs, spinach, feta, lemon"."""
    terms = [t.strip().lower() for t in ingredients.split(",") if t.strip()]
    if not terms:
        return []

    matches = []
    for page in db.query(Page).filter(Page.template_type == "recipe_or_dish").all():
        recipe_ingredients = [ing["name"].lower() for ing in page.content.get("ingredients", [])]
        matched_terms = [
            term for term in terms if any(term in name or name in term for name in recipe_ingredients)
        ]
        if matched_terms:
            image_url, image_attribution, hero_image_query, image_alt = _summary_image(page.content)
            matches.append(
                {
                    "slug": page.slug,
                    "title": page.title,
                    "matched_count": len(matched_terms),
                    "requested_count": len(terms),
                    "total_ingredients": len(recipe_ingredients),
                    "image_url": image_url,
                    "image_attribution": image_attribution,
                    "hero_image_query": hero_image_query,
                    "image_alt": image_alt,
                }
            )

    matches.sort(key=lambda m: m["matched_count"], reverse=True)
    return matches[:5]


# Manual trigger for fetch_stock_images.py, for hosts (like Render's free
# tier) with no shell access to run the script directly. Gated behind
# ADMIN_TASK_TOKEN so it isn't a public unauthenticated endpoint hitting
# external APIs -- if that env var isn't set, this always 404s, matching
# the "inert without configuration" pattern used everywhere else in the
# stock-photo feature. A token in a URL query string is a modest bar (it
# can end up in server/proxy logs) but is a reasonable trade-off for an
# occasional manual maintenance action on a low-traffic site; rotate
# ADMIN_TASK_TOKEN in Render if you ever suspect it's leaked.
ADMIN_TASK_TOKEN = os.environ.get("ADMIN_TASK_TOKEN")


@app.get("/admin/fetch-images")
def trigger_fetch_images(
    token: str,
    force: bool = False,
    slugs: str | None = Query(
        default=None,
        description=(
            "Comma-separated slugs to re-fetch, ignoring every other page. Always "
            "re-fetches the given slugs regardless of `force`. Matches a "
            "category_roundup card by its own slug too, not just a top-level "
            "page's slug -- e.g. `slugs=char-siu` redoes both the standalone "
            "char-siu recipe page and (if it's linked into one) its card on a "
            "collection page, without touching that collection's other cards."
        ),
    ),
    revalidate: bool = Query(
        default=False,
        description=(
            "Also treat an existing image_url as needing a fresh fetch if it no "
            "longer actually loads (not just missing or on a disallowed host) -- "
            "one real network request per already-valid image, so this is "
            "noticeably slower than a normal run. Meant to be run periodically "
            "(e.g. a scheduled weekly call) as the actual self-healing mechanism "
            "for a photo that was live when fetched but has since been taken "
            "down at the source -- see fetch_images()'s own docstring."
        ),
    ),
    db: Session = Depends(get_db),
):
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    only_slugs = {s.strip() for s in slugs.split(",") if s.strip()} if slugs else None

    log = io.StringIO()
    with redirect_stdout(log):
        pages_updated, images_written = fetch_images(db, force=force, only_slugs=only_slugs, revalidate=revalidate)

    frontend_revalidated = _revalidate_frontend() if images_written else False

    return {
        "unsplash_configured": bool(UNSPLASH_ACCESS_KEY),
        "pexels_configured": bool(PEXELS_ACCESS_KEY),
        "pages_updated": pages_updated,
        "images_written": images_written,
        "frontend_revalidated": frontend_revalidated,
        "log": log.getvalue().splitlines(),
    }


@app.get("/admin/image-audit")
def image_audit(
    token: str,
    check_reachability: bool = Query(
        default=False,
        description=(
            "Also live-check (GET, not just a host-string check) every "
            "image_url that already looks valid. Off by default -- this "
            "endpoint is otherwise a pure DB read with no external calls, "
            "and this option trades that for the one check that actually "
            "catches a URL that was reachable when fetched but has since "
            "died at the source (see `dead` below); runs one request per "
            "image, so it's slower and worth reserving for an actual "
            "periodic check, not every casual call."
        ),
    ),
    db: Session = Depends(get_db),
):
    """A full-site image report, gated behind the same ADMIN_TASK_TOKEN as
    /admin/fetch-images. Three kinds of problems this surfaces that
    clicking through pages one at a time can't:

    - `missing`: pages/cards with no image_url at all (shows as the
      placeholder box on the site).
    - `broken`: pages/cards whose image_url is set but points at a host
      next.config.mjs doesn't allowlist for next/image -- these render as
      a broken image, not a placeholder, which is easy to miss since
      nothing else in this pipeline currently detects it. (images.py
      refuses to write one of these going forward, and fetch_images()
      itself now treats an existing broken URL the same as a missing one,
      so every entry here self-heals on the next startup or
      /admin/fetch-images run with no `force` needed -- this endpoint is
      purely diagnostic for this case, not a required step before a fix
      takes effect.)
    - `dead` (only checked when check_reachability=true): a URL that looks
      fine (real host, real shape) but the photo itself no longer loads --
      taken down at the source after being fetched, going stale in a way
      images.py's own write-time _is_reachable() check can't catch, since
      that only runs once, at the moment a photo is first selected. This
      is exactly the class of bug that shipped silently on char-siu's
      chinese-recipes card: a photo valid when written, dead by the time a
      reader actually saw the page, with nothing surfacing it except a
      user noticing the missing photo (StockPhotoSlot's onError hides a
      failed load rather than showing a broken-image icon, by design --
      see its own docstring). Same remediation as `broken`: an
      /admin/fetch-images run (force=true, scoped via `slugs` to just the
      affected pages) replaces it with a fresh, currently-live photo.
    """
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    missing = []
    broken = []
    dead = []

    def _check(url: str | None, **identity):
        if not url:
            missing.append(identity)
        elif not is_allowed_image_url(url):
            broken.append({**identity, "image_url": url})
        elif check_reachability and not _is_reachable(url):
            dead.append({**identity, "image_url": url})

    for page in db.query(Page).order_by(Page.id).all():
        content = page.content
        query_key = SINGLE_IMAGE_TEMPLATES.get(page.template_type)
        if query_key and query_key in content:
            _check(content.get("image_url"), slug=page.slug, template_type=page.template_type)
        elif page.template_type == "category_roundup":
            for card in content.get("recipe_cards", []):
                _check(card.get("image_url"), slug=page.slug, card=card.get("title"))

    return {
        "missing_count": len(missing),
        "missing": missing,
        "broken_count": len(broken),
        "broken": broken,
        "dead_count": len(dead) if check_reachability else None,
        "dead": dead,
    }
