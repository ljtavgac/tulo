import asyncio
import copy
import io
import os
import re
import secrets
import threading
import time
from collections import Counter
from contextlib import asynccontextmanager, redirect_stdout
from datetime import datetime, timezone
from html import escape as escape_html
from typing import NamedTuple

import requests
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .content_audit import run_full_audit, scan_ai_tells, scan_image_relevance_risk
from .database import Base, SessionLocal, engine, get_db
from .fetch_stock_images import SINGLE_IMAGE_TEMPLATES, _category_fallback_query, _recipe_dish_must_match_terms, _search_query_for, fetch_images
from .images import (
    ALLOWED_IMAGE_HOSTS,
    PEXELS_ACCESS_KEY,
    SEARCH_RESULTS_PER_PAGE,
    UNSPLASH_ACCESS_KEY,
    _is_reachable,
    _is_relevant,
    _search_pexels,
    _search_unsplash,
    is_allowed_image_url,
)
from .models import BatchApproval, OutreachProspect, Page, PageReview
from .schemas import PageOut, PageSummary
from .seed_templates import SEED_PAGES, resync_content, seed


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
# throttling it. Lowered from 3600 to 900, then to 300, given the real
# backlog (~1,000 pages) was visibly clearing too slowly at each prior
# value -- still purely a guess at Pexels' real window (never confirmed,
# see fetch_stock_images.py for the same admission), just a less
# conservative one now that there's a cheap way to find out if it's wrong.
# Every pass -- rate-limited or not -- still does a full scan of the whole
# page catalog to find what needs a fetch (see fetch_images()'s own
# all_pages query), so going much lower than this starts trading Pexels
# throughput for a real, separate, recurring DB/CPU cost that scales with
# how often this wakes up; worth optimizing that query before going lower
# than 300. Configurable via env var for the same reason.
IMAGE_FETCH_INTERVAL_SECONDS = int(os.environ.get("IMAGE_FETCH_INTERVAL_SECONDS", 300))

# How often a background pass also revalidates already-written image_urls
# (see fetch_images()'s revalidate param), not just backfill pages with no
# image at all -- a real, separate cost from the default pass (one live
# GET per already-valid image already in the database, not the cheap dict
# check _needs_fetch does otherwise), so this runs on a much slower
# cadence than IMAGE_FETCH_INTERVAL_SECONDS itself rather than on every
# pass. 24 hours by default: catches a photo taken down at the source
# within a day, without turning every 5-minute pass into a full-catalog
# live-fetch storm. Configurable via env var for the same reason as
# IMAGE_FETCH_INTERVAL_SECONDS.
IMAGE_REVALIDATE_INTERVAL_SECONDS = int(os.environ.get("IMAGE_REVALIDATE_INTERVAL_SECONDS", 86400))


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

    Also periodically revalidates already-written image_urls, on the much
    slower IMAGE_REVALIDATE_INTERVAL_SECONDS cadence tracked below as
    elapsed wall-clock time since this loop started. Confirmed necessary
    for real, not just a hypothetical: the default pass alone only ever
    finds pages with *no* image_url, never one that was valid when
    written and has since been taken down at the source (see images.py's
    _is_reachable() docstring for the char-siu incident this exact gap
    let through once already) -- that class of decay had no automatic
    path to self-heal before this, only a manual
    /admin/fetch-images?revalidate=true run someone had to remember to
    make. The elapsed-time tracker lives only in this process's memory,
    so a redeploy resets it -- if deploys happen more often than
    IMAGE_REVALIDATE_INTERVAL_SECONDS, a periodic revalidation pass might
    never actually fire before the process restarts.
    /admin/image-audit?check_reachability=true stays the manual fallback
    that doesn't depend on this loop's uptime at all.

    fetch_images() is synchronous (blocking `requests` calls) so each pass
    runs in a worker thread via asyncio.to_thread rather than blocking the
    event loop that's also serving real requests -- confirmed non-blocking
    locally (see 32b9c62)."""
    last_revalidate = time.monotonic()
    while True:
        db = SessionLocal()
        try:
            due_for_revalidate = time.monotonic() - last_revalidate >= IMAGE_REVALIDATE_INTERVAL_SECONDS
            pages_updated, images_written = await asyncio.to_thread(
                fetch_images, db, revalidate=due_for_revalidate
            )
            if due_for_revalidate:
                last_revalidate = time.monotonic()
            if images_written:
                label = "Background image fetch (revalidating)" if due_for_revalidate else "Background image fetch"
                print(f"{label}: {pages_updated} page(s) updated, {images_written} image(s) written.")
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


def _add_missing_columns(engine) -> None:
    """Base.metadata.create_all() (called right after this in lifespan())
    only creates tables that don't exist yet -- it never ALTERs an
    existing table to add a column a newer version of a model defines.
    This codebase has no migration framework (no Alembic), so a column
    added to a model whose table was already deployed (e.g.
    OutreachProspect.sent_at/send_error, added after outreach_prospects
    already existed in live Postgres) needs to be added by hand here, or
    every request that touches that column crashes with "column does not
    exist" -- confirmed for real: both tulo-backend and
    tulo-backend-staging failed to deploy on the commit that added those
    two columns, because _seed_outreach_examples() queries the table at
    startup.

    Walks every mapped table/column pair; for any column the live
    database doesn't have yet, issues a plain ALTER TABLE ADD COLUMN.
    Idempotent and safe on every startup -- a no-op once a column exists,
    same self-healing pattern as seed()/resync_content() below. Every
    column added this way must be nullable (true of every column on
    every model in this file so far) -- ADD COLUMN on a table with
    existing rows needs a value for those rows, and a nullable column
    with no explicit default just backfills NULL, which is exactly what
    "this field didn't exist yet for old rows" should mean anyway."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # Brand-new table -- create_all() handles this case.
            existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'))
                print(f"  _add_missing_columns: added {table.name}.{column.name} ({col_type})")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _add_missing_columns(engine)
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
        _seed_outreach_examples(db)
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
    # git_commit lets a caller tell "the deploy of commit X has actually
    # landed and is serving requests" apart from "the service responds at
    # all" -- RENDER_GIT_COMMIT is set automatically by Render for any
    # service deployed from a connected git repo (unset outside Render,
    # e.g. local dev, in which case this is just null and harmless).
    # apply-baked-images-to-prod.yml polls this instead of blindly
    # retrying on a fixed timer -- real, confirmed gap (2026-09-15): a
    # slow-than-usual Render deploy needed three separate manual
    # workflow re-triggers (~15+ minutes) before the fixed ~4.5-minute
    # retry window ever lined up with the deploy actually being live.
    return {"status": "ok", "git_commit": os.environ.get("RENDER_GIT_COMMIT")}


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
    """Every *published* page of this template_type, as plain (slug, title,
    content) snapshots -- computed once per process and reused for its
    lifetime, see the block comment above for why that's safe here. The
    lock only guards against redundant (not incorrect -- recomputing is
    idempotent) duplicate work from concurrent requests racing to populate
    a cold entry; sync endpoints like this run in FastAPI's threadpool,
    not the single-threaded event loop, so that race is real, just benign
    without it.

    Excludes content["unpublished"] pages (see e.g. swordfish-recipes) at
    this one shared source rather than in each caller -- every function
    built on this cache (hub_slug resolution, recipe_slugs, related_*,
    the auto-linking dictionary, ...) gets the exclusion automatically:
    an unpublished ingredient_hub page stops being a valid hub_slug match
    target, stops offering its substitutes, stops appearing as a related
    link, etc., all for free, with nothing to remember to add at a new
    call site later."""
    cached = _page_cache.get(template_type)
    if cached is not None:
        return cached
    with _page_cache_lock:
        cached = _page_cache.get(template_type)
        if cached is not None:
            return cached
        rows = db.query(Page.slug, Page.title, Page.content).filter(Page.template_type == template_type).all()
        records = [
            _PageRecord(slug=r.slug, title=r.title, content=r.content)
            for r in rows
            if not r.content.get("unpublished")
        ]
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


# Real recipe ingredient names almost always carry a trailing prep clause
# ("garlic, minced"), a trailing parenthetical aside ("sour cream
# (optional)"), or a leading state/packaging adjective ("fresh chives",
# "unsweetened cocoa powder") that a bare exact match can't see past --
# confirmed live (2026-09-15): only 361/1031 published recipes had even
# one ingredient resolve to a hub at all. These two lists are the fix,
# and they're deliberately narrow: every word in them is either a pure
# preparation/state/packaging descriptor (chopped, diced, softened,
# divided, optional, room temperature...) or a pure quantity/cut
# descriptor (inch, pieces, wedges...) -- NEVER a color (black, white,
# red...) and NEVER a word that's itself a distinct food noun elsewhere
# in this corpus (chicken, garlic, cream, onion, vanilla...), so
# stripping one can't turn one food into a different one. "ground" is
# deliberately excluded even though it looks like a state word --
# "ground beef" and "beef" have meaningfully different fat content, so
# collapsing that distinction would be a real (if subtle) accuracy
# regression, not just a missed match. Measured impact: 361 -> 473/1031
# recipes gain a real, correctly-resolved swappable ingredient, with
# every one of the 112 newly-matched pairs manually reviewed.
_HUB_MATCH_LEADING_SAFE_WORDS = {
    "fresh", "unsalted", "dried", "large", "small", "fine", "finely",
    "granulated", "kosher", "powdered", "toasted", "unsweetened", "frozen",
    "plain", "whole", "chopped", "minced", "diced", "sliced", "shredded",
    "grated", "cubed", "crumbled", "raw", "cooked",
}
_HUB_MATCH_TRAILING_CLAUSE_SAFE_WORDS = {
    "for", "chopped", "and", "sliced", "minced", "diced", "into", "cut",
    "finely", "softened", "thinly", "inch", "peeled", "freshly",
    "garnish", "melted", "or", "divided", "serving", "the", "on", "shredded",
    "halved", "drained", "skinless", "frying", "smashed", "plus", "optional",
    "rinsed", "cubed", "beaten", "quartered", "skin", "pieces", "thick",
    "packed", "room", "temperature", "at", "to", "taste", "strips", "wedges",
    "bite", "sized", "size", "crushed", "trimmed", "boneless",
    "cubes", "julienned", "zested", "seeded", "stemmed",
}


def _exact_hub_match(key: str, hub_titles: dict[str, str]) -> str | None:
    if key in hub_titles:
        return hub_titles[key]
    if key.endswith("s") and key[:-1] in hub_titles:
        return hub_titles[key[:-1]]
    return None


def _resolve_hub_slug(name: str, explicit: str | None, hub_titles: dict[str, str]) -> str | None:
    """An ingredient's effective hub_slug: whatever's hand-set on it wins
    (an author can always override or deliberately leave one unmatched),
    otherwise a match against a known hub title (see
    _ingredient_hub_slugs_by_title) -- exact first, then the same exact
    match retried after stripping a trailing parenthetical, a trailing
    prep clause made ENTIRELY of words in
    _HUB_MATCH_TRAILING_CLAUSE_SAFE_WORDS, and/or a leading word in
    _HUB_MATCH_LEADING_SAFE_WORDS. Deliberately never a substring/fuzzy
    match anywhere in this chain -- that was tried by hand during content
    backfill and produced real false positives ("cream cheese" matching
    "feta cheese", "rice vinegar" matching "balsamic vinegar"), which is
    exactly what stripping only from a curated, food-noun-free word list
    (rather than searching for a hub title anywhere inside the name)
    structurally can't reproduce: the core noun phrase itself is never
    touched, only its recognized edges."""
    if explicit:
        return explicit
    key = name.strip().lower()

    match = _exact_hub_match(key, hub_titles)
    if match:
        return match

    stripped_paren = re.sub(r"\s*\([^)]*\)", "", key).strip()
    if stripped_paren != key:
        match = _exact_hub_match(stripped_paren, hub_titles)
        if match:
            return match
        key = stripped_paren

    if "," in key:
        prefix, clause = key.split(",", 1)
        prefix = prefix.strip()
        clause_words = re.findall(r"[a-z]+", clause)
        if clause_words and all(w in _HUB_MATCH_TRAILING_CLAUSE_SAFE_WORDS for w in clause_words):
            match = _exact_hub_match(prefix, hub_titles)
            if match:
                return match
            key = prefix

    words = key.split()
    while len(words) > 1 and words[0] in _HUB_MATCH_LEADING_SAFE_WORDS:
        words = words[1:]
        match = _exact_hub_match(" ".join(words), hub_titles)
        if match:
            return match

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


