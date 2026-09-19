"""One-off: applies the user's chosen replacement Pexels photos to the two
pages that were silently reverted by apply-baked-images run #73
(baking-soda-substitute, baking-powder-vs-baking-soda -- see the
2026-09-19 investigation), then recovers real photographer attribution
for each new photo. Runs against PROD via the existing admin endpoints:

1. /admin/review-queue/override-image -- sets the new image_url, stamps
   source="manual_override" (now protected from apply-baked-images by
   this session's guard fix, which must already be deployed -- this
   script polls /health first to confirm).
2. /admin/apply-recovered-attribution -- looks up the new photo's real
   Pexels credit and fills it in, while preserving the manual_override
   tag (also part of this session's fix).
"""

import os
import sys
import time

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
ADMIN_TASK_TOKEN = os.environ["ADMIN_TASK_TOKEN"]
REQUIRED_COMMIT = os.environ["REQUIRED_COMMIT"]

FIXES = {
    "baking-soda-substitute": "https://images.pexels.com/photos/743984/pexels-photo-743984.jpeg",
    "baking-powder-vs-baking-soda": "https://images.pexels.com/photos/8477743/pexels-photo-8477743.jpeg",
}

deadline = time.time() + 720
while time.time() < deadline:
    try:
        health = requests.get(f"{BACKEND_BASE_URL}/health", timeout=20).json()
    except requests.RequestException:
        health = {}
    live_commit = health.get("git_commit") or ""
    if live_commit == REQUIRED_COMMIT:
        print(f"Prod is serving {REQUIRED_COMMIT} -- proceeding.")
        break
    print(f"Prod is on '{live_commit or '<unreachable>'}', waiting for {REQUIRED_COMMIT}...")
    time.sleep(15)
else:
    print(f"::error::Prod never reported serving {REQUIRED_COMMIT} within 12 minutes -- aborting, nothing written.")
    sys.exit(1)

for slug, image_url in FIXES.items():
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/review-queue/override-image",
        params={"token": ADMIN_TASK_TOKEN, "slug": slug, "image_url": image_url, "batch": "manual-fix-2026-09-19"},
        allow_redirects=False,
        timeout=30,
    )
    print(f"{slug}: override-image -> HTTP {r.status_code}")
    if r.status_code != 303:
        print(f"::error::{slug}: unexpected response: {r.text}")
        sys.exit(1)

time.sleep(1.5)  # let the writes commit before the attribution lookup reads them back

r = requests.get(
    f"{BACKEND_BASE_URL}/admin/apply-recovered-attribution",
    params={"token": ADMIN_TASK_TOKEN, "slugs": ",".join(FIXES), "dry_run": "false"},
    timeout=60,
)
r.raise_for_status()
print("apply-recovered-attribution result:")
print(r.json())
