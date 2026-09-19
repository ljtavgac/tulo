"""One-off verification: prints the current image_url and image_attribution
for a sample of pages just fixed by apply-recovered-attribution, via a
pure DB read (/admin/export-images -- no provider API calls, so it never
touches the already-strained Pexels quota). Compare image_url by eye
against the "current_image_url" value captured in the report run's own
log from before the write -- avoids passing full URLs (with query-string
&s) as shell arguments, which a prior version of this script got wrong.

Usage:
    BACKEND_BASE_URL=... ADMIN_TASK_TOKEN=... \\
    python3 content/scripts/verify_recovered_attribution.py slug-one slug-two ...
"""

import os
import sys

import requests

slugs = sys.argv[1:]

base = os.environ["BACKEND_BASE_URL"].rstrip("/")
token = os.environ["ADMIN_TASK_TOKEN"]

r = requests.get(
    f"{base}/admin/export-images",
    params={"token": token, "slugs": ",".join(slugs)},
    timeout=30,
)
r.raise_for_status()
data = r.json()

for slug in slugs:
    info = data.get(slug, {})
    print(f"{slug}:")
    print(f"  image_url: {info.get('image_url')}")
    print(f"  image_attribution: {info.get('image_attribution')}")