def _resolved_category_roundup_cards(db: Session, page: Page) -> list[dict]:
    """A category_roundup page's own recipe_cards, enriched exactly the
    way get_page()'s single-page response enriches them: any still
    slug-less card gets filled in via live title-matching against a real
    recipe whose category_link already points here (recipe_cards is
    hand-curated editorial content that deliberately includes aspirational
    cards for dishes the site hasn't written yet, so this only ever adds
    or fills in, never removes or reorders), then every linked card's
    image is synced straight from its own recipe -- a card the reader can
    click through to a real page should always show that exact page's
    photo, not a different, possibly stale stock result from the card's
    own independent image search.

    Factored out of get_page() so a second caller, _summary_image() (the
    homepage carousel / section-index thumbnail path, via list_pages()),
    can resolve the exact same first-card image get_page()'s own
    single-page response already shows, instead of reading recipe_cards
    straight off the stored row. A real bug, confirmed live: a
    collection's homepage tile kept showing an unrelated, independently-
    searched stock photo for its first card long after the collection's
    own detail page was fixed to show the right one -- that earlier fix
    only ever enriched get_page()'s response for that one request, never
    the stored row this second code path reads directly."""
    content = page.content
    cards = copy.deepcopy(content.get("recipe_cards", []))
    existing_slugs = {c.get("slug") for c in cards if c.get("slug")}
    cards_by_title = {_normalize_dish_title(c.get("title", "")): c for c in cards}
    # _recipes_linking_to reads recipe_or_dish pages from the process cache
    # (see _cached_pages) -- fine for category_link, title, and
    # why_it_works, which never change once a process starts, but NOT for
    # image_url/image_attribution, which the background image-fetch loop
    # writes at runtime. So this loop deliberately leaves a new or newly-
    # filled card's image fields unset rather than copying a cached (and
    # potentially long-stale) rc.get("image_url") -- the sync pass right
    # below does a fresh, uncached lookup for every linked card instead.
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
    linked_cards = [c for c in cards if c.get("slug")]
    if linked_cards:
        recipes_by_slug = {
            r.slug: r
            for r in db.query(Page)
            .filter(Page.slug.in_({c["slug"] for c in linked_cards}))
            .all()
        }
        for card in linked_cards:
            recipe = recipes_by_slug.get(card["slug"])
            if recipe is not None and recipe.content.get("image_url"):
                card["image_url"] = recipe.content.get("image_url")
                card["image_attribution"] = recipe.content.get("image_attribution")
    return cards


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
    # content["unpublished"] is a deliberate, explicit per-page opt-out
    # (see e.g. swordfish-recipes) -- not found is exactly the right
    # response, indistinguishable from a slug that was never seeded at
    # all, rather than a distinct "page exists but hidden" status that
    # would need its own frontend handling.
    if page.content.get("unpublished"):
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
        content = copy.deepcopy(page.content)
        content["recipe_cards"] = _resolved_category_roundup_cards(db, page)
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


def _summary_image(page: Page, db: Session) -> tuple[str | None, dict | None, str | None, str | None]:
    """image_url, image_attribution, hero_image_query, image_alt for a
    page's summary thumbnail. Category Roundup pages have no hero image of
    their own (only per-card images on recipe_cards), so this falls back to
    the first card's image (and that card's own image_alt) as a
    representative thumbnail for the collection -- resolved via the same
    live title-matching + per-card image sync get_page() itself applies
    (see _resolved_category_roundup_cards), not the raw stored row, which
    can carry a stale or still slug-less first card for a companion recipe
    generated after the collection was first published."""
    content = page.content
    if content.get("image_url"):
        return (
            content["image_url"],
            content.get("image_attribution"),
            content.get("hero_image_query"),
            content.get("image_alt"),
        )
    cards = _resolved_category_roundup_cards(db, page) if page.template_type == "category_roundup" else content.get("recipe_cards")
    if cards:
        first = cards[0]
        return first.get("image_url"), first.get("image_attribution"), first.get("image_query"), first.get("image_alt")
    return None, None, content.get("hero_image_query"), content.get("image_alt")


@app.get("/pages")
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
    lean: bool = Query(
        default=False,
        description=(
            "Skip image_url/image_attribution entirely (always null) and "
            "serve from the same process-lifetime cache _cached_pages() "
            "uses for /pages/{slug}'s cross-linking, instead of a live "
            "query -- for a caller that only needs slug/title/link_terms "
            "and never touches photo data, e.g. the site-wide auto-linking "
            "dictionary (getLinkTerms), which used to run 4 full, "
            "uncached template_type scans on every single content page "
            "view. Safe with no staleness risk for the same reason "
            "_cached_pages() is: title/slug/link_terms never change at "
            "runtime, unlike image_url. Requires template_type (the cache "
            "is keyed per template_type); ignores q/slugs/limit/offset."
        ),
    ),
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    paged: bool = Query(
        default=False,
        description=(
            "Opt-in cursor-based response shape: {items, next_offset, "
            "has_more} instead of a bare list. See list_pages()'s own "
            "comment on the limit/offset branch for why the bare-list "
            "shape can silently under-fill a page and stop 'Load more' "
            "early -- existing callers that pass limit/offset without "
            "this flag (the homepage carousels) keep that exact behavior "
            "unchanged, since a static, non-paginated carousel can't "
            "compound the bug the way repeated 'Load more' calls do."
        ),
    ),
    db: Session = Depends(get_db),
):
    if lean:
        if template_type is None:
            raise HTTPException(status_code=400, detail="lean requires template_type")
        return [
            PageSummary(
                slug=page.slug,
                template_type=template_type,
                title=page.title,
                link_terms=page.content.get("link_terms") if template_type == "definition" else None,
            )
            for page in _cached_pages(db, template_type)
        ]

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
    base_query = db.query(Page).order_by(Page.id.desc())
    if template_type is not None:
        base_query = base_query.filter(Page.template_type == template_type)
    if slugs is not None:
        base_query = base_query.filter(Page.slug.in_([s for s in slugs.split(",") if s]))
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
        base_query = base_query.filter(Page.title.ilike(f"%{q}%"), Page.template_type != "homepage")

    def _build_summary(page: Page) -> PageSummary:
        image_url, image_attribution, hero_image_query, image_alt = _summary_image(page, db)
        return PageSummary(
            slug=page.slug,
            template_type=page.template_type,
            title=page.title,
            image_url=image_url,
            image_attribution=image_attribution,
            hero_image_query=hero_image_query,
            image_alt=image_alt,
            link_terms=page.content.get("link_terms") if page.template_type == "definition" else None,
        )

    if paged and limit is not None:
        # A raw SQL OFFSET/LIMIT can't see content["unpublished"] (a JSON
        # field, not a queryable column) -- so a plain `.offset(offset)
        # .limit(limit)` batch that happens to contain an unpublished page
        # comes back shorter than `limit` even though more published pages
        # exist further on. PagedPageGrid.tsx took "got back fewer than I
        # asked for" as "there's nothing left" and stopped offering "Load
        # more" -- confirmed live: /food/recipes stopped at 71 of the 929
        # real recipe_or_dish rows, because a "Load more" batch somewhere
        # in that range happened to contain an unpublished page.
        #
        # Fetching in a loop here, expanding the raw window (tracked as
        # `raw_offset`, not `len(items)`) until `limit` published items are
        # collected or a fetched batch itself comes back shorter than
        # `limit` (the only reliable "no more raw rows" signal -- SQL only
        # returns a short batch at the true end of the matching set), means
        # the only way this endpoint returns fewer than `limit` items is
        # genuinely reaching the end. `next_offset` is the real raw-row
        # cursor for the next call, not a published-item count, since those
        # two diverge the moment any row in between was unpublished.
        items: list[PageSummary] = []
        raw_offset = offset
        exhausted = False
        while len(items) < limit:
            batch = base_query.offset(raw_offset).limit(limit).all()
            if not batch:
                exhausted = True
                break
            consumed = 0
            for page in batch:
                consumed += 1
                if page.content.get("unpublished"):
                    continue
                items.append(_build_summary(page))
                if len(items) >= limit:
                    break
            raw_offset += consumed
            if len(batch) < limit:
                exhausted = True
                break
        return {
            "items": items,
            "next_offset": raw_offset,
            "has_more": not exhausted and len(items) >= limit,
        }

    # Unchanged legacy behavior (no `paged` flag) -- still used by the
    # homepage carousels and any other limit/offset caller that hasn't
    # opted into the cursor-based shape above. A static, non-paginated
    # carousel can under-fill by at most a couple of items if an unpublished
    # page lands in its one fixed batch; it doesn't compound the way
    # repeated "Load more" calls do, so it's lower priority to migrate.
    query = base_query
    if limit is not None:
        query = query.offset(offset).limit(limit)

    summaries = []
    for page in query.all():
        if page.content.get("unpublished"):
            continue
        summaries.append(_build_summary(page))
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
            image_url, image_attribution, hero_image_query, image_alt = _summary_image(page, db)
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

# Outreach-specific admin auth -- deliberately a SEPARATE credential from
# ADMIN_TASK_TOKEN above, not a reuse of it. Every other /admin/* route
# guards an occasional maintenance action (re-fetch a photo, flag a page)
# where a URL-embedded token leaking into a server/proxy log is a modest,
# accepted risk. The outreach portal is different in kind: it will
# eventually hold real third-party contact data and gate real sends, so a
# real approve/reject decision deserves a real credential a browser
# doesn't echo back into every log line and Referer header the way a
# query param does. HTTPBasic is the smallest real step up available
# without building a login/session system this codebase has nowhere else
# -- the browser prompts once and remembers it, and the credential travels
# in an Authorization header instead of the URL.
#
# Every other /admin/* route returns a bare 404 on a bad token specifically
# to avoid confirming "this route exists, you just got the credential
# wrong" to anyone probing it. Basic Auth can't preserve that: a browser
# will only show its username/password prompt in response to a real 401
# with a WWW-Authenticate challenge, so _require_outreach_auth below
# trades that particular stealth property, on these routes only, for
# actual auth stronger than a URL token -- a deliberate, scoped exception,
# not an oversight.
OUTREACH_ADMIN_USER = os.environ.get("OUTREACH_ADMIN_USER")
OUTREACH_ADMIN_PASSWORD = os.environ.get("OUTREACH_ADMIN_PASSWORD")
_outreach_basic_auth = HTTPBasic(auto_error=False)


def _require_outreach_auth(credentials: HTTPBasicCredentials | None = Depends(_outreach_basic_auth)) -> None:
    """FastAPI dependency guarding every /admin/outreach-queue* route.
    404s (not 401) when the feature is simply unconfigured -- same
    "inert without setup" convention as ADMIN_TASK_TOKEN elsewhere in this
    file -- so the outreach portal is unreachable, not half-open, until
    OUTREACH_ADMIN_USER/OUTREACH_ADMIN_PASSWORD are both set."""
    if not OUTREACH_ADMIN_USER or not OUTREACH_ADMIN_PASSWORD:
        raise HTTPException(status_code=404)
    valid = (
        credentials is not None
        and secrets.compare_digest(credentials.username, OUTREACH_ADMIN_USER)
        and secrets.compare_digest(credentials.password, OUTREACH_ADMIN_PASSWORD)
    )
    if not valid:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic realm=\"outreach\""})


# Real Snov.io send integration, written against their published API docs
# (client provided the full doc text directly -- not guessed at, unlike
# the CSV-export fallback this replaces for tool_pitch prospects). Three
# separate env vars, deliberately not reusing any other credential:
#   SNOV_CLIENT_ID / SNOV_CLIENT_SECRET -- OAuth2 client_credentials pair
#     from https://app.snov.io/account/api.
#   SNOV_LIST_ID -- the Snov.io prospect list to add approved prospects
#     to. Created once, by hand, in the Snov.io dashboard, along with the
#     drip campaign that must already be marked active against that list
#     -- per Snov.io's own docs, add-prospect-to-list is exactly the
#     "automate adding prospects to lists with active email drip
#     campaigns" pattern, so an active campaign on this list is what
#     actually sends anything; this code only ever adds the prospect.
#
# IMPORTANT CAVEAT, not yet resolved: this has been verified against the
# documented request/response shapes and compiles/type-checks, but could
# NOT be exercised against a live api.snov.io call from this environment
# -- both snov.io and api.snov.io are blocked by this environment's own
# egress proxy (confirmed earlier via a direct curl, 403 from the proxy
# itself). The first real approval after these env vars are set is this
# integration's actual first live test; watch send_error on that first
# approved prospect.
SNOV_CLIENT_ID = os.environ.get("SNOV_CLIENT_ID")
SNOV_CLIENT_SECRET = os.environ.get("SNOV_CLIENT_SECRET")
SNOV_LIST_ID = os.environ.get("SNOV_LIST_ID")

# Process-lifetime cache for the OAuth bearer token -- documented as
# valid for 3600 seconds; refetched with a 5-minute safety margin rather
# than on every single send, same "don't redo cheap-to-cache work every
# request" reasoning as _cached_pages() elsewhere in this file.
_snov_token_cache: dict[str, object] = {"token": None, "expires_at": 0.0}


