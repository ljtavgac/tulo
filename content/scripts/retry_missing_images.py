"""One-off repair: re-run the image fetch for a specific list of slugs that
came out of a daily_batch.py run with no image_url yet (the run's own log
names them explicitly: "Skipped N slug(s) with no image_url yet on
staging"), then bake the result into seed_templates.py and commit to
staging -- the exact same two steps daily_batch.py itself runs
automatically for a batch's slugs, just re-targeted at the leftovers a
first pass didn't get a stock-photo match for.

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    ADMIN_TASK_TOKEN=... \
    python3 content/scripts/retry_missing_images.py --batch-number 10 \
        slug-one slug-two slug-three
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from daily_batch import bake_batch_images, fetch_images_for_batch  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="+", help="Slugs to re-fetch images for")
    parser.add_argument("--batch-number", type=int, required=True)
    args = parser.parse_args()

    pages_updated, images_written = fetch_images_for_batch(args.slugs)
    print(f"Fetched: {pages_updated} page(s) updated, {images_written} image(s) written.")

    still_missing = len(args.slugs) - images_written
    if still_missing > 0:
        print(f"{still_missing} slug(s) still have no image after this retry (no match found again).")

    bake_batch_images(args.slugs, args.batch_number)


if __name__ == "__main__":
    main()
