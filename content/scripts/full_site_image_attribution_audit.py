"""Full-site audit answering three questions in one pass, scoped to
PUBLISHED pages only (an unpublished/redirected page isn't part of "the
site" a visitor sees):

1. How many pages have no image at all.
2. Of the pages that DO have an image, how many have no attribution line
   under it (matches StockPhotoSlot.tsx's real render logic exactly, not
   just "photographer is null" -- an Unsplash-hosted photo with no
   photographer now gets a generic "Photo via Unsplash" credit as of
   2026-09-19, so it does NOT count as missing attribution here; only a
   Pexels-hosted photo with no photographer actually renders nothing).

Read-only, no network calls -- reads straight from SEED_PAGES."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.fetch_stock_images import SINGLE_IMAGE_TEMPLATES  # noqa: E402
from app.seed_templates import SEED_PAGES  # noqa: E402


def has_attribution_line(image_url: str, attribution: dict) -> bool:
    """Mirrors StockPhotoSlot.tsx exactly: Unsplash always gets a line
    (named or generic); every other host needs a real photographer."""
    if "images.unsplash.com" in image_url:
        return True
    return bool(attribution.get("photographer") and attribution.get("photographer_url"))


def main() -> None:
    no_image = {"single_image": [], "category_roundup_cards": []}
    no_attribution = []
    total_pages_in_scope = 0
    total_images_in_scope = 0

    for page in SEED_PAGES:
        content = page.get("content", {})
        if content.get("unpublished"):
            continue
        tt = page["template_type"]

        if tt in SINGLE_IMAGE_TEMPLATES:
            total_pages_in_scope += 1
            image_url = content.get("image_url")
            if not image_url:
                no_image["single_image"].append(page["slug"])
                continue
            total_images_in_scope += 1
            attribution = content.get("image_attribution") or {}
            if not has_attribution_line(image_url, attribution):
                no_attribution.append((page["slug"], image_url))

        elif tt == "category_roundup":
            for card in content.get("recipe_cards", []):
                total_pages_in_scope += 1
                image_url = card.get("image_url")
                if not image_url:
                    no_image["category_roundup_cards"].append(f'{page["slug"]} / {card.get("title")}')
                    continue
                total_images_in_scope += 1
                attribution = card.get("image_attribution") or {}
                if not has_attribution_line(image_url, attribution):
                    no_attribution.append((f'{page["slug"]} / {card.get("title")}', image_url))

        # homepage / static_page (some) / tool_page: no per-page image
        # mechanism at all -- not counted as "missing" since there's
        # nothing to check (static_page IS in SINGLE_IMAGE_TEMPLATES, so
        # it's already covered above).

    print("=" * 70)
    print("1. PAGES WITH NO IMAGE")
    print("=" * 70)
    print(f"Single-image-template pages with no image_url: {len(no_image['single_image'])}")
    for s in no_image["single_image"]:
        print(f"  {s}")
    print(f"Category-roundup cards with no image_url: {len(no_image['category_roundup_cards'])}")
    for s in no_image["category_roundup_cards"][:20]:
        print(f"  {s}")
    if len(no_image["category_roundup_cards"]) > 20:
        print(f"  ... and {len(no_image['category_roundup_cards']) - 20} more")
    total_no_image = len(no_image["single_image"]) + len(no_image["category_roundup_cards"])
    print(f"\nTotal image slots in scope: {total_pages_in_scope}")
    print(f"TOTAL WITH NO IMAGE: {total_no_image}")

    print()
    print("=" * 70)
    print("2. IMAGES PRESENT BUT NO ATTRIBUTION LINE RENDERED")
    print("=" * 70)
    print(f"(out of {total_images_in_scope} images that exist)")
    print(f"TOTAL: {len(no_attribution)}")
    for s, url in no_attribution:
        print(f"  {s}: {url}")


if __name__ == "__main__":
    main()
