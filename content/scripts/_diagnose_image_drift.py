"""One-off: pulls image_url/image_attribution for the two reported slugs
from both backends (root-cause evidence -- does staging's value look like
a fresh auto-search result, not a preserved manual override?), then runs
sync_staging_images_to_prod.py's own dry-run scan for the full-site diff.

Usage:
    PROD_BACKEND_BASE_URL=... PROD_ADMIN_TASK_TOKEN=... \
    STAGING_BACKEND_BASE_URL=... STAGING_ADMIN_TASK_TOKEN=... \
    python3 content/scripts/_diagnose_image_drift.py
"""

import json
import os

import requests

SLUGS = [
    "copycat-mcdonald-s-double-cheeseburger",
    "smoked-haddock-chowder",
]


def export_images(base_url, token, slugs):
    r = requests.get(
        f"{base_url.rstrip('/')}/admin/export-images",
        params={"token": token, "slugs": ",".join(slugs)},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main():
    prod_base = os.environ["PROD_BACKEND_BASE_URL"]
    prod_token = os.environ["PROD_ADMIN_TASK_TOKEN"]
    staging_base = os.environ["STAGING_BACKEND_BASE_URL"]
    staging_token = os.environ["STAGING_ADMIN_TASK_TOKEN"]

    prod_data = export_images(prod_base, prod_token, SLUGS)
    staging_data = export_images(staging_base, staging_token, SLUGS)

    print("=== Root-cause evidence for the 2 reported slugs ===")
    for slug in SLUGS:
        print(f"\n{slug}")
        print(f"  PROD:    {json.dumps(prod_data.get(slug), indent=2)}")
        print(f"  STAGING: {json.dumps(staging_data.get(slug), indent=2)}")


if __name__ == "__main__":
    main()
