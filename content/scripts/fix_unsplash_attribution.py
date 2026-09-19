"""One-off compliance repair: re-fetches a real, properly-attributed photo
for a fixed list of slugs whose current image_attribution is missing the
photographer (the 30 pages found by the 2026-09-19 audit with
"source": "manual_override" -- see /admin/review-queue/override-image's
own docstring for why that path always discarded attribution -- and an
images.unsplash.com URL specifically, a genuine Unsplash API Terms
violation, not just a style gap the way the same issue on a Pexels URL
would be).

Two steps, same ones daily_batch.py itself runs automatically for a new
batch's slugs: force a fresh fetch via /admin/fetch-images (always
re-fetches the given slugs regardless of the page's current image, see
that endpoint's own docstring), then bake the result into
seed_templates.py as literal data via bake_images_from_staging.bake() so
production's own seed data reflects it too, not just the runtime DB this
call just touched. Only the fetch step and step timing is why this isn't
just a call to override_images.py -- there's no specific URL to pin here,
just "get this page a real photo with real attribution."

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    ADMIN_TASK_TOKEN=... \
    python3 content/scripts/fix_unsplash_attribution.py slug-one slug-two ...
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_images_from_staging import bake  # noqa: E402


def main() -> None:
    slugs = sys.argv[1:]
    if not slugs:
        print("Usage: fix_unsplash_attribution.py slug-one slug-two ...", file=sys.stderr)
        sys.exit(1)

    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    token = os.environ["ADMIN_TASK_TOKEN"]

    print(f"Force re-fetching {len(slugs)} slug(s)...")
    r = requests.get(
        f"{base}/admin/fetch-images",
        params={"token": token, "slugs": ",".join(slugs)},
        timeout=1800,
    )
    r.raise_for_status()
    result = r.json()
    print(f"Fetch result: {result['pages_updated']} page(s) updated, {result['images_written']} image(s) written.")
    for line in result.get("log", []):
        print(f"  {line}")

    print(f"\nBaking new image_url/image_attribution into seed_templates.py for {len(slugs)} slug(s)...")
    bake(base, token, slugs)


if __name__ == "__main__":
    main()
