"""One-off: finds every published page whose stored image_url is missing
the sizing query params fetch_stock_images.py's pipeline always bakes in
(Pexels: ?auto=compress&cs=tinysrgb&h=..&w=..; Unsplash: full ixid/ixlib/
q/w query string). A bare URL like that serves Pexels/Unsplash's
full-resolution original through StockPhotoSlot's `unoptimized` <Image>
-- confirmed live (2026-09-20): 1055 KB vs 43 KB and 1458 KB vs 27 KB for
the same two photos, a 24x-54x size difference that directly explains a
multi-second LCP regression on the two pages carrying one.

Queries PROD'S LIVE DATABASE directly, not git -- a manual override (the
only way a bare URL like this gets written; the automated pipeline
always appends these params) never gets baked back into git, per
_RUNTIME_IMAGE_KEYS, so a git-only check would undercount exactly the
pages this bug actually affects, same lesson as this session's earlier
image-drift investigation.
"""

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.fetch_stock_images import SINGLE_IMAGE_TEMPLATES  # noqa: E402
from app.seed_templates import SEED_PAGES  # noqa: E402

PROD_BASE = os.environ["PROD_BACKEND_BASE_URL"].rstrip("/")
PROD_TOKEN = os.environ["PROD_ADMIN_TASK_TOKEN"]
CHUNK_SIZE = 150


def is_bare(image_url: str) -> bool:
    if "images.pexels.com" in image_url:
        return "?" not in image_url or "w=" not in image_url
    if "images.unsplash.com" in image_url:
        return "?" not in image_url or "ixlib=" not in image_url
    return False  # some other allowed host -- not this bug's shape


slugs_by_type: dict[str, list[str]] = {}
for p in SEED_PAGES:
    if p.get("content", {}).get("unpublished"):
        continue
    tt = p["template_type"]
    if tt in SINGLE_IMAGE_TEMPLATES or tt == "category_roundup":
        slugs_by_type.setdefault(tt, []).append(p["slug"])

all_slugs = [s for slugs in slugs_by_type.values() for s in slugs]
print(f"Checking {len(all_slugs)} published slugs across {len(slugs_by_type)} template types...")

image_data: dict[str, dict] = {}
for i in range(0, len(all_slugs), CHUNK_SIZE):
    chunk = all_slugs[i : i + CHUNK_SIZE]
    r = requests.get(
        f"{PROD_BASE}/admin/export-images",
        params={"token": PROD_TOKEN, "slugs": ",".join(chunk)},
        timeout=60,
    )
    r.raise_for_status()
    image_data.update(r.json())

slug_to_type = {p["slug"]: p["template_type"] for p in SEED_PAGES}

bare_by_type: dict[str, list[tuple[str, str]]] = {}
total_checked = 0
for slug, info in image_data.items():
    if "error" in info:
        continue
    url = info.get("image_url")
    if not url:
        continue
    total_checked += 1
    if is_bare(url):
        tt = slug_to_type.get(slug, "unknown")
        bare_by_type.setdefault(tt, []).append((slug, url))

total_bare = sum(len(v) for v in bare_by_type.values())
print(f"\nChecked {total_checked} pages with a real image_url on prod.")
print(f"TOTAL bare (unsized) image URLs found: {total_bare}\n")

for tt, entries in sorted(bare_by_type.items(), key=lambda kv: -len(kv[1])):
    print(f"{tt}: {len(entries)}")
    for slug, url in entries:
        print(f"  {slug}: {url}")
    print()
