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

Only Recipe, Ingredient Hub, How-To, Definition (single hero image) and
Category Roundup (one image per recipe card) have an image slot in their
template -- Comparison, Substitute, Homepage, and Tool pages don't, so
they're skipped entirely.
"""

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
}


def _apply_result(content: dict, query: str) -> bool:
    """Looks up an image for `query` and writes image_url/image_attribution
    into `content` in place. Returns True if it found and wrote one."""
    result = search_image(query)
    if result is None:
        return False
    content["image_url"] = result.url
    content["image_attribution"] = {
        "photographer": result.photographer,
        "photographer_url": result.photographer_url,
        "source": result.source,
    }
    if result.source == "unsplash" and result.download_location:
        ping_download(result.download_location)
    return True


def fetch_images(db: Session, force: bool = False) -> tuple[int, int]:
    """Returns (pages_updated, images_written)."""
    pages_updated = 0
    images_written = 0

    for page in db.query(Page).all():
        content = page.content
        changed = False

        query_key = SINGLE_IMAGE_TEMPLATES.get(page.template_type)
        if query_key and query_key in content:
            if force or not content.get("image_url"):
                query = content[query_key]
                print(f"  {page.slug}: searching '{query}'...")
                try:
                    if _apply_result(content, query):
                        images_written += 1
                        changed = True
                    else:
                        print(f"    no result for '{query}'")
                except Exception as e:
                    print(f"    error: {e}")

        elif page.template_type == "category_roundup":
            for card in content.get("recipe_cards", []):
                if force or not card.get("image_url"):
                    query = card.get("image_query")
                    if not query:
                        continue
                    print(f"  {page.slug} / {card.get('title')}: searching '{query}'...")
                    try:
                        if _apply_result(card, query):
                            images_written += 1
                            changed = True
                        else:
                            print(f"    no result for '{query}'")
                    except Exception as e:
                        print(f"    error: {e}")

        if changed:
            page.content = dict(content)  # reassign so SQLAlchemy detects the JSON mutation
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
