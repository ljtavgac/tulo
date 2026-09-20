"""One-off: makes staging's image_url/image_attribution match prod's for
every page where they differ -- ONE DIRECTION ONLY, prod -> staging.
Never writes to prod; only ever reads it. Prod is production content the
user has already verified live; staging is the thing that's drifted.

Root cause of the drift: staging and prod are separate database
instances. An image change made directly against one (a manual override,
a re-fetch, an apply-baked-images run) only ever reaches that one
backend's rows -- nothing keeps the two databases' image fields in sync
with each other, only each one's own resync_content()/apply-baked-images
history. Confirmed live (2026-09-19) on how-to-cook-lobster and bbq-rub,
both showing different photos on staging than on prod.

Usage:
    PROD_BACKEND_BASE_URL=... PROD_ADMIN_TASK_TOKEN=... \\
    STAGING_BACKEND_BASE_URL=... STAGING_ADMIN_TASK_TOKEN=... \\
    DRY_RUN=true \\
    python3 content/scripts/sync_staging_images_to_prod.py
"""

import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.fetch_stock_images import SINGLE_IMAGE_TEMPLATES  # noqa: E402
from app.seed_templates import SEED_PAGES  # noqa: E402

PROD_BASE = os.environ["PROD_BACKEND_BASE_URL"].rstrip("/")
PROD_TOKEN = os.environ["PROD_ADMIN_TASK_TOKEN"]
STAGING_BASE = os.environ["STAGING_BACKEND_BASE_URL"].rstrip("/")
STAGING_TOKEN = os.environ["STAGING_ADMIN_TASK_TOKEN"]
DRY_RUN = os.environ.get("DRY_RUN", "true").strip().lower() != "false"

if PROD_BASE == STAGING_BASE:
    print("::error::PROD_BACKEND_BASE_URL and STAGING_BACKEND_BASE_URL are identical -- refusing to run.")
    sys.exit(1)

CHUNK_SIZE = 150


def export_images(base_url: str, token: str, slugs: list[str]) -> dict:
    result = {}
    for i in range(0, len(slugs), CHUNK_SIZE):
        chunk = slugs[i : i + CHUNK_SIZE]
        r = requests.get(
            f"{base_url}/admin/export-images",
            params={"token": token, "slugs": ",".join(chunk)},
            timeout=60,
        )
        r.raise_for_status()
        result.update(r.json())
    return result


slugs = sorted(
    {
        p["slug"]
        for p in SEED_PAGES
        if not p.get("content", {}).get("unpublished")
        and (p["template_type"] in SINGLE_IMAGE_TEMPLATES or p["template_type"] == "category_roundup")
    }
)
print(f"Checking {len(slugs)} published slugs across both backends...")

prod_data = export_images(PROD_BASE, PROD_TOKEN, slugs)
print(f"Exported {len(prod_data)} rows from PROD (read-only).")
staging_data = export_images(STAGING_BASE, STAGING_TOKEN, slugs)
print(f"Exported {len(staging_data)} rows from STAGING.")

mismatches = []
for slug in slugs:
    prod_row = prod_data.get(slug, {})
    staging_row = staging_data.get(slug, {})
    if "error" in prod_row or "error" in staging_row:
        continue
    prod_url = prod_row.get("image_url")
    if prod_url and prod_url != staging_row.get("image_url"):
        mismatches.append(slug)

print(f"\n{len(mismatches)} page(s) differ (staging will be updated to match prod's value):")
for slug in mismatches:
    print(f"  {slug}")
    print(f"    staging: {staging_data[slug].get('image_url')}")
    print(f"    prod:    {prod_data[slug].get('image_url')}")

if DRY_RUN:
    print("\nDRY RUN -- nothing written to staging. Re-run with DRY_RUN=false to apply.")
    sys.exit(0)

if not mismatches:
    print("\nNothing to sync.")
    sys.exit(0)

print(f"\nWriting {len(mismatches)} page(s) to STAGING only...")
failures = []
for slug in mismatches:
    payload = {
        "image_url": prod_data[slug]["image_url"],
        "image_attribution": prod_data[slug].get("image_attribution"),
    }
    r = requests.post(
        f"{STAGING_BASE}/admin/set-image-fields",
        params={"token": STAGING_TOKEN, "slug": slug},
        json=payload,
        timeout=30,
    )
    ok = r.status_code == 200
    print(f"  {slug}: HTTP {r.status_code}{'' if ok else ' -- ' + r.text}")
    if not ok:
        failures.append(slug)
    time.sleep(0.05)

print(f"\nDone. {len(mismatches) - len(failures)}/{len(mismatches)} written to staging.")
if failures:
    print(f"::error::{len(failures)} slug(s) failed: {failures}")
    sys.exit(1)
