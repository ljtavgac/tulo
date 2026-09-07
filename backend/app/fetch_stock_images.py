"""
Maintenance script: fills in real stock photos (via images.py) for every
page that's missing one. Run manually, same pattern as seed_templates.py --
not an HTTP endpoint, since this hits free-tier external APIs and doesn't
need its own auth/rate-limit surface for what's fundamentally an occasional
batch operation.

No-ops safely with a clear message if no API keys are configured (see
images.py) -- safe to run at any time, keys present or not.

Usage:
    python -m app.fetch_stock_images            # skip pages that already have an image
    python -m app.fetch_stock_images --force     # re-fetch and overwrite existing images

Recipe, Ingredient Hub, How-To, Definition, Comparison, and Substitute
(single hero image) and Category Roundup (one image per recipe card) have
an image slot in their template -- Homepage and Tool pages don't, so
they're skipped entirely.
"""

import copy
import re
import sys

from sqlalchemy.orm import Session

from .database import SessionLocal
from .images import search_image, ping_download, UNSPLASH_ACCESS_KEY, PEXELS_ACCESS_KEY
from .models import Page

# template_type -> the content key holding the search query for a single
# hero image.
SINGLE_IMAGE_TEMPLATES = {
    "recipe_or_dish": "hero_image_query",
    "ingredient_hub": "hero_image_query",
    "howto_technique": "hero_image_query",
    "definition": "hero_image_query",
    "comparison": "hero_image_query",
    "substitute": "hero_image_query",
}

# Templates whose image represents a finished, plated dish rather than a raw
# ingredient or an in-progress technique shot. A bare dish name (e.g.
# "eggplant parmesan") searched against a general-purpose stock site often
# surfaces the raw ingredient or a generic product shot as the top match --
# appending a food-styling qualifier biases toward an actual prepared dish.
# Ingredient Hub/Definition/How-To keep the plain query: a raw or in-progress
# shot is the *correct* image there, not a bug to work around.
DISH_TEMPLATES = {"recipe_or_dish", "category_roundup"}


def _search_query_for(template_type: str, raw_query: str) -> str:
    if template_type in DISH_TEMPLATES:
        return f"{raw_query} plated dish"
    return raw_query


def _category_fallback_query(page_title: str) -> str:
    """A broader query to fall back to when a recipe card's own specific
    dish name (e.g. "nasu dengaku") has no match on Unsplash/Pexels -- a
    thin free-tier catalog is far more likely to have a photo for the
    parent category (e.g. "eggplant", from the page title "Eggplant
    Recipes") than for a niche regional dish name."""
    return re.sub(r"\s+recipes?$", "", page_title, flags=re.IGNORECASE).strip()


def _apply_result(content: dict, queries: list[str], template_type: str, used_urls: set[str]) -> bool:
    """Tries each query in `queries`, in order, and writes
    image_url/image_attribution into `content` in place from the first one
    that finds a result. Returns True if it found and wrote one."""
    for query in queries:
        search_query = _search_query_for(template_type, query)
        result = search_image(search_query, exclude_urls=frozenset(used_urls))
        if result is None:
            print(f"    no result for '{search_query}'")
            continue
        content["image_url"] = result.url
        content["image_attribution"] = {
            "photographer": result.photographer,
            "photographer_url": result.photographer_url,
            "source": result.source,
        }
        if result.source == "unsplash" and result.download_location:
            ping_download(result.download_location)
        used_urls.add(result.url)
        return True
    return False


def fetch_images(db: Session, force: bool = False) -> tuple[int, int]:
    """Returns (pages_updated, images_written)."""
    pages_updated = 0
    images_written = 0
    # Shared across the whole run so two different pages/cards never end up
    # with the literally same photo -- see search_image()'s exclude_urls.
    used_urls: set[str] = set()

    for page in db.query(Page).all():
        # A deep copy, not a reference: mutating page.content directly (or a
        # shallow copy of it, for category_roundup's nested recipe_cards)
        # would change the "before" value SQLAlchemy compares against too,
        # since it'd be the same object -- then the reassignment below looks
        # like a no-op and it silently never emits the UPDATE.
        content = copy.deepcopy(page.content)
        changed = False

        query_key = SINGLE_IMAGE_TEMPLATES.get(page.template_type)
        if query_key and query_key in content:
            if force or not content.get("image_url"):
                query = content[query_key]
                print(f"  {page.slug}: searching '{query}'...")
                try:
                    if _apply_result(content, [query], page.template_type, used_urls):
                        images_written += 1
                        changed = True
                except Exception as e:
                    print(f"    error: {e}")

        elif page.template_type == "category_roundup":
            for card in content.get("recipe_cards", []):
                if force or not card.get("image_url"):
                    query = card.get("image_query")
                    if not query:
                        continue
                    # A specific dish name (e.g. "nasu dengaku") often has no
                    # match in a free-tier catalog -- fall back to the
                    # page's own category (e.g. "Eggplant") so a card isn't
                    # left permanently blank just because its exact dish is
                    # too niche to have stock photos of its own.
                    fallback = _category_fallback_query(page.title)
                    queries = [query] if fallback.lower() == query.lower() else [query, fallback]
                    print(f"  {page.slug} / {card.get('title')}: searching '{query}'...")
                    try:
                        if _apply_result(card, queries, page.template_type, used_urls):
                            images_written += 1
                            changed = True
                    except Exception as e:
                        print(f"    error: {e}")

        if changed:
            page.content = content  # already an independent object -- see the deepcopy above
            pages_updated += 1

    db.commit()
    return pages_updated, images_written


if __name__ == "__main__":
    if not UNSPLASH_ACCESS_KEY and not PEXELS_ACCESS_KEY:
        print(
            "No UNSPLASH_ACCESS_KEY or PEXELS_ACCESS_KEY set -- nothing to do.\n"
            "Get free keys at https://unsplash.com/developers and/or "
            "https://www.pexels.com/api/, then set them as environment "
            "variables and re-run this script."
        )
        sys.exit(0)

    force = "--force" in sys.argv
    session = SessionLocal()
    try:
        updated, written = fetch_images(session, force=force)
        print(f"\nDone. {updated} page(s) updated, {written} image(s) written.")
    finally:
        session.close()
