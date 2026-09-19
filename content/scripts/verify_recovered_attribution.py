"""One-off verification: confirms image_url is unchanged and image_attribution
now carries a real photographer for a sample of pages just fixed by
apply-recovered-attribution. Pure DB read via /admin/export-images -- no
provider API calls, so it never touches the already-strained Pexels quota.

Usage:
    BACKEND_BASE_URL=... ADMIN_TASK_TOKEN=... \\
    python3 content/scripts/verify_recovered_attribution.py slug=expected_image_url ...
"""

import os
import sys

import requests

EXPECTED = dict(arg.split("=", 1) for arg in sys.argv[1:])

base = os.environ["BACKEND_BASE_URL"].rstrip("/")
token = os.environ["ADMIN_TASK_TOKEN"]

r = requests.get(
    f"{base}/admin/export-images",
    params={"token": token, "slugs": ",".join(EXPECTED)},
    timeout=30,
)
r.raise_for_status()
data = r.json()

all_ok = True
for slug, expected_url in EXPECTED.items():
    info = data.get(slug, {})
    actual_url = info.get("image_url")
    attribution = info.get("image_attribution") or {}
    url_ok = actual_url == expected_url
    has_real_attribution = bool(attribution.get("photographer"))
    status = "OK" if (url_ok and has_real_attribution) else "MISMATCH"
    if status == "MISMATCH":
        all_ok = False
    print(f"{slug}: {status}")
    print(f"  image_url unchanged: {url_ok} ({actual_url})")
    print(f"  real attribution present: {has_real_attribution} ({attribution})")

sys.exit(0 if all_ok else 1)
