"""One-off: fixes the 34 pre-existing bare (unsized) Pexels URLs found by
content/scripts/audit_bare_stock_image_urls.py (2026-09-20 site-wide
audit). Every one can only have been written via
/admin/review-queue/override-image (the only path capable of producing a
bare URL at all -- the automated pipeline always uses Pexels' own
pre-sized "large" variant), which has always unconditionally stamped
null attribution + source="manual_override" on every write, so
re-submitting each slug's own current (bare) URL through that same
endpoint is a safe no-op on attribution state while triggering this
session's new write-time normalization to fix the URL.

Runs against PROD, whose SIBLING_BACKEND_BASE_URL replication (confirmed
working 2026-09-20) mirrors each write onto staging automatically, which
already carries the identical bare URLs per the full image sync run
earlier today.

After the URL fix, runs apply-recovered-attribution across all 34 slugs
to fill in real photographer credit (now resolvable, since each is a
real Pexels photo ID) while preserving the manual_override tag.
"""

import os
import sys
import time

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
ADMIN_TASK_TOKEN = os.environ["ADMIN_TASK_TOKEN"]
REQUIRED_COMMIT = os.environ["REQUIRED_COMMIT"]


def get_with_retries(url, *, attempts=4, **kwargs):
    """requests.get with exponential backoff on transient connection errors
    (a bare ConnectionResetError killed the first run of this script partway
    through -- prod's own responses/errors still raise/return normally)."""
    for attempt in range(1, attempts + 1):
        try:
            return requests.get(url, **kwargs)
        except requests.exceptions.RequestException as exc:
            if attempt == attempts:
                raise
            wait = 2**attempt
            print(f"  (transient error on attempt {attempt}/{attempts}: {exc!r} -- retrying in {wait}s)")
            time.sleep(wait)

# The re-submission step below relies on write-time normalization
# (review_queue_override_image rejecting/fixing bare Pexels URLs) --
# refuse to run against a backend that hasn't deployed that fix yet,
# since without it this script would just re-write the same bare URLs.
deadline = time.time() + 720
while time.time() < deadline:
    try:
        health = requests.get(f"{BACKEND_BASE_URL}/health", timeout=20).json()
    except requests.RequestException:
        health = {}
    live_commit = health.get("git_commit") or ""
    if live_commit == REQUIRED_COMMIT:
        print(f"Backend is serving {REQUIRED_COMMIT} -- proceeding.")
        break
    print(f"Backend is on '{live_commit or '<unreachable>'}', waiting for {REQUIRED_COMMIT}...")
    time.sleep(15)
else:
    print(f"::error::Backend never reported serving {REQUIRED_COMMIT} within 12 minutes -- aborting, nothing written.")
    sys.exit(1)

BARE_URL_SLUGS = [
    "pumpkin-bars-with-cream-cheese-frosting",
    "panes-con-pollo-puerto-rican-chicken-salad-sandwiches",
    "poppy-seed-dressing",
    "strawberry-crunch-cake",
    "cake-mix-cookies",
    "stick-of-butter-rice",
    "mashed-rutabaga",
    "roasted-rutabaga-cubes",
    "rutabaga-fries",
    "neeps-and-tatties",
    "rutabaga-and-root-vegetable-soup",
    "brandy-alexander",
    "easy-baked-ziti",
    "dill-dip",
    "cement-mixer-shot",
    "special-k-bars",
    "cajeta-mexican-goat-s-milk-caramel",
    "cuban-oregano",
    "chilacayote",
    "greek-rice",
    "bicol-express",
    "coconut-jelly",
    "mustard-oil",
    "piquillo-peppers",
    "picaditas",
    "kadai-paneer-masala",
    "nduja-sausage",
    "potted-cake",
    "tamarind-candy",
    "what-is-horseradish",
    "baking-powder-vs-baking-soda",
    "baking-soda-substitute",
    "rutabaga-recipes",
    "how-to-steam-milk-for-a-latte",
]

# Step 1: read current state, confirm still bare, log attribution for a
# sanity check (never assumed blind).
r = get_with_retries(
    f"{BACKEND_BASE_URL}/admin/export-images",
    params={"token": ADMIN_TASK_TOKEN, "slugs": ",".join(BARE_URL_SLUGS)},
    timeout=60,
)
r.raise_for_status()
before = r.json()

print(f"=== Before state ({len(BARE_URL_SLUGS)} slugs) ===")
still_bare = []
for slug in BARE_URL_SLUGS:
    info = before.get(slug, {})
    url = info.get("image_url", "")
    attribution = info.get("image_attribution")
    is_bare = "images.pexels.com" in url and "w=" not in url
    print(f"{slug}: bare={is_bare} attribution={attribution}")
    if is_bare:
        still_bare.append((slug, url))

print(f"\n{len(still_bare)}/{len(BARE_URL_SLUGS)} confirmed still bare -- proceeding with those.")

# Step 2: re-submit each slug's own current URL through override-image,
# triggering write-time normalization.
failures = []
for slug, url in still_bare:
    resp = get_with_retries(
        f"{BACKEND_BASE_URL}/admin/review-queue/override-image",
        params={"token": ADMIN_TASK_TOKEN, "slug": slug, "image_url": url, "batch": "backfill-bare-url-fix-2026-09-20"},
        allow_redirects=False,
        timeout=30,
    )
    print(f"{slug}: override-image -> HTTP {resp.status_code}")
    if resp.status_code != 303:
        print(f"  UNEXPECTED: {resp.text[:300]}")
        failures.append(slug)
    time.sleep(0.3)

if failures:
    print(f"\n::error::{len(failures)} slug(s) failed to normalize: {failures}")

# Step 3: verify no bare URLs remain.
time.sleep(1.5)
r = get_with_retries(
    f"{BACKEND_BASE_URL}/admin/export-images",
    params={"token": ADMIN_TASK_TOKEN, "slugs": ",".join(BARE_URL_SLUGS)},
    timeout=60,
)
r.raise_for_status()
after = r.json()

print("\n=== After normalization ===")
remaining_bare = []
for slug in BARE_URL_SLUGS:
    info = after.get(slug, {})
    url = info.get("image_url", "")
    is_bare = "images.pexels.com" in url and "w=" not in url
    print(f"{slug}: {url} (bare={is_bare})")
    if is_bare:
        remaining_bare.append(slug)

if remaining_bare:
    print(f"\n::error::{len(remaining_bare)} slug(s) STILL bare after normalization: {remaining_bare}")
    sys.exit(1)

# Step 4: recover real attribution for all successfully-normalized slugs
# (preserves manual_override tag per this session's earlier fix).
recover_slugs = [s for s, _ in still_bare if s not in remaining_bare]
if recover_slugs:
    r = get_with_retries(
        f"{BACKEND_BASE_URL}/admin/apply-recovered-attribution",
        params={"token": ADMIN_TASK_TOKEN, "slugs": ",".join(recover_slugs), "dry_run": "false"},
        timeout=120,
    )
    r.raise_for_status()
    print("\n=== apply-recovered-attribution result ===")
    print(r.json())

print("\nDone.")