def _get_snov_access_token() -> str:
    """POST https://api.snov.io/v1/oauth/access_token, client_credentials
    grant. Raises requests.HTTPError / requests.RequestException on
    failure -- callers (only _add_prospect_to_snov_list below) are
    expected to catch and record it, never let a Snov.io outage break the
    approve action itself."""
    if _snov_token_cache["token"] and time.time() < float(_snov_token_cache["expires_at"]):
        return _snov_token_cache["token"]  # type: ignore[return-value]

    response = requests.post(
        "https://api.snov.io/v1/oauth/access_token",
        data={
            "grant_type": "client_credentials",
            "client_id": SNOV_CLIENT_ID,
            "client_secret": SNOV_CLIENT_SECRET,
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    _snov_token_cache["token"] = data["access_token"]
    _snov_token_cache["expires_at"] = time.time() + data["expires_in"] - 300
    return data["access_token"]


def _add_prospect_to_snov_list(prospect: OutreachProspect) -> None:
    """POST https://api.snov.io/v1/add-prospect-to-list -- per Snov.io's
    own docs, adding a prospect to a list with an already-active drip
    campaign automatically enrolls and starts that campaign for them.
    Sets prospect.sent_at on success or prospect.send_error on failure;
    never raises, so a Snov.io-side problem shows up as a visible error
    on the prospect in the portal instead of breaking the approve action.
    Caller is responsible for the actual db.commit()."""
    if not (SNOV_CLIENT_ID and SNOV_CLIENT_SECRET and SNOV_LIST_ID):
        return  # Not configured -- approving just records the decision, same as before this existed.
    if not prospect.contact_email:
        prospect.send_error = "No contact_email set -- can't add to Snov.io without one."
        return

    try:
        token = _get_snov_access_token()
        name_parts = (prospect.contact_name or "").split(maxsplit=1)
        first_name, last_name = (name_parts + [""])[:2] if name_parts else ("", "")

        response = requests.post(
            "https://api.snov.io/v1/add-prospect-to-list",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "email": prospect.contact_email,
                "fullName": prospect.contact_name or "",
                "firstName": first_name,
                "lastName": last_name,
                "companySite": f"https://{prospect.target_domain}" if prospect.target_domain else "",
                "updateContact": "true",
                "listId": SNOV_LIST_ID,
            },
            timeout=15,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("success"):
            prospect.sent_at = datetime.now(timezone.utc)
            prospect.send_error = None
        else:
            prospect.send_error = str(result.get("errors") or "Snov.io returned success=false with no error detail.")
    except requests.RequestException as e:
        prospect.send_error = f"Snov.io request failed: {e}"
    except (KeyError, ValueError) as e:
        prospect.send_error = f"Unexpected Snov.io response shape: {e}"


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


@app.get("/admin/content-audit")
def content_audit(token: str, db: Session = Depends(get_db)):
    """Site-wide content quality report combining three checks in one
    pass, so a new batch can be verified before it reaches manual review
    instead of relying on someone clicking through pages one at a time and
    reporting problems as they're found (see content_audit.py's own
    docstring for the debugging session that motivated this):

    - image completeness (a thin wrapper around the same missing/broken
      logic as /admin/image-audit above)
    - image relevance risk (a heuristic scan for the same real wrong-photo
      patterns found by hand this session -- homonym collisions,
      vessel-dominant queries, a weak/generic-only match term -- returned
      as `review` for score>=2 stacked-signal pages and `low_confidence`
      for a single weak signal, since a standalone signal alone isn't
      itself evidence of a bad photo, see that function's docstring)
    - AI-writing-tell phrasing, split into `blocking` (a small,
      near-zero-false-positive list already enforced at import time by
      seed_templates.py -- reported here too so a live run surfaces the
      same thing without needing a redeploy) and `advisory` (softer
      marketing-cliche constructions needing a human judgment call)

    `clean` is true only when there's nothing in missing/broken image
    completeness and no blocking AI-tell matches -- image relevance risk
    and advisory AI tells never affect it, since both are inherently
    judgment calls, not hard failures.

    Same tool as `python -m app.content_audit` (see that module), exposed
    over HTTP so it can run against a real deployment without shell
    access to it -- gated behind the same ADMIN_TASK_TOKEN as every other
    /admin/* route.
    """
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    return run_full_audit(db)


# Mirrors frontend/lib/seo.ts's TEMPLATE_ROUTES -- the one other place
# this mapping is defined. Kept as its own small copy here rather than
# threaded through from the frontend (there's no shared package between
# the two apps to put it in). Originally just for building a human-facing
# link in the admin image-review tools below; also backs the public
# /redirects endpoint now, so no longer admin-only despite the name's
# old history.
_FRONTEND_TEMPLATE_ROUTES: dict[str, str] = {
    "recipe_or_dish": "recipes",
    "ingredient_hub": "ingredients",
    "howto_technique": "how-to",
    "definition": "what-is",
    "comparison": "comparisons",
    "substitute": "substitutes",
    "category_roundup": "collections",
    "tool_page": "tools",
}


def _frontend_page_path(template_type: str, slug: str) -> str:
    if template_type == "homepage":
        return "/"
    if template_type == "static_page":
        return f"/{slug}"
    prefix = _FRONTEND_TEMPLATE_ROUTES.get(template_type)
    return f"/food/{prefix}/{slug}" if prefix else f"/food/{slug}"


@app.get("/redirects")
def list_redirects(db: Session = Depends(get_db)):
    """Public, unauthenticated -- {source, destination} path pairs for
    every page that's been unpublished as a duplicate of another, still-
    published page. content["redirect_to"] (a slug), set alongside
    content["unpublished"] (see seed_templates.py's own convention), is
    the one thing this reads.

    Read by frontend/next.config.mjs's redirects() at build time, the
    same mechanism that already backs this site's hand-maintained
    permanent redirects (e.g. /food/vs -> /food/comparisons) -- this just
    computes entries instead of requiring a next.config.mjs edit every
    time a duplicate gets unpublished, which would be easy to forget (a
    real, confirmed-live gap: quick-pickled-beets was unpublished as a
    duplicate of pickled-beets with no redirect at all, so an old link or
    bookmark to it 404s outright rather than landing on the real page).

    Only ever returns a redirect whose destination is a real, currently-
    published page -- redirect_to naming an unpublished, deleted, or
    nonexistent slug is skipped rather than ever sending a reader to
    another dead end or into a loop.
    """
    pages_by_slug = {p.slug: p for p in db.query(Page).all()}
    redirects = []
    for page in pages_by_slug.values():
        target_slug = page.content.get("redirect_to")
        if not target_slug:
            continue
        target = pages_by_slug.get(target_slug)
        if target is None or target.content.get("unpublished"):
            continue
        redirects.append(
            {
                "source": _frontend_page_path(page.template_type, page.slug),
                "destination": _frontend_page_path(target.template_type, target.slug),
            }
        )
    return redirects


@app.get("/admin/image-relevance-review", response_class=HTMLResponse)
def image_relevance_review(token: str, db: Session = Depends(get_db)):
    """The same score>=2 image-relevance-risk list content_audit.py's
    scan_image_relevance_risk() returns, rendered as an actual visual
    grid instead of raw JSON/CSV -- built after handing over a CSV of
    signal labels made for a slower, less useful review pass than
    actually looking at each flagged photo and clicking straight through
    to the live page. Each card shows the page's current photo (pulled
    live from the database -- scan_image_relevance_risk() itself only
    sees seed_templates.py's static content, which never has image_url),
    its risk signals, and a link to both the live page and its
    /admin/debug-page-image view for a deeper look. Not meant to be a
    permanent route.
    """
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    risk = scan_image_relevance_risk(SEED_PAGES)
    review = sorted([r for r in risk if r["score"] >= 2], key=lambda r: -r["score"])

    slugs = [r["slug"] for r in review]
    pages_by_slug = {p.slug: p for p in db.query(Page).filter(Page.slug.in_(slugs)).all()}

    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

    cards = []
    for r in review:
        page = pages_by_slug.get(r["slug"])
        content = page.content if page else {}
        image_url = content.get("image_url")
        img_html = (
            f'<img src="{image_url}" alt="">'
            if image_url
            else '<div class="no-image">no image_url</div>'
        )
        live_url = f"{frontend_origin}{_frontend_page_path(r['template_type'], r['slug'])}"
        debug_url = f"/admin/debug-page-image?token={token}&slug={r['slug']}"
        signals_html = "".join(f"<li>{s}</li>" for s in r["signals"])
        cards.append(f"""
        <div class="card">
          <div class="thumb">{img_html}</div>
          <div class="info">
            <div class="title"><a href="{live_url}" target="_blank">{r['title']}</a> <span class="score">score {r['score']}</span></div>
            <div class="meta">{r['template_type']} &middot; {r['slug']}</div>
            <div class="query">query: {r['query']!r}</div>
            {f'<div class="query">must_match: {r["must_match"]!r}</div>' if r.get('must_match') else ''}
            {f'<div class="query">salient_query: {r["salient_query"]!r}</div>' if r.get('salient_query') else ''}
            <ul class="signals">{signals_html}</ul>
            <div class="links"><a href="{live_url}" target="_blank">live page</a> &middot; <a href="{debug_url}" target="_blank">debug search</a></div>
          </div>
        </div>
        """)

    html = f"""
    <html>
    <head>
      <title>Image relevance review ({len(review)} pages)</title>
      <style>
        body {{ font-family: -apple-system, sans-serif; margin: 24px; background: #fafafa; }}
        h1 {{ font-size: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }}
        .card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; display: flex; }}
        .thumb {{ width: 140px; min-width: 140px; background: #eee; display: flex; align-items: center; justify-content: center; }}
        .thumb img {{ width: 100%; height: 140px; object-fit: cover; }}
        .no-image {{ font-size: 11px; color: #b00; text-align: center; padding: 8px; }}
        .info {{ padding: 10px 12px; font-size: 13px; flex: 1; min-width: 0; }}
        .title {{ font-weight: 600; font-size: 14px; }}
        .title a {{ color: #111; text-decoration: none; }}
        .title a:hover {{ text-decoration: underline; }}
        .score {{ font-weight: 400; color: #b00; font-size: 11px; }}
        .meta {{ color: #888; font-size: 11px; margin: 2px 0 6px; }}
        .query {{ color: #555; font-size: 11px; margin: 2px 0; word-break: break-word; }}
        .signals {{ margin: 6px 0; padding-left: 16px; font-size: 11px; color: #a55; }}
        .links {{ margin-top: 6px; font-size: 12px; }}
        .links a {{ color: #06c; }}
      </style>
    </head>
    <body>
      <h1>Image relevance review -- {len(review)} pages (score&ge;2)</h1>
      <div class="grid">
        {"".join(cards)}
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


def _build_review_rows(batch_pages: list[dict], db: Session) -> list[dict]:
    """The per-page data /admin/review-queue renders as cards, factored out
    so /admin/review-queue/data (a plain-JSON view of the exact same rows)
    doesn't duplicate this query-and-signal-scan logic. Unfiltered and
    unsorted -- both callers apply their own `show` filter and ordering on
    top of this."""
    slugs = [p["slug"] for p in batch_pages]
    db_pages = {p.slug: p for p in db.query(Page).filter(Page.slug.in_(slugs)).all()}
    reviews = {r.slug: r for r in db.query(PageReview).filter(PageReview.slug.in_(slugs)).all()}

    image_risk_by_slug = {r["slug"]: r for r in scan_image_relevance_risk(batch_pages)}
    ai_tells = scan_ai_tells(batch_pages)
    ai_tells_by_slug: dict[str, list[dict]] = {}
    for hit in ai_tells["blocking"] + ai_tells["advisory"]:
        ai_tells_by_slug.setdefault(hit["slug"], []).append(hit)

    rows = []
    for p in batch_pages:
        slug = p["slug"]
        db_page = db_pages.get(slug)
        content = db_page.content if db_page else {}
        image_url = content.get("image_url")
        review = reviews.get(slug)
        status = review.status if review else "pending"
        signals = []
        if not image_url:
            signals.append(("missing image", True))
        risk = image_risk_by_slug.get(slug)
        if risk:
            signals.append((f"image risk (score {risk['score']}): {', '.join(risk['signals'])}", risk["score"] >= 2))
        for hit in ai_tells_by_slug.get(slug, []):
            signals.append((f"AI-tell [{hit['pattern']}]: {hit['excerpt'][:80]!r}", True))
        rows.append({"slug": slug, "title": p["title"], "template_type": p["template_type"],
                      "image_url": image_url, "status": status, "note": review.note if review else None,
                      "reviewed_at": review.reviewed_at.isoformat() if review else None,
                      "signals": signals})
    return rows


# Batches 0-5 are legacy content: real recipe/ingredient/how-to pages
# published the ordinary way (commit to main, merge into staging) long
# before this review queue existed, not new drops awaiting a first-time
# review. Surfacing them here reads as "pending review," which is exactly
# the confusion a reviewer hit in practice -- flagging pages from one of
# these batches expecting it to be new, unreviewed, staging-only content,
# when it had actually been live on both staging and prod for a while.
# The review queue (and everything that shares its batch-number picker)
# only ever surfaces batch_number >= this, starting at the first batch
# daily_batch.py will actually create.
_PIPELINE_START_BATCH = 6


def _eligible_batch_numbers() -> list[int]:
    """Every batch_number in SEED_PAGES that's actually part of the
    review-queue pipeline (see _PIPELINE_START_BATCH), newest first."""
    return sorted(
        {p["batch_number"] for p in SEED_PAGES if p["batch_number"] is not None and p["batch_number"] >= _PIPELINE_START_BATCH},
        reverse=True,
    )


def _resolve_batch_pages(batch: str | None) -> tuple[str | int, list[dict]]:
    """Shared by /admin/review-queue and its approve-remaining action:
    resolves the `batch` query param (a batch_number, the literal "all",
    or unset) to a display label and the matching published pages.
    `batch="all"` is what makes a missed day's backlog reviewable as one
    combined queue instead of forcing a click through each day
    separately -- a page's approve/flag status already lives in
    PageReview keyed only by slug, not by batch, so nothing about
    reviewing across batches at once needed to change except this
    filter. Rejects any batch_number below _PIPELINE_START_BATCH outright
    rather than silently showing legacy content that was never meant to
    be "reviewed" through this tool."""
    all_batches = _eligible_batch_numbers()
    if not all_batches:
        raise HTTPException(status_code=400, detail="No eligible batch_number values found in SEED_PAGES")

    if batch == "all":
        target: str | int = "all"
        pages = [
            p for p in SEED_PAGES
            if p["batch_number"] is not None and p["batch_number"] >= _PIPELINE_START_BATCH and not p["content"].get("unpublished")
        ]
    else:
        target = int(batch) if batch is not None else all_batches[0]
        if target < _PIPELINE_START_BATCH:
            raise HTTPException(
                status_code=400,
                detail=f"batch {target} predates the review pipeline (batches below {_PIPELINE_START_BATCH} are "
                f"legacy content, already fully live on both staging and prod -- nothing to review).",
            )
        pages = [p for p in SEED_PAGES if p["batch_number"] == target and not p["content"].get("unpublished")]
    if not pages:
        raise HTTPException(status_code=404, detail=f"No published pages in batch {target}")
    return target, pages


@app.get("/admin/review-queue", response_class=HTMLResponse)
def review_queue(
    token: str,
    batch: str | None = Query(default=None, description="batch_number to review, or 'all' to combine every batch's pending/flagged backlog; defaults to the newest batch_number present."),
    show: str = Query(default="pending", description="pending | flagged | approved | all"),
    db: Session = Depends(get_db),
):
    """The daily-batch review workflow: everything from one content batch
    (see SEED_PAGES' own batch_number field -- confirmed the right unit to
    scope by, since it already tracks real, distinct content-generation
    runs, not just an incidental count) in one visual queue, each page
    showing its live photo plus every automated quality signal that
    applies to it (image-relevance risk and AI-tell hits from
    content_audit.py, scoped to just this batch rather than the whole
    site -- and unlike /admin/image-relevance-review, a single risk
    signal is worth surfacing here: a fresh ~100-page batch is small
    enough that noise tolerance is different from a full ~2,100-page
    site scan), with a one-click Approve/Flag action per page so a
    reviewer's progress persists across visits instead of starting over
    each time (see PageReview in models.py).

    Defaults to the newest batch_number and to `show=pending` (the actual
    day's work queue) -- flagged pages always render regardless of `show`,
    since a flag is exactly the thing a reviewer shouldn't lose track of.
    Runs against whichever database this deployment points at, so hitting
    this on the staging backend reviews staging's own fetched photos
    before a batch's images get baked into seed_templates.py and merged
    to main (see /admin/export-images below) -- no separate "staging
    mode" needed, it falls out of the existing per-environment deploy.

    Does not gate publishing itself -- see PageReview's own docstring for
    why flagging is a checklist, not an enforcement mechanism.
    """
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    target_batch, batch_pages = _resolve_batch_pages(batch)
    slugs = [p["slug"] for p in batch_pages]
    all_batches = _eligible_batch_numbers()

    all_rows = _build_review_rows(batch_pages, db)
    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

    rows = all_rows if show == "all" else [r for r in all_rows if r["status"] == "flagged" or (show == r["status"])]
    # Flagged always first regardless of sort, then anything with a live signal, then the rest.
    rows.sort(key=lambda r: (r["status"] != "flagged", not r["signals"], r["status"] != "pending"))

    counts = Counter(r["status"] for r in all_rows)

    approval = None
    if isinstance(target_batch, int):
        approval = db.query(BatchApproval).filter(BatchApproval.batch_number == target_batch).first()
    fully_approved = counts.get("approved", 0) == len(slugs)
    if approval is not None and approval.merged_at is not None:
        promo_status_html = f'<span class="pill pill-approved">merged to prod {approval.merged_at:%Y-%m-%d}</span>'
        promo_cta_html = ""
    elif approval is not None:
        # A request that's been sitting unmerged for a while almost always
        # means the GitHub Actions dispatch didn't land (it's a
        # best-effort, silent-on-failure call -- see _trigger_batch_merge)
        # -- e.g. the exact bug hit during setup, where the workflow
        # wasn't registered on GitHub's side yet. Re-hitting
        # approve-for-prod is a safe no-op on the BatchApproval row itself
        # and re-fires the dispatch, so surface it as a real retry action
        # rather than leaving the reviewer with a dead-end status pill and
        # no way to unstick it without a raw URL.
        promo_status_html = f'<span class="pill pill-pending">requested {approval.requested_at:%Y-%m-%d %H:%M}, waiting for merge</span>'
        promo_cta_html = (
            f'<a class="btn-approve-prod" '
            f'href="/admin/review-queue/approve-for-prod?token={token}&batch={target_batch}">Retry merge dispatch</a>'
        )
    elif isinstance(target_batch, int):
        promo_status_html = ""
        promo_cta_html = (
            f'<a class="btn-approve-prod{"" if fully_approved else " disabled"}" '
            f'href="/admin/review-queue/approve-for-prod?token={token}&batch={target_batch}">Approve batch {target_batch} for prod</a>'
        )
    else:
        promo_status_html = ""
        promo_cta_html = '<span style="font-size:12px;color:#888;">pick a single batch above to approve it for prod</span>'

    def card(r: dict) -> str:
        img_html = f'<img src="{r["image_url"]}" alt="">' if r["image_url"] else '<div class="no-image">no image_url</div>'
        live_url = f"{frontend_origin}{_frontend_page_path(r['template_type'], r['slug'])}"
        debug_url = f"/admin/debug-page-image?token={token}&slug={r['slug']}"
        signals_html = "".join(f'<li class="{"crit" if crit else ""}">{s}</li>' for s, crit in r["signals"])
        note_html = f'<div class="note">note: {r["note"]}</div>' if r["note"] else ""
        return f"""
        <div class="card status-{r['status']}">
          <div class="thumb">{img_html}</div>
          <div class="info">
            <div class="title"><a href="{live_url}" target="_blank">{r['title']}</a> <span class="pill pill-{r['status']}">{r['status']}</span></div>
            <div class="meta">{r['template_type']} &middot; {r['slug']}</div>
            {f'<ul class="signals">{signals_html}</ul>' if signals_html else ''}
            {note_html}
            <div class="links"><a href="{live_url}" target="_blank">live</a> &middot; <a href="{debug_url}" target="_blank">debug search</a></div>
            <form method="get" action="/admin/review-queue/mark" class="mark-form">
              <input type="hidden" name="token" value="{token}">
              <input type="hidden" name="slug" value="{r['slug']}">
              <input type="hidden" name="batch" value="{target_batch}">
              <input type="hidden" name="show" value="{show}">
              <input type="text" name="note" placeholder="describe the photo you want -- used as the re-search (optional)" value="{r['note'] or ''}">
              <button type="submit" name="status" value="flagged" class="btn-flag">Flag</button>
              <button type="submit" name="status" value="approved" class="btn-approve-one">approve just this one</button>
            </form>
            <form method="get" action="/admin/review-queue/override-image" class="override-form">
              <input type="hidden" name="token" value="{token}">
              <input type="hidden" name="slug" value="{r['slug']}">
              <input type="hidden" name="batch" value="{target_batch}">
              <input type="hidden" name="show" value="{show}">
              <input type="text" name="image_url" placeholder="paste an exact images.pexels.com/... or images.unsplash.com/... URL">
              <button type="submit" class="btn-override">use this photo</button>
            </form>
          </div>
        </div>
        """

    batch_label = "all batches" if target_batch == "all" else f"batch {target_batch}"
    batch_links = " &middot; ".join(
        [f'<a href="/admin/review-queue?token={token}&batch=all&show={show}">{"<b>all batches</b>" if target_batch == "all" else "all batches"}</a>']
        + [
            f'<a href="/admin/review-queue?token={token}&batch={b}&show={show}">{"batch " + str(b) if b != target_batch else f"<b>batch {b}</b>"}</a>'
            for b in all_batches
        ]
    )

    html = f"""
    <html>
    <head>
      <title>Review queue — {batch_label}</title>
      <style>
        body {{ font-family: -apple-system, sans-serif; margin: 24px; background: #fafafa; }}
        h1 {{ font-size: 20px; margin-bottom: 4px; }}
        .subnav {{ font-size: 13px; color: #666; margin-bottom: 6px; }}
        .summary {{ font-size: 13px; color: #444; margin-bottom: 18px; }}
        .filters a {{ margin-right: 10px; font-size: 13px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }}
        .card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; display: flex; }}
        .card.status-flagged {{ border-color: #c33; box-shadow: 0 0 0 1px #c33; }}
        .card.status-approved {{ opacity: 0.6; }}
        .thumb {{ width: 140px; min-width: 140px; background: #eee; display: flex; align-items: center; justify-content: center; }}
        .thumb img {{ width: 100%; height: 140px; object-fit: cover; }}
        .no-image {{ font-size: 11px; color: #b00; text-align: center; padding: 8px; }}
        .info {{ padding: 10px 12px; font-size: 13px; flex: 1; min-width: 0; }}
        .title {{ font-weight: 600; font-size: 14px; }}
        .title a {{ color: #111; text-decoration: none; }}
        .pill {{ font-size: 10px; padding: 1px 7px; border-radius: 20px; margin-left: 4px; font-weight: 400; }}
        .pill-pending {{ background: #eee; color: #666; }}
        .pill-flagged {{ background: #fbdada; color: #a00; }}
        .pill-approved {{ background: #dcefe0; color: #276b3c; }}
        .meta {{ color: #888; font-size: 11px; margin: 2px 0 6px; }}
        .signals {{ margin: 6px 0; padding-left: 16px; font-size: 11px; color: #a55; }}
        .signals .crit {{ color: #c00; font-weight: 600; }}
        .note {{ font-size: 11px; color: #555; font-style: italic; margin: 4px 0; }}
        .links {{ margin: 6px 0; font-size: 12px; }}
        .links a {{ color: #06c; }}
        .mark-form {{ display: flex; gap: 6px; margin-top: 8px; align-items: center; }}
        .mark-form input[type=text], .override-form input[type=text] {{ flex: 1; min-width: 0; font-size: 12px; padding: 4px 6px; border: 1px solid #ccc; border-radius: 4px; }}
        .btn-approve-one {{ background: none; border: none; color: #888; font-size: 11px; cursor: pointer; text-decoration: underline; padding: 0; }}
        .btn-flag {{ background: #b23; color: #fff; border: none; border-radius: 4px; padding: 5px 10px; font-size: 12px; cursor: pointer; white-space: nowrap; }}
        .override-form {{ display: flex; gap: 6px; margin-top: 6px; align-items: center; }}
        .btn-override {{ background: #555; color: #fff; border: none; border-radius: 4px; padding: 5px 10px; font-size: 11px; cursor: pointer; white-space: nowrap; }}
        .action-bar {{ display: flex; align-items: center; gap: 16px; margin: 14px 0 22px; }}
        .btn-approve-all {{ background: #2f7d43; color: #fff; border: none; border-radius: 6px; padding: 10px 18px; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; }}
        .btn-approve-all.disabled {{ background: #ccc; pointer-events: none; }}
        .promo-bar {{ display: flex; align-items: center; gap: 16px; margin: 0 0 22px; padding: 14px 18px; background: #eef6f0; border: 1px solid #cde3d3; border-radius: 8px; }}
        .btn-approve-prod {{ background: #1c4d99; color: #fff; border: none; border-radius: 6px; padding: 10px 18px; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; }}
        .btn-approve-prod.disabled {{ background: #ccc; pointer-events: none; }}
      </style>
    </head>
    <body>
      <h1>Review queue — {batch_label}</h1>
      <div class="subnav">{batch_links}</div>
      <div class="summary">{len(slugs)} pages in batch &middot; {counts.get('pending', 0)} pending &middot; {counts.get('flagged', 0)} flagged &middot; {counts.get('approved', 0)} approved</div>
      <div class="action-bar">
        <a class="btn-approve-all{' disabled' if counts.get('pending', 0) == 0 else ''}" href="/admin/review-queue/approve-remaining?token={token}&batch={target_batch}&show={show}">Approve all remaining ({counts.get('pending', 0)})</a>
        <span style="font-size:12px;color:#888;">Flag the ones that look wrong below first, then hit this once for the rest.</span>
      </div>
      <div class="promo-bar">
        {promo_cta_html}
        {promo_status_html}
        {'' if (fully_approved or promo_status_html) else '<span style="font-size:12px;color:#888;">every page in this batch needs to be approved (no pending, no flagged) before this unlocks.</span>'}
      </div>
      <div class="filters">
        <a href="/admin/review-queue?token={token}&batch={target_batch}&show=pending">pending</a>
        <a href="/admin/review-queue?token={token}&batch={target_batch}&show=flagged">flagged</a>
        <a href="/admin/review-queue?token={token}&batch={target_batch}&show=approved">approved</a>
        <a href="/admin/review-queue?token={token}&batch={target_batch}&show=all">all</a>
      </div>
      <div class="grid">
        {"".join(card(r) for r in rows)}
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/admin/review-queue/data")
def review_queue_data(
    token: str,
    batch: str | None = Query(default=None, description="batch_number, or 'all'; defaults to the newest eligible batch_number."),
    show: str = Query(default="flagged", description="pending | flagged | approved | all"),
    db: Session = Depends(get_db),
):
    """Plain-JSON twin of /admin/review-queue, built specifically so a
    Claude Code session (or anything else automated) can read exactly what
    a reviewer flagged -- slug, title, and note -- without anyone needing
    to copy-paste it out of the HTML page by hand. Same data, same
    _resolve_batch_pages/_build_review_rows the HTML view uses; this is
    just the machine-readable shape of it. Defaults to show=flagged since
    "what did the reviewer flag and why" is the thing worth polling for."""
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    target_batch, batch_pages = _resolve_batch_pages(batch)
    all_rows = _build_review_rows(batch_pages, db)
    rows = all_rows if show == "all" else [r for r in all_rows if r["status"] == "flagged" or (show == r["status"])]

    return {
        "batch": target_batch,
        "counts": dict(Counter(r["status"] for r in all_rows)),
        "pages": [
            {
                "slug": r["slug"],
                "title": r["title"],
                "template_type": r["template_type"],
                "status": r["status"],
                "note": r["note"],
                "reviewed_at": r["reviewed_at"],
                "signals": [{"text": text, "critical": critical} for text, critical in r["signals"]],
            }
            for r in rows
        ],
    }


@app.get("/admin/review-queue/mark")
def review_queue_mark(
    token: str,
    slug: str,
    status: str,
    batch: str,
    show: str = "pending",
    note: str = "",
    db: Session = Depends(get_db),
):
    """Upserts one PageReview row -- the write side of /admin/review-queue
    above, for the one action that's still worth a deliberate per-page
    click: flagging an exception. (Approving is the batch action below --
    reviewing ~100 pages a day by clicking Approve on every single one
    that's actually fine defeats the point of a queue; flag the bad ones,
    then clear the rest in one click.) A plain GET link + redirect, same
    convention as every other mutating /admin/* endpoint in this file
    (e.g. /admin/fetch-images) -- these are internal, token-gated tools,
    not user-facing forms, so a POST-only-for-mutations rule doesn't buy
    anything here and a GET form avoids a multipart-parsing dependency
    this deploy doesn't otherwise need.

    Flagging also immediately re-fetches this one page's image (see
    fetch_images' only_slugs param -- it already excludes the page's own
    current photo from the new search, exactly "try something other than
    the one that's wrong" with zero new logic needed) so the reviewer
    sees a fresh candidate on the very next page load instead of the same
    bad photo staring back at them. The note field doubles as that
    re-fetch's search text (see fetch_images' query_overrides) -- the note
    has no other purpose in this tool, so a reviewer typing what's
    actually wrong ("raw eggplant, need it baked as parmesan") gets that
    used as the next search instead of just being commentary. Best-effort:
    a search hiccup here (rate limit, network error -- fetch_images
    already catches and logs per-page errors internally) never blocks
    saving the flag itself, since the note is the part of this action
    that must never get lost."""
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)
    if status not in ("approved", "flagged"):
        raise HTTPException(status_code=400, detail="status must be 'approved' or 'flagged'")

    review = db.query(PageReview).filter(PageReview.slug == slug).first()
    if review is None:
        review = PageReview(slug=slug)
        db.add(review)
    review.status = status
    review.note = note or None
    db.commit()

    if status == "flagged":
        try:
            query_overrides = {slug: note.strip()} if note.strip() else None
            fetch_images(db, only_slugs={slug}, query_overrides=query_overrides)
        except Exception as e:
            print(f"  review-queue auto-refetch for {slug} failed: {e}")

    return RedirectResponse(url=f"/admin/review-queue?token={token}&batch={batch}&show={show}", status_code=303)


@app.get("/admin/review-queue/override-image")
def review_queue_override_image(
    token: str,
    slug: str,
    image_url: str,
    batch: str,
    show: str = "pending",
    db: Session = Depends(get_db),
):
    """Manual escape hatch for when an automatic re-fetch (see
    review_queue_mark above) doesn't find the right photo either: the
    reviewer already knows the exact photo they want -- the same
    paste-a-Pexels-URL workflow done by hand in chat throughout this
    project -- and applies it directly here instead, no search involved,
    no chat needed. Needs the direct image CDN URL (images.pexels.com/...
    or images.unsplash.com/...), not a pexels.com/photo/... page link --
    same ALLOWED_IMAGE_HOSTS next/image itself requires, checked here
    with the same is_allowed_image_url/_is_reachable guarantees a normal
    fetch gives, just skipping the search step entirely."""
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)
    if not is_allowed_image_url(image_url):
        raise HTTPException(
            status_code=400,
            detail=f"Needs the direct image URL, starting with one of {ALLOWED_IMAGE_HOSTS} -- not a photo page link.",
        )
    if not _is_reachable(image_url):
        raise HTTPException(status_code=400, detail="That URL didn't load -- double check it's the direct image URL.")

    page = db.query(Page).filter(Page.slug == slug).first()
    if page is None:
        raise HTTPException(status_code=404, detail=f"No page with slug {slug}")
    content = copy.deepcopy(page.content)
    content["image_url"] = image_url
    content["image_attribution"] = {"photographer": None, "photographer_url": None, "source": "manual_override"}
    page.content = content
    db.commit()

    return RedirectResponse(url=f"/admin/review-queue?token={token}&batch={batch}&show={show}", status_code=303)


@app.get("/admin/delete-pages")
def delete_pages(
    token: str,
    slugs: str = Query(..., description="Comma-separated slugs to permanently delete from the database."),
    db: Session = Depends(get_db),
):
    """Real, permanent deletion by slug -- unlike every other /admin/*
    mutation in this file, which works through content["unpublished"]
    (see seed_templates.py's own convention: never hard-delete real
    content, since a page removed from SEED_PAGES entirely becomes a
    permanent orphan -- resync_content() only ever touches a row whose
    slug is STILL present in SEED_PAGES, so it can never clean up
    anything removed outright). This endpoint exists only for rows that
    were never real content to begin with: a throwaway test page whose
    seed_templates.py entry already got hard-deleted (exactly the
    mistake that orphaned merge-pipeline-test-9999 and motivated adding
    this). Refuses to touch any slug still present in SEED_PAGES --
    that's real content, and belongs in a "keep one, unpublish the
    other(s)" flow in seed_templates.py itself, not here."""
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    slug_list = [s.strip() for s in slugs.split(",") if s.strip()]
    if not slug_list:
        raise HTTPException(status_code=400, detail="No slugs given")

    seed_slugs = {p["slug"] for p in SEED_PAGES}
    deleted, refused, not_found = [], [], []
    for slug in slug_list:
        if slug in seed_slugs:
            refused.append(slug)
            continue
        page = db.query(Page).filter(Page.slug == slug).first()
        if page is None:
            not_found.append(slug)
            continue
        db.delete(page)
        deleted.append(slug)
    db.commit()

    return {"deleted": deleted, "refused_still_in_seed_templates": refused, "not_found": not_found}


@app.get("/admin/review-queue/approve-remaining")
def review_queue_approve_remaining(
    token: str,
    batch: str,
    show: str = "pending",
    db: Session = Depends(get_db),
):
    """The primary way a review session actually ends: flag whatever's
    wrong first (mark above), then hit this once to approve every other
    page in the batch (or, with batch=all, every batch's combined
    backlog -- see _resolve_batch_pages) that isn't currently flagged --
    including ones never individually touched. Re-approving an
    already-approved page is a harmless no-op, so this is safe to click
    more than once, e.g. after flagging a couple more on a second pass."""
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    _, batch_pages = _resolve_batch_pages(batch)
    batch_slugs = [p["slug"] for p in batch_pages]
    existing = {r.slug: r for r in db.query(PageReview).filter(PageReview.slug.in_(batch_slugs)).all()}

    for slug in batch_slugs:
        review = existing.get(slug)
        if review is not None and review.status == "flagged":
            continue
        if review is None:
            review = PageReview(slug=slug)
            db.add(review)
        review.status = "approved"
    db.commit()

    return RedirectResponse(url=f"/admin/review-queue?token={token}&batch={batch}&show={show}", status_code=303)


# GitHub repo this deploy's content lives in -- not a secret, just where to
# send the workflow_dispatch call below. GITHUB_ACTIONS_TRIGGER_TOKEN is the
# only credential involved on this side: a fine-grained PAT scoped to this
# one repo with *only* the "Actions: write" permission, which can kick off a
# workflow run but cannot read or push code. The actual git merge happens
# inside GitHub's own runner using its auto-provisioned, run-scoped
# GITHUB_TOKEN -- a git push credential never lives in this always-on
# web service.
_GITHUB_REPO = "ljtavgac/tulo"
_GITHUB_ACTIONS_TRIGGER_TOKEN = os.environ.get("GITHUB_ACTIONS_TRIGGER_TOKEN")


def _trigger_batch_merge(batch_number: int) -> None:
    """Best-effort: ask GitHub Actions to merge this batch right now (see
    .github/workflows/merge-approved-batch.yml). If this fails -- token not
    configured yet, GitHub hiccup, whatever -- it's not fatal: the
    BatchApproval row written by the caller is the durable source of truth,
    and daily_batch.py's own run retries any merged_at IS NULL row it finds
    as a fallback, so a failed dispatch here costs at most a delay to the
    next scheduled run rather than silently losing the approval."""
    if not _GITHUB_ACTIONS_TRIGGER_TOKEN:
        return
    try:
        requests.post(
            f"https://api.github.com/repos/{_GITHUB_REPO}/actions/workflows/merge-approved-batch.yml/dispatches",
            headers={
                "Authorization": f"Bearer {_GITHUB_ACTIONS_TRIGGER_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            json={"ref": "main", "inputs": {"batch_number": str(batch_number)}},
            timeout=10,
        )
    except requests.RequestException:
        pass


@app.get("/admin/review-queue/approve-for-prod")
def review_queue_approve_for_prod(
    token: str,
    batch: str,
    db: Session = Depends(get_db),
):
    """The explicit CTA the user asked for: once every page in a batch is
    approved (no pending, no flagged), click this once and the batch merges
    to main right away -- no further approval needed in chat, and no
    waiting for the next day's scheduled run. Writes a BatchApproval row
    (see models.py) as the durable signal, then fires _trigger_batch_merge
    to kick off the actual merge immediately via GitHub Actions.

    Requires a real batch_number, not batch=all: promotion is an
    all-or-nothing per-batch operation, matching how daily_batch.py
    generates and pushes one batch_number at a time to staging (each
    commit's message carries a "Tulo-Batch-Number: <N>" trailer so the
    merge workflow can find the exact commit -- not a git tag, since this
    repo's push credentials can create branches but not tag refs).
    Re-clicking after a batch is already merged is a harmless no-op
    (redirects back without writing anything, but still re-fires the
    dispatch in case an earlier click's merge never landed)."""
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)
    if batch == "all":
        raise HTTPException(status_code=400, detail="Pick a specific batch_number to approve for prod, not 'all'.")

    batch_number = int(batch)
    _, batch_pages = _resolve_batch_pages(batch)
    batch_slugs = [p["slug"] for p in batch_pages]
    reviews = {r.slug: r for r in db.query(PageReview).filter(PageReview.slug.in_(batch_slugs)).all()}
    statuses = Counter(reviews[s].status if s in reviews else "pending" for s in batch_slugs)
    if statuses.get("approved", 0) != len(batch_slugs):
        raise HTTPException(
            status_code=400,
            detail=f"batch {batch_number} isn't fully approved yet "
            f"({statuses.get('pending', 0)} pending, {statuses.get('flagged', 0)} flagged).",
        )

    approval = db.query(BatchApproval).filter(BatchApproval.batch_number == batch_number).first()
    already_merged = approval is not None and approval.merged_at is not None
    if approval is None:
        db.add(BatchApproval(batch_number=batch_number))
        db.commit()
    # else: already requested (or already merged) -- nothing new to write.

    if not already_merged:
        _trigger_batch_merge(batch_number)

    return RedirectResponse(url=f"/admin/review-queue?token={token}&batch={batch}&show=all", status_code=303)


@app.get("/admin/review-queue/mark-merged")
def review_queue_mark_merged(
    token: str,
    batch: int,
    db: Session = Depends(get_db),
):
    """Callback the merge-approved-batch.yml GitHub Action hits after it
    successfully pushes a batch's commit to main -- sets BatchApproval's
    merged_at so the review queue shows "merged" instead of "waiting for
    merge", and so daily_batch.py's fallback retry (see
    _trigger_batch_merge's docstring) knows this batch is already done.
    Gated behind the same ADMIN_TASK_TOKEN as every other /admin/* route;
    the Action holds this token as a GitHub Actions secret (a copy of the
    same value Render has, not a new kind of credential)."""
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    approval = db.query(BatchApproval).filter(BatchApproval.batch_number == batch).first()
    if approval is None:
        raise HTTPException(status_code=404, detail=f"No BatchApproval row for batch {batch}")
    if approval.merged_at is None:
        approval.merged_at = datetime.now(timezone.utc)
        db.commit()
    return {"batch_number": batch, "merged_at": approval.merged_at}


@app.get("/admin/export-images")
def export_images(
    token: str,
    slugs: str = Query(
        ...,
        description="Comma-separated slugs to export image_url/image_attribution for.",
    ),
    db: Session = Depends(get_db),
):
    """The "bake" step's read side (see content/scripts/bake_images_from_staging.py):
    given a batch of slugs that were just seeded and fetched on staging,
    returns each one's real image_url/image_attribution so the bake script
    can write them into seed_templates.py as literal data before that
    batch merges to main -- otherwise image_url only ever exists in a
    runtime database (see _RUNTIME_IMAGE_KEYS in seed_templates.py), never
    in the git-tracked seed data, and production would restart the same
    fetch race from zero the moment the batch's code merges, reproducing
    the exact problem the staging pipeline exists to solve.

    Covers single-hero-image templates (SINGLE_IMAGE_TEMPLATES) plus
    category_roundup -- a collection normally has no image_url of its own
    (its cards render each linked recipe's own, already-baked photo live
    at serve time, see _resolved_category_roundup_cards), but a reviewer
    can still set one directly via /admin/review-queue's general-purpose
    override-image escape hatch, which writes content["image_url"]
    unconditionally regardless of template_type -- get_page() and
    _summary_image() both already check for and prioritize that real,
    stored value over the computed card fallback. Without this endpoint
    also willing to export it, that override only ever existed on
    staging: confirmed live (2026-09-14) on beets-recipes, whose
    manually-overridden thumbnail never reached production because this
    endpoint rejected the whole template_type outright. Every OTHER
    template_type still gets the same "nothing to export" error, since
    they never carry a real image_url outside SINGLE_IMAGE_TEMPLATES.

    Gated behind the same ADMIN_TASK_TOKEN as the other /admin/* routes.
    Meant to be called against staging's own base URL, with staging's own
    ADMIN_TASK_TOKEN -- never against production, which has nothing new
    to export.
    """
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    requested = [s.strip() for s in slugs.split(",") if s.strip()]
    pages_by_slug = {
        page.slug: page
        for page in db.query(Page).filter(Page.slug.in_(requested)).all()
    }

    result = {}
    for slug in requested:
        page = pages_by_slug.get(slug)
        if page is None:
            result[slug] = {"error": "not found"}
            continue
        if page.template_type not in SINGLE_IMAGE_TEMPLATES and page.template_type != "category_roundup":
            result[slug] = {
                "error": f"template_type {page.template_type!r} has no page-level image_url to export"
            }
            continue
        result[slug] = {
            "image_url": page.content.get("image_url"),
            "image_attribution": page.content.get("image_attribution"),
        }

    return result


@app.get("/admin/apply-baked-images")
def apply_baked_images(token: str, db: Session = Depends(get_db)):
    """One-time (safely re-runnable) fix for a real gap: resync_content()
    and seed() both deliberately never touch an existing row's image_url/
    image_attribution (see _RUNTIME_IMAGE_KEYS in seed_templates.py) --
    correct behavior for protecting a live-fetched or admin-overridden
    photo from a naive resync, but it also means baking a verified-correct
    image_url into SEED_PAGES (see bake_images_from_staging.py /
    audit_and_bake_all_images.py) never actually reaches an EXISTING
    database row once deployed: seed() only ever inserts brand-new slugs,
    and resync_content() skips these two keys on every existing one, on
    purpose. Confirmed live (2026-09-14): a full-site image audit baked
    2,132 already-reviewed-correct images into seed_templates.py and
    merged to main, but production kept showing the old (or missing)
    photo on every one of those pre-existing pages after redeploying --
    nothing had ever pushed SEED_PAGES' newly-baked value onto the
    already-live row.

    This is the one deliberate exception: pushes SEED_PAGES' image_url/
    image_attribution onto a matching existing row wherever SEED_PAGES
    has a real (non-null) value that differs from what's currently
    stored. Never nulls out an existing DB image just because SEED_PAGES
    happens to have none for that slug -- only ever overwrites toward a
    real baked value, the same one-directional intent as the bake scripts
    themselves. Safe to re-run: a no-op for any row that already
    matches."""
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    seed_by_slug = {p["slug"]: p["content"] for p in SEED_PAGES}
    # Scoped to slugs with a real baked image_url (most of the site, but a
    # real, meaningful reduction from literally every SEED_PAGES slug) and
    # chunked, rather than one query()+loop over the whole match set --
    # the exact shape of the OOM crash fetch_images() hit earlier this
    # session (see CONCURRENCY's docstring in fetch_stock_images.py) before
    # its own query got the same only_slugs scoping. Confirmed the risk is
    # real here too, not just theoretical: a request to this endpoint hung
    # for 13+ minutes from a GitHub Actions caller (2026-09-14) consistent
    # with prod either OOMing mid-request or a Render deploy racing it --
    # either way, holding every matched row's full content in memory at
    # once was the wrong shape for a 512MB instance regardless of which it
    # was. Committing per chunk lets memory actually be released between
    # batches instead of holding the whole result set until one final commit.
    candidate_slugs = [slug for slug, content in seed_by_slug.items() if content.get("image_url")]
    _CHUNK_SIZE = 200
    updated: list[str] = []
    for i in range(0, len(candidate_slugs), _CHUNK_SIZE):
        chunk = candidate_slugs[i : i + _CHUNK_SIZE]
        chunk_updated = False
        for page in db.query(Page).filter(Page.slug.in_(chunk)).all():
            seed_image_url = seed_by_slug[page.slug]["image_url"]
            if page.content.get("image_url") == seed_image_url:
                continue
            content = copy.deepcopy(page.content)
            content["image_url"] = seed_image_url
            content["image_attribution"] = seed_by_slug[page.slug].get("image_attribution")
            page.content = content
            updated.append(page.slug)
            chunk_updated = True
        if chunk_updated:
            db.commit()

    return {"updated_count": len(updated), "updated_slugs": updated}


# One-off diagnostic for comparing Pexels vs. Unsplash search-result quality
# side by side on the same queries -- a mix of terms Pexels previously had
# no relevant match for (from the ingredient_hub backlog) and terms Pexels
# already handled easily, to see whether Unsplash actually helps on the hard
# cases and how it compares on the easy ones. Calls both providers directly
# (not through search_image()'s Pexels-first/Unsplash-fallback order) so
# both always run regardless of whether Pexels succeeds. Not meant to be a
# permanent route -- safe to delete once the comparison's been reviewed.
_COMPARE_IMAGE_TERMS = [
    # Pexels was struggling (obscure ingredient_hub terms)
    ("braunschweiger", "sliced braunschweiger liver sausage on rye bread", ("liverwurst", "braunschweiger")),
    ("scoby", "kombucha scoby culture in glass jar", "kombucha"),
    ("langostino", "cooked langostino tails on ice", ("langostino", "shrimp", "lobster")),
    ("qottab", "fried pastries dusted with powdered sugar on a plate", ("pastry", "pastries")),
    ("kanpachi", "sliced raw fish sashimi on a plate", ("sashimi", "fish")),
    # Pexels wasn't struggling (easy, common queries)
    ("chocolate chip cookies", "chocolate chip cookies", None),
    ("roasted brussels sprouts", "roasted brussels sprouts", None),
    ("grilled salmon fillet", "grilled salmon fillet", None),
    ("banana bread slice", "banana bread slice", None),
    ("taco bowl", "taco bowl with ground beef and toppings", None),
]


@app.get("/admin/compare-images", response_class=HTMLResponse)
def compare_images(token: str):
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    def render_result(provider: str, query: str, must_match) -> str:
        try:
            if provider == "pexels":
                photo = _search_pexels(query, must_match=must_match)
            else:
                photo = _search_unsplash(query, must_match=must_match)
        except Exception as e:
            return f'<div class="cell error">Error: {e}</div>'
        if photo is None:
            return '<div class="cell empty">No relevant result found</div>'
        return f"""
        <div class="cell">
          <img src="{photo.url}" alt="">
          <p class="meta">by {photo.photographer} on {photo.source}</p>
        </div>
        """

    rows = []
    for label, query, must_match in _COMPARE_IMAGE_TERMS:
        pexels_html = render_result("pexels", query, must_match)
        unsplash_html = render_result("unsplash", query, must_match)
        rows.append(f"""
        <tr>
          <td class="label">
            <strong>{label}</strong>
            <div class="query">query: "{query}"</div>
          </td>
          <td>{pexels_html}</td>
          <td>{unsplash_html}</td>
        </tr>
        """)

    html = f"""
    <html>
    <head>
      <title>Pexels vs. Unsplash comparison</title>
      <style>
        body {{ font-family: -apple-system, sans-serif; padding: 24px; background: #faf9f7; }}
        table {{ border-collapse: collapse; width: 100%; }}
        td {{ border: 1px solid #ddd; padding: 12px; vertical-align: top; width: 33%; }}
        th {{ padding: 8px 12px; text-align: left; background: #eee; }}
        .label {{ background: #f5f5f5; }}
        .query {{ color: #888; font-size: 12px; margin-top: 4px; }}
        .cell img {{ max-width: 100%; max-height: 220px; border-radius: 6px; display: block; }}
        .meta {{ font-size: 12px; color: #666; margin: 4px 0 0; }}
        .empty {{ color: #b00; font-style: italic; }}
        .error {{ color: #b00; }}
      </style>
    </head>
    <body>
      <h1>Pexels vs. Unsplash: same queries, side by side</h1>
      <table>
        <tr><th>Term</th><th>Pexels</th><th>Unsplash</th></tr>
        {"".join(rows)}
      </table>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


def _raw_candidates(provider: str, query: str, limit: int = 12) -> list[dict]:
    """Like images._search_pexels/_search_unsplash, but returns every
    candidate the API ranked (up to `limit`), not just the first one that
    passes every check -- for /admin/debug-page-image below, which needs to
    show *why* a given photo won or lost, not just the final answer."""
    if provider == "pexels":
        if not PEXELS_ACCESS_KEY:
            return []
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_ACCESS_KEY},
            params={"query": query, "per_page": SEARCH_RESULTS_PER_PAGE},
            timeout=10,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])[:limit]
        return [
            {
                "url": p["src"]["large"],
                "alt": p.get("alt") or "",
                "photographer": p["photographer"],
                "source": "pexels",
            }
            for p in photos
        ]
    if not UNSPLASH_ACCESS_KEY:
        return []
    r = requests.get(
        "https://api.unsplash.com/search/photos",
        headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
        params={"query": query, "per_page": SEARCH_RESULTS_PER_PAGE},
        timeout=10,
    )
    r.raise_for_status()
    results = r.json().get("results", [])[:limit]
    return [
        {
            "url": p["urls"]["regular"],
            "alt": " ".join(filter(None, (p.get("alt_description"), p.get("description")))),
            "photographer": p["user"]["name"],
            "source": "unsplash",
        }
        for p in results
    ]


@app.get("/admin/debug-page-image", response_class=HTMLResponse)
def debug_page_image(token: str, slug: str, db: Session = Depends(get_db)):
    """Shows exactly what fetch_stock_images.py would search for and select
    for one real page -- every attempt (salient_ingredient_query first when
    set, then the dish/primary query, each with its actual must_match), and
    for each attempt, every candidate photo both providers returned with its
    real alt text and whether it passed the relevance check, not just the
    single final answer _apply_result would have picked. Built after two
    rounds of guessing wrong about why a specific page's re-fetch still
    wasn't picking a good photo -- this replaces guessing with actually
    seeing what the search is doing. Not meant to be a permanent route.
    """
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    page = db.query(Page).filter(Page.slug == slug).first()
    if page is None:
        raise HTTPException(status_code=404, detail="page not found")

    content = page.content

    def render_candidates(provider: str, attempt_query: str, must_match) -> str:
        candidates = _raw_candidates(provider, attempt_query)
        if not candidates:
            return '<p class="empty">No results (no key configured, or provider returned nothing).</p>'
        rows = []
        for c in candidates:
            passes = _is_relevant(c["alt"], must_match)
            host_ok = c["url"].startswith(ALLOWED_IMAGE_HOSTS)
            css = "pass" if passes and host_ok else "fail"
            reason = "" if passes else "no must_match term in alt text"
            if not host_ok:
                reason = "disallowed host"
            rows.append(f"""
            <div class="candidate {css}">
              <img src="{c['url']}" alt="">
              <div class="cand-info">
                <div class="verdict">{"PASS" if passes and host_ok else "FAIL"} {f'<span class="reason">({reason})</span>' if reason else ""}</div>
                <div class="alt">alt: "{c['alt'] or '(blank)'}"</div>
                <div class="photog">by {c['photographer']} on {c['source']}</div>
                <input type="text" class="url-box" readonly value="{c['url']}" onclick="this.select()">
              </div>
            </div>
            """)
        return "".join(rows)

    page_style = """
        body { font-family: -apple-system, sans-serif; padding: 24px; background: #faf9f7; max-width: 900px; margin: 0 auto; }
        h1 { font-size: 20px; }
        h2 { font-size: 16px; margin-top: 32px; border-bottom: 1px solid #ddd; padding-bottom: 6px; }
        h3 { font-size: 13px; color: #666; margin: 16px 0 8px; }
        .mm { font-size: 12px; color: #666; }
        .candidate { display: flex; gap: 12px; padding: 8px; border-radius: 6px; margin-bottom: 6px; }
        .candidate.pass { background: #e6f4ea; }
        .candidate.fail { background: #fbe9e7; opacity: 0.6; }
        .candidate img { width: 100px; height: 70px; object-fit: cover; border-radius: 4px; flex-shrink: 0; }
        .cand-info { font-size: 12px; }
        .verdict { font-weight: 700; }
        .reason { font-weight: 400; color: #888; }
        .alt { color: #333; margin-top: 2px; }
        .photog { color: #888; margin-top: 2px; }
        .empty { color: #b00; font-style: italic; }
        .card-block { margin-top: 28px; padding-top: 4px; }
        .url-box { width: 100%; max-width: 280px; margin-top: 4px; font-size: 10px; font-family: monospace; padding: 3px 5px; border: 1px solid #ccc; border-radius: 3px; background: #fff; color: #555; }
    """

    if page.template_type == "category_roundup":
        # A category_roundup page has no single hero image -- each card in
        # recipe_cards gets its own photo (see process_category_roundup_page
        # in fetch_stock_images.py) -- so this shows one section per card
        # instead of the single-attempt view below. Mirrors that function's
        # real attempt list exactly: the card's own image_query, then the
        # page-title-derived category fallback (skipped if identical), both
        # with must_match=None -- category_roundup cards get no relevance
        # check at all today (see that function's own `attempts` line), so
        # every reachable candidate below shows as PASS; this view still
        # surfaces that clearly rather than pretending a check ran.
        card_sections = []
        for card in content.get("recipe_cards", []):
            card_title = card.get("title") or "(untitled card)"
            query = card.get("image_query")
            if not query:
                card_sections.append(f'<div class="card-block"><h2>{card_title}</h2><p class="empty">No image_query set on this card.</p></div>')
                continue
            fallback = _category_fallback_query(page.title)
            queries = [query] if fallback.lower() == query.lower() else [query, fallback]
            attempt_sections = []
            for raw_query in queries:
                search_query = _search_query_for(page.template_type, raw_query)
                suffix_note = (
                    f' <span class="suffix">(actually searched as "{search_query}")</span>'
                    if search_query != raw_query
                    else ""
                )
                attempt_sections.append(f"""
                <section>
                  <h3>Attempt: "{raw_query}"{suffix_note}</h3>
                  <p class="mm">must_match: None (category_roundup cards get no relevance check)</p>
                  <h3>Pexels</h3>
                  {render_candidates("pexels", search_query, None)}
                  <h3>Unsplash</h3>
                  {render_candidates("unsplash", search_query, None)}
                </section>
                """)
            current_card_url = card.get("image_url")
            current_card_block = (
                f'<img src="{current_card_url}" alt="" style="max-width:250px;border-radius:8px;">'
                if current_card_url
                else "<p>(no image_url set on this card)</p>"
            )
            card_sections.append(f"""
            <div class="card-block">
              <h2>{card_title}</h2>
              <p><strong>Current photo:</strong></p>
              {current_card_block}
              {"".join(attempt_sections)}
            </div>
            """)

        html = f"""
        <html>
        <head>
          <title>Debug: {slug}</title>
          <style>{page_style}</style>
        </head>
        <body>
          <h1>Debug image search: {slug} (category_roundup -- one section per card)</h1>
          {"".join(card_sections) or '<p class="empty">No recipe_cards on this page.</p>'}
        </body>
        </html>
        """
        return HTMLResponse(content=html)

    query_key = SINGLE_IMAGE_TEMPLATES.get(page.template_type)
    if query_key is None or query_key not in content:
        raise HTTPException(status_code=400, detail=f"template_type {page.template_type!r} has no image query")

    query = content[query_key]
    salient_query = content.get("salient_ingredient_query")
    override_must_match = content.get("hero_image_must_match")

    # Mirrors fetch_images()'s real attempt order: salient tier first, using
    # its own explicit salient_ingredient_must_match override when the page
    # sets one (never hero_image_must_match -- see `protected_attempts` in
    # fetch_stock_images.py) and falling back to the derived term only when
    # no override is set, then the dish/primary query (with
    # hero_image_must_match applied if set, else the derived term for
    # recipe_or_dish, else None for every other template). This used to
    # always show the derived term for the salient tier regardless of
    # whether the page had its own override -- confirmed live on
    # black-sesame-paste and homemade-onion-soup-mix, both of which do set
    # salient_ingredient_must_match: the real fetch was already using the
    # tighter, correct term, but this view showed the loose auto-derived
    # one instead, making a correctly-working search look broken.
    #
    # Each attempt's *search* query is run through _search_query_for, the
    # exact same call fetch_images() makes -- that appends " plated dish"
    # for recipe_or_dish/category_roundup templates. This view used to pass
    # the raw content query straight to _raw_candidates, silently skipping
    # that suffix -- confirmed live on spinach-artichoke-dip: this page
    # showed a real, passing "...with a spinach dip" candidate for the
    # un-suffixed salient query, but the actual fetch (searching "spinach
    # and artichoke dip plated dish", a different query to the API) came
    # back with nothing. The label still shows the page's own content
    # query, unsuffixed, since that's what a human editing this page
    # actually wrote -- only the real API call gets the suffix.
    attempts: list[tuple[str, str, str, object]] = []
    if salient_query:
        salient_must_match = content.get("salient_ingredient_must_match") or _recipe_dish_must_match_terms(salient_query)
        salient_search_query = _search_query_for(page.template_type, salient_query)
        attempts.append((f"{salient_query} (salient)", salient_query, salient_search_query, salient_must_match))
    dish_must_match = override_must_match if override_must_match else _recipe_dish_must_match_terms(query)
    dish_search_query = _search_query_for(page.template_type, query)
    attempts.append((query, query, dish_search_query, dish_must_match))

    sections = []
    for label, raw_query, search_query, must_match in attempts:
        suffix_note = (
            f' <span class="suffix">(actually searched as "{search_query}")</span>'
            if search_query != raw_query
            else ""
        )
        sections.append(f"""
        <section>
          <h2>Attempt: "{label}"{suffix_note}</h2>
          <p class="mm">must_match: {must_match!r}</p>
          <h3>Pexels</h3>
          {render_candidates("pexels", search_query, must_match)}
          <h3>Unsplash</h3>
          {render_candidates("unsplash", search_query, must_match)}
        </section>
        """)

    current_url = content.get("image_url")
    current_block = (
        f'<img src="{current_url}" alt="" style="max-width:300px;border-radius:8px;">'
        if current_url
        else "<p>(no image_url set)</p>"
    )

    html = f"""
    <html>
    <head>
      <title>Debug: {slug}</title>
      <style>
        body {{ font-family: -apple-system, sans-serif; padding: 24px; background: #faf9f7; max-width: 900px; margin: 0 auto; }}
        h1 {{ font-size: 20px; }}
        h2 {{ font-size: 16px; margin-top: 32px; border-bottom: 1px solid #ddd; padding-bottom: 6px; }}
        h3 {{ font-size: 13px; color: #666; margin: 16px 0 8px; }}
        .mm {{ font-size: 12px; color: #666; }}
        .candidate {{ display: flex; gap: 12px; padding: 8px; border-radius: 6px; margin-bottom: 6px; }}
        .candidate.pass {{ background: #e6f4ea; }}
        .candidate.fail {{ background: #fbe9e7; opacity: 0.6; }}
        .candidate img {{ width: 100px; height: 70px; object-fit: cover; border-radius: 4px; flex-shrink: 0; }}
        .cand-info {{ font-size: 12px; }}
        .verdict {{ font-weight: 700; }}
        .reason {{ font-weight: 400; color: #888; }}
        .alt {{ color: #333; margin-top: 2px; }}
        .photog {{ color: #888; margin-top: 2px; }}
        .empty {{ color: #b00; font-style: italic; }}
      </style>
    </head>
    <body>
      <h1>Debug image search: {slug}</h1>
      <p><strong>Current live photo:</strong></p>
      {current_block}
      {"".join(sections)}
    </body>
    </html>
    """
    return HTMLResponse(content=html)


def _seed_outreach_examples(db: Session) -> None:
    """Populates a handful of clearly-marked example rows the first time
    outreach_prospects is empty, purely so /admin/outreach-queue (a shell
    -- see OutreachProspect's own docstring for what's not built yet) has
    something real to show and its Approve/Reject buttons have something
    to act on, instead of shipping a page that looks broken empty. Every
    example uses a fictitious .test domain and no real contact --
    is_example=True keeps it visually and structurally distinguishable
    from a real prospect once real sourcing exists. Idempotent: only
    inserts when the table has zero rows, so a reviewer's real decisions
    (or a future real prospect) are never touched by a redeploy."""
    if db.query(OutreachProspect).first() is not None:
        return
    examples = [
        OutreachProspect(
            pitch_type="tool_pitch",
            target_domain="example-cooking-blog.test",
            contact_name="Jamie (example contact)",
            contact_email="jamie@example-cooking-blog.test",
            subject="A free pan-size converter your readers might like",
            body_preview=(
                "Hi Jamie -- I noticed your banana bread post mentions swapping pan sizes by eye. "
                "We built a free pan-size/yield calculator that adjusts bake time too, thought it "
                "might be a useful link for that post."
            ),
            is_example=True,
        ),
        OutreachProspect(
            pitch_type="tool_pitch",
            target_domain="example-nutrition-site.test",
            contact_name="Morgan (example contact)",
            contact_email="morgan@example-nutrition-site.test",
            subject="A live recipe nutrition recalculator (swap-aware)",
            body_preview=(
                "Hi Morgan -- following your piece on recipe substitutions, we built a tool that "
                "recalculates a recipe's nutrition live as you swap ingredients or change servings. "
                "Could be a relevant link for readers making substitutions."
            ),
            is_example=True,
        ),
        OutreachProspect(
            pitch_type="haro_reply",
            target_domain="example-journalist-outlet.test",
            contact_name="Reporter (example contact)",
            contact_email=None,
            source_query=(
                "Looking for a home cook or food writer to comment on ingredient substitution "
                "mistakes for a piece on baking fails."
            ),
            subject="Source for your ingredient-substitution piece",
            body_preview=(
                "Hi -- happy to help as a source. One common mistake: substituting baking soda for "
                "baking powder 1:1 -- baking soda is roughly 3x stronger and needs its own acid to "
                "activate, so the swap either falls flat or turns bitter. Happy to expand with a "
                "couple more examples if useful."
            ),
            is_example=True,
        ),
    ]
    db.add_all(examples)
    db.commit()


@app.get("/admin/outreach-queue", response_class=HTMLResponse)
def outreach_queue(
    show: str = Query(default="queued", description="queued | approved | rejected | all"),
    db: Session = Depends(get_db),
    _auth: None = Depends(_require_outreach_auth),
):
    """Portal shell for link-building outreach (tool-pitch emails and
    HARO/Connectively-style query replies) -- see OutreachProspect's
    docstring for exactly what is and isn't real yet. Real prospect
    sourcing and real sending are still pending on settling an
    email-sending API and a HARO/Connectively data source (see this
    session's research). Approve/Reject state itself is real and
    persists, and this route is now gated by _require_outreach_auth
    (HTTPBasic, a credential separate from ADMIN_TASK_TOKEN) instead of
    the URL-token pattern the rest of /admin uses -- see that
    dependency's own docstring for why this portal specifically warrants
    the step up."""
    query = db.query(OutreachProspect)
    if show != "all":
        query = query.filter(OutreachProspect.status == show)
    rows = query.order_by(OutreachProspect.created_at.desc()).all()

    counts = Counter(r.status for r in db.query(OutreachProspect).all())

    def card(r: OutreachProspect) -> str:
        pitch_label = "Tool pitch" if r.pitch_type == "tool_pitch" else "HARO/query reply"
        pitch_pill_class = "tool" if r.pitch_type == "tool_pitch" else "haro"
        query_html = (
            f'<div class="source-query">Query: {escape_html(r.source_query)}</div>' if r.source_query else ""
        )
        contact_bits = [
            escape_html(v) for v in (r.contact_name, r.contact_email) if v
        ]
        contact_html = " &middot; ".join(contact_bits)
        example_pill = '<span class="pill pill-example">example</span>' if r.is_example else ""
        if r.status == "queued":
            actions_html = f"""
            <div class="actions">
              <a class="btn-approve" href="/admin/outreach-queue/decide?prospect_id={r.id}&status=approved&show={show}">Approve</a>
              <a class="btn-reject" href="/admin/outreach-queue/decide?prospect_id={r.id}&status=rejected&show={show}">Reject</a>
            </div>
            """
        else:
            decided_label = f"{r.decided_at:%Y-%m-%d %H:%M}" if r.decided_at else ""
            actions_html = (
                f'<div class="decided">decided {decided_label} &middot; '
                f'<a href="/admin/outreach-queue/decide?prospect_id={r.id}&status=queued&show={show}">undo</a></div>'
            )
        if r.sent_at:
            send_status_html = f'<div class="send-ok">sent to Snov.io {r.sent_at:%Y-%m-%d %H:%M}</div>'
        elif r.send_error:
            send_status_html = f'<div class="send-error">send failed: {escape_html(r.send_error)}</div>'
        else:
            send_status_html = ""
        return f"""
        <div class="card status-{r.status}">
          <div class="info">
            <div class="title">{escape_html(r.subject)}
              <span class="pill pill-{pitch_pill_class}">{pitch_label}</span>{example_pill}
              <span class="pill pill-status-{r.status}">{r.status}</span>
            </div>
            <div class="meta">{escape_html(r.target_domain)}{" &middot; " + contact_html if contact_html else ""}</div>
            {query_html}
            <div class="body-preview">{escape_html(r.body_preview)}</div>
            {send_status_html}
            {actions_html}
          </div>
        </div>
        """

    rows_html = "".join(card(r) for r in rows) if rows else '<p style="color:#888;font-size:13px;">Nothing here.</p>'

    html = f"""
    <html>
    <head>
      <title>Outreach queue</title>
      <style>
        body {{ font-family: -apple-system, sans-serif; margin: 24px; background: #fafafa; max-width: 900px; }}
        h1 {{ font-size: 20px; margin-bottom: 4px; }}
        .banner {{ font-size: 12px; color: #7a5b00; background: #fff6dd; border: 1px solid #f0dfa0; border-radius: 6px; padding: 10px 14px; margin-bottom: 18px; }}
        .summary {{ font-size: 13px; color: #444; margin-bottom: 14px; }}
        .filters {{ margin-bottom: 16px; }}
        .filters a {{ margin-right: 10px; font-size: 13px; }}
        .card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; }}
        .card.status-approved {{ border-color: #bde0c4; }}
        .card.status-rejected {{ opacity: 0.6; }}
        .title {{ font-weight: 600; font-size: 14px; }}
        .pill {{ font-size: 10px; padding: 1px 7px; border-radius: 20px; margin-left: 4px; font-weight: 400; }}
        .pill-tool {{ background: #e3ecfb; color: #24478a; }}
        .pill-haro {{ background: #f0e6fb; color: #5b2d90; }}
        .pill-example {{ background: #eee; color: #777; }}
        .pill-status-queued {{ background: #eee; color: #666; }}
        .pill-status-approved {{ background: #dcefe0; color: #276b3c; }}
        .pill-status-rejected {{ background: #fbdada; color: #a00; }}
        .meta {{ color: #888; font-size: 11px; margin: 4px 0 8px; }}
        .source-query {{ font-size: 12px; color: #5b2d90; background: #f7f2fc; border-radius: 4px; padding: 6px 8px; margin: 6px 0; }}
        .body-preview {{ font-size: 12px; color: #333; margin: 8px 0; white-space: pre-wrap; }}
        .actions {{ margin-top: 10px; }}
        .btn-approve {{ background: #2f7d43; color: #fff; border: none; border-radius: 4px; padding: 5px 12px; font-size: 12px; text-decoration: none; margin-right: 8px; }}
        .btn-reject {{ background: #b23; color: #fff; border: none; border-radius: 4px; padding: 5px 12px; font-size: 12px; text-decoration: none; }}
        .decided {{ font-size: 11px; color: #888; margin-top: 8px; }}
        .decided a {{ color: #06c; }}
        .send-ok {{ font-size: 11px; color: #276b3c; margin-top: 8px; }}
        .send-error {{ font-size: 11px; color: #a00; margin-top: 8px; }}
      </style>
    </head>
    <body>
      <h1>Outreach queue</h1>
      <div class="banner">
        Approving a real (non-example) Tool pitch prospect with a contact email now actually adds them to
        a Snov.io list and can trigger a real send, once SNOV_CLIENT_ID/SNOV_CLIENT_SECRET/SNOV_LIST_ID are
        configured -- check the send status under each approved row. HARO/query reply prospects still need
        a human to send the reply themselves; every row below is otherwise either an example, or a real
        prospect from the inbound-email webhook.
      </div>
      <div class="summary">{counts.get('queued', 0)} queued &middot; {counts.get('approved', 0)} approved &middot; {counts.get('rejected', 0)} rejected</div>
      <div class="filters">
        <a href="/admin/outreach-queue?show=queued">queued</a>
        <a href="/admin/outreach-queue?show=approved">approved</a>
        <a href="/admin/outreach-queue?show=rejected">rejected</a>
        <a href="/admin/outreach-queue?show=all">all</a>
        &middot;
        <a href="/admin/outreach-queue/export.csv?status=approved">export approved as CSV</a>
      </div>
      {rows_html}
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/admin/outreach-queue/decide")
def outreach_queue_decide(
    prospect_id: int,
    status: str,
    show: str = "queued",
    db: Session = Depends(get_db),
    _auth: None = Depends(_require_outreach_auth),
):
    """Records a human's approve/reject (or undo-back-to-queued) decision
    on one prospect. Same GET-link-plus-redirect convention as
    /admin/review-queue/mark -- an internal click, not a user-facing form
    -- gated by _require_outreach_auth (see its docstring) rather than a
    URL token, so the browser's own remembered Basic Auth credential
    carries across this redirect the same as any other same-origin
    request.

    Approving a tool_pitch prospect also attempts the real Snov.io send
    (see _add_prospect_to_snov_list) -- a no-op until SNOV_CLIENT_ID/
    SNOV_CLIENT_SECRET/SNOV_LIST_ID are all configured. A haro_reply is
    never auto-sent this way (see OutreachProspect's docstring for why),
    and un-approving (back to queued or rejected) never un-sends
    something already added to Snov.io -- there's no real "undo" for a
    prospect Snov.io has already started emailing."""
    if status not in ("queued", "approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be queued, approved, or rejected")

    prospect = db.query(OutreachProspect).filter(OutreachProspect.id == prospect_id).first()
    if prospect is None:
        raise HTTPException(status_code=404)

    prospect.status = status
    prospect.decided_at = datetime.now(timezone.utc) if status != "queued" else None
    if status == "approved" and prospect.pitch_type == "tool_pitch" and prospect.sent_at is None:
        _add_prospect_to_snov_list(prospect)
    db.commit()

    return RedirectResponse(url=f"/admin/outreach-queue?show={show}", status_code=303)


@app.post("/admin/outreach-queue/create")
async def outreach_queue_create(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(_require_outreach_auth),
):
    """Inserts one real (is_example=False) prospect, queued for human
    review -- the write side a sourcing script needs (see
    content/scripts/add_outreach_prospects.py) to get researched
    candidates into the live queue without a human retyping each one by
    hand into a form that doesn't exist. JSON body:
    {pitch_type, target_domain, subject, body_preview} required;
    contact_name/contact_email/source_query optional. Same
    _require_outreach_auth gate as every other outreach route -- a
    sourcing script authenticates with OUTREACH_ADMIN_USER/PASSWORD from
    a GitHub Actions secret, the same way override_images.py already
    authenticates to /admin/review-queue/override-image with
    ADMIN_TASK_TOKEN, so the real credential never has to pass through
    chat.

    Deliberately no dedup against existing rows: this is a one-off
    research batch, not a recurring automated job, so a rerun creating a
    duplicate is a human reject-and-move-on, not a real problem worth
    the extra complexity of a same-domain/same-subject lookup here."""
    payload = await request.json()

    pitch_type = payload.get("pitch_type")
    if pitch_type not in ("tool_pitch", "haro_reply"):
        raise HTTPException(status_code=400, detail="pitch_type must be tool_pitch or haro_reply")
    target_domain = (payload.get("target_domain") or "").strip()
    subject = (payload.get("subject") or "").strip()
    body_preview = (payload.get("body_preview") or "").strip()
    if not (target_domain and subject and body_preview):
        raise HTTPException(status_code=400, detail="target_domain, subject, and body_preview are required")

    prospect = OutreachProspect(
        pitch_type=pitch_type,
        target_domain=target_domain,
        contact_name=(payload.get("contact_name") or None),
        contact_email=(payload.get("contact_email") or None),
        source_query=(payload.get("source_query") or None),
        subject=subject,
        body_preview=body_preview,
        is_example=False,
        status="queued",
    )
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    return {"created_prospect_id": prospect.id}


@app.get("/admin/outreach-queue/export.csv")
def outreach_queue_export_csv(
    status: str = Query(default="approved", description="approved | queued | rejected | all"),
    db: Session = Depends(get_db),
    _auth: None = Depends(_require_outreach_auth),
):
    """CSV export of prospects, for manually importing into a campaign
    tool's own UI. Originally built as a bridge for tool_pitch prospects
    before real Snov.io API docs were available (see git history) --
    that gap is closed now (_add_prospect_to_snov_list), but this export
    stays useful for: haro_reply prospects (never auto-sent -- see
    OutreachProspect's docstring), any tool_pitch prospect whose send
    failed or Snov.io isn't configured yet (send_error/sent_at columns
    below show exactly why), and as a plain backup/audit trail.

    Defaults to status=approved -- the "ready to act on" set -- not the
    full queue, so the file downloaded here isn't accidentally imported
    with still-pending or already-rejected rows mixed in."""
    import csv
    import io

    query = db.query(OutreachProspect)
    if status != "all":
        query = query.filter(OutreachProspect.status == status)
    rows = query.order_by(OutreachProspect.created_at.desc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["prospect_id", "pitch_type", "target_domain", "contact_name", "contact_email", "subject", "body_preview", "source_query", "status", "is_example", "sent_at", "send_error"]
    )
    for r in rows:
        writer.writerow(
            [r.id, r.pitch_type, r.target_domain, r.contact_name or "", r.contact_email or "", r.subject, r.body_preview, r.source_query or "", r.status, r.is_example, r.sent_at or "", r.send_error or ""]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="outreach-prospects-{status}.csv"'},
    )


# Postmark's own recommended pattern -- see "Configure an inbound server"
# in their docs -- is to embed HTTP Basic credentials straight into the
# webhook URL you register with them (https://user:pass@host/path):
# Postmark then sends that Authorization header on every POST with no
# challenge/response round trip needed, since it's a server-to-server
# call, not a browser visiting a page. That's exactly what
# _require_outreach_auth already checks, so the inbound webhook reuses it
# rather than inventing a second secret. Whichever inbound-email provider
# actually gets set up (Postmark Inbound was this session's research
# recommendation; Mailgun Routes is a close second) needs to be
# configured to hit this URL with those credentials embedded.
_MAX_INGESTED_QUERY_CHARS = 8000


def _strip_html_tags(html_text: str) -> str:
    """Crude HTML->text fallback for the rare inbound email that has no
    plain-text body at all (most providers synthesize one, but an
    unusually-formatted forwarded digest could still arrive HTML-only) --
    good enough for a human reviewer to read the gist, not a real parser."""
    return re.sub(r"<[^>]+>", " ", html_text)


def _parse_inbound_email_payload(payload: dict) -> tuple[str, str, str]:
    """Extracts (sender_email, subject, body) from either of two inbound
    webhook JSON shapes, auto-detected by which keys are present --
    covers both providers this session actually confirmed a real schema
    for:

    - Postmark Inbound: FromFull.Email (falls back to the legacy plain
      From string), Subject, TextBody, HtmlBody.
    - CloudMailin (JSON Normalised format): envelope.from,
      headers.subject, plain, html.

    Detection key is "envelope" or "plain" -> CloudMailin; anything else
    is treated as Postmark's shape, since that was this integration's
    original target. A third provider needs a third branch here, not a
    guess -- same discipline as everywhere else this session pulled a
    real schema before writing a parser for it."""
    if "envelope" in payload or "plain" in payload:
        sender_email = (payload.get("envelope") or {}).get("from") or ""
        subject = (payload.get("headers") or {}).get("subject") or "(no subject)"
        body = payload.get("plain") or _strip_html_tags(payload.get("html") or "")
    else:
        from_full = payload.get("FromFull") or {}
        sender_email = from_full.get("Email") or payload.get("From") or ""
        subject = payload.get("Subject") or "(no subject)"
        body = payload.get("TextBody") or _strip_html_tags(payload.get("HtmlBody") or "")
    return sender_email, subject.strip(), body.strip()


@app.post("/admin/outreach-queue/ingest-email")
async def outreach_queue_ingest_email(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(_require_outreach_auth),
):
    """Receives one forwarded email (a HARO/Connectively-style query
    digest, or anything else routed to the inbound address) from an
    inbound-email-to-webhook provider and queues it as one new
    OutreachProspect for human review. Parses either Postmark Inbound's
    or CloudMailin's JSON schema (see _parse_inbound_email_payload) --
    CloudMailin over Postmark Inbound specifically because Postmark
    Inbound has no free tier, while CloudMailin's free tier (10,000
    messages/month, not a time-limited trial) comfortably covers this
    volume and, like Postmark, supports embedding Basic Auth credentials
    directly in the registered target URL -- so it reuses
    _require_outreach_auth exactly like Postmark would have, no separate
    secret. A provider whose POST isn't JSON at all (e.g. Mailgun Routes,
    which is form-encoded) would need a real code change here, not just a
    new schema branch.

    Deliberately does NOT try to split a digest email containing many
    individual queries into separate prospects -- an automatic splitter
    would have to guess at each source's own formatting (HARO's and
    Connectively's digest layouts differ, and a forwarding step can
    mangle either further with quoted-reply markers), and this session
    already has direct, hard-won evidence (the #2 near-miss ingredient
    matcher, rejected after a ~60-70% false-positive rate on manual
    sampling) that a guessed heuristic here would misfire silently rather
    than obviously. One row per inbound email, holding the full raw text,
    is the honest scope: a human reads it and manually creates/edits
    individual prospects, or this gets revisited once real sample emails
    exist to build and verify a real splitter against."""
    payload = await request.json()
    sender_email, subject, body = _parse_inbound_email_payload(payload)
    sender_domain = sender_email.split("@")[-1].strip().lower() if "@" in sender_email else "unknown-sender"

    truncated = len(body) > _MAX_INGESTED_QUERY_CHARS
    if truncated:
        body = body[:_MAX_INGESTED_QUERY_CHARS] + "\n\n[... truncated, see original email for the rest]"

    prospect = OutreachProspect(
        pitch_type="haro_reply",
        target_domain=sender_domain,
        contact_name=None,
        contact_email=None,
        source_query=body or "(empty body)",
        subject=f"[Draft needed] Re: {subject}",
        body_preview=(
            "Raw forwarded digest -- likely contains multiple individual queries bundled together. "
            "Read the source query above, pick the one(s) worth responding to, and replace this "
            "placeholder with a real drafted reply (and split into separate prospects if more than "
            "one query here is worth pursuing) before approving."
        ),
        is_example=False,
        status="queued",
    )
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    return {"created_prospect_id": prospect.id}
