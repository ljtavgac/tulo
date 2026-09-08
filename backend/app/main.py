import io
import os
import secrets
from contextlib import asynccontextmanager, redirect_stdout

import requests
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .fetch_stock_images import SINGLE_IMAGE_TEMPLATES, fetch_images
from .images import PEXELS_ACCESS_KEY, UNSPLASH_ACCESS_KEY
from .models import Page
from .schemas import PageOut, PageSummary
from .seed_templates import resync_content, seed

# The only two hosts next.config.mjs allows next/image to load from -- an
# image_url outside these renders as a broken image on the site with
# nothing else here to ever flag it. Kept in sync with the same check
# images.py now applies before writing a URL in the first place; this list
# lets /admin/image-audit also surface any URL that slipped through before
# that filter existed.
_ALLOWED_IMAGE_HOSTS = ("https://images.unsplash.com/", "https://images.pexels.com/")


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Render's free-tier disk is ephemeral (resets on redeploy), so this
    # keeps the small template-review dataset self-healing without a manual
    # step. Real batch content will need a persistent database before launch.
    db = SessionLocal()
    try:
        seed(db)
        # Unlike seed(), this DOES touch pages that already exist -- see its
        # docstring for why a copy edit or a corrected stock-photo query
        # needs to reach already-seeded pages, not just freshly inserted
        # ones, without wiping out any photo already fetched for them.
        resync_content(db)

        # Backfills real stock photos for any page still missing one --
        # previously only reachable via the standalone script or the
        # /admin/fetch-images endpoint, which meant every new batch of
        # content needed a manual trigger to actually get photos. Safe to
        # run on every startup: fetch_images() skips any page that already
        # has an image with a plain dict check (no API call), so repeat
        # deploys with no new content do effectively nothing here, and only
        # genuinely new pages trigger a real Unsplash/Pexels search. Guarded
        # the same way the standalone script is, so this is a complete
        # no-op -- not even a page loop -- when no key is configured.
        if UNSPLASH_ACCESS_KEY or PEXELS_ACCESS_KEY:
            pages_updated, images_written = fetch_images(db)
            if images_written:
                print(f"Startup image fetch: {pages_updated} page(s) updated, {images_written} image(s) written.")
                _revalidate_frontend()
    finally:
        db.close()
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


@app.get("/pages/{slug}", response_model=PageOut)
def get_page(slug: str, db: Session = Depends(get_db)):
    page = db.query(Page).filter(Page.slug == slug).first()
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


def _summary_image(content: dict) -> tuple[str | None, dict | None, str | None]:
    """image_url, image_attribution, hero_image_query for a page's summary
    thumbnail. Category Roundup pages have no hero image of their own (only
    per-card images on recipe_cards), so this falls back to the first
    card's image as a representative thumbnail for the collection."""
    if content.get("image_url"):
        return content["image_url"], content.get("image_attribution"), content.get("hero_image_query")
    cards = content.get("recipe_cards")
    if cards:
        first = cards[0]
        return first.get("image_url"), first.get("image_attribution"), first.get("image_query")
    return None, None, content.get("hero_image_query")


@app.get("/pages", response_model=list[PageSummary])
def list_pages(
    template_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
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
    query = db.query(Page).order_by(Page.id)
    if template_type is not None:
        query = query.filter(Page.template_type == template_type)
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
        image_url, image_attribution, hero_image_query = _summary_image(page.content)
        summaries.append(
            PageSummary(
                slug=page.slug,
                template_type=page.template_type,
                title=page.title,
                image_url=image_url,
                image_attribution=image_attribution,
                hero_image_query=hero_image_query,
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
            image_url, image_attribution, hero_image_query = _summary_image(page.content)
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
    slugs: str | None = Query(default=None, description="Comma-separated page slugs to re-fetch, ignoring every other page. Always re-fetches the given slugs regardless of `force`."),
    db: Session = Depends(get_db),
):
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    only_slugs = {s.strip() for s in slugs.split(",") if s.strip()} if slugs else None

    log = io.StringIO()
    with redirect_stdout(log):
        pages_updated, images_written = fetch_images(db, force=force, only_slugs=only_slugs)

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
def image_audit(token: str, db: Session = Depends(get_db)):
    """A full-site image report with no external API calls -- a pure read
    of what's already in the database, gated behind the same
    ADMIN_TASK_TOKEN as /admin/fetch-images. Two kinds of problems this
    surfaces that clicking through pages one at a time can't:

    - `missing`: pages/cards with no image_url at all (shows as the
      placeholder box on the site).
    - `broken`: pages/cards whose image_url is set but points at a host
      next.config.mjs doesn't allowlist for next/image -- these render as
      a broken image, not a placeholder, which is easy to miss since
      nothing else in this pipeline currently detects it. (images.py now
      refuses to write one of these going forward, but this catches any
      that were already written before that check existed.)

    Every entry in `broken` needs `/admin/fetch-images?...&force=true` to
    get overwritten with a working URL -- force=false skips anything that
    already has *a* image_url, broken or not.
    """
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    missing = []
    broken = []

    def _check(url: str | None, **identity):
        if not url:
            missing.append(identity)
        elif not url.startswith(_ALLOWED_IMAGE_HOSTS):
            broken.append({**identity, "image_url": url})

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
    }
