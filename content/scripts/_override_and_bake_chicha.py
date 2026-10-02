"""One-off: set the chicha page's image on staging (working around the
buggy admin portal) and immediately bake that same image_url/attribution
into seed_templates.py in the SAME push, so this page's content commit
carries its own correct image from the start.

This sidesteps the exact gap found with the chicken-tender batch: that
batch's image was only ever set in staging's live DB, so when the batch's
content later merged to main via a manual conflict resolution (bypassing
merge-approved-batch.yml's own bake step), the new prod row got inserted
with no image at all, and the later separate bake-to-git came too late to
reach the already-existing row (resync_content()/seed() never touch
image_url on an existing row, by design). Baking the image into git NOW,
as part of this same content change, means seed()'s eventual insert on
main already has the right photo embedded -- no dependency on a
post-merge bake step succeeding, whether or not that merge is a clean
cherry-pick or needs manual resolution.

Usage:
    BACKEND_BASE_URL=https://tulo-backend-staging.onrender.com \
    ADMIN_TASK_TOKEN=... \
    python3 content/scripts/_override_and_bake_chicha.py
"""

from __future__ import annotations

import os
import sys

import requests

sys.path.insert(0, os.path.dirname(__file__))
from bake_images_from_staging import bake  # noqa: E402

SLUG = "what-is-chicha-peru-s-traditional-fermented-corn-drink"
# Pre-sized (not a bare Pexels URL) so the backend's override-image endpoint
# skips its live Pexels lookup entirely -- that lookup hit a 429 rate limit
# the last time this ran against a bare URL.
IMAGE_URL = "https://images.pexels.com/photos/28490841/pexels-photo-28490841.jpeg?auto=compress&cs=tinysrgb&w=1260"


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    token = os.environ["ADMIN_TASK_TOKEN"]

    r = requests.get(
        f"{base}/admin/review-queue/override-image",
        params={"token": token, "slug": SLUG, "image_url": IMAGE_URL, "batch": "all"},
        timeout=30,
        allow_redirects=False,
    )
    if r.status_code != 303:
        print(f"override-image FAILED ({r.status_code}): {r.text[:300]}", file=sys.stderr)
        sys.exit(1)
    print(f"{SLUG}: image set on staging")

    bake(base, token, [SLUG])


if __name__ == "__main__":
    main()
