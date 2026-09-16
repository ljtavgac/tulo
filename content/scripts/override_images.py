"""One-off, explicit-list image restore: calls
/admin/review-queue/override-image for a fixed slug -> image_url map, one
request per slug -- the same single-page, exact-URL tool the admin portal
itself uses, never a search. Built to restore prod-verified images for a
handful of old substitute pages without touching anything else: no
site-wide scan, no query-based fetch, so it structurally cannot collide
with a page someone is actively curating elsewhere.

Note: this endpoint always stamps image_attribution as
{"source": "manual_override", photographer: None} -- it has no field for a
real photographer credit, so restoring via this path trades that credit
line away. Acceptable for a one-off repair; not a reason to build a new
backend endpoint just for this.

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    ADMIN_TASK_TOKEN=... \
    python3 content/scripts/override_images.py '{"slug-a": "https://images.pexels.com/...", ...}'
"""

from __future__ import annotations

import json
import os
import sys

import requests


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: override_images.py '<json map of slug -> image_url>'", file=sys.stderr)
        sys.exit(1)

    slug_to_url: dict[str, str] = json.loads(sys.argv[1])
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    token = os.environ["ADMIN_TASK_TOKEN"]

    for slug, image_url in slug_to_url.items():
        r = requests.get(
            f"{base}/admin/review-queue/override-image",
            params={"token": token, "slug": slug, "image_url": image_url, "batch": "all"},
            timeout=30,
            allow_redirects=False,
        )
        if r.status_code == 303:
            print(f"{slug}: set")
        else:
            print(f"{slug}: FAILED ({r.status_code}) {r.text[:200]}")


if __name__ == "__main__":
    main()
