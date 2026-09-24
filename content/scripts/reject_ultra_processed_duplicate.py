"""One-off: rejects outreach prospect #384 -- the duplicate "sub
submission" that never auto-folded into #382's reply (see
diagnose_ultra_processed_fold.py and the fix in
_resolve_pending_articles). #382 already carries #384's own URL for
both point 2 and point 3, so sending #384 separately would pitch
Healthline the same source twice for the same story. Verifies the
rejection actually took before declaring success.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/reject_ultra_processed_duplicate.py
"""

from __future__ import annotations

import os

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
PROSPECT_ID = 384


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/decide",
        params={"prospect_id": PROSPECT_ID, "status": "rejected", "show": "queued"},
        auth=AUTH, timeout=30, allow_redirects=False,
    )
    print(f"decide -> HTTP {r.status_code}")
    r.raise_for_status()

    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "rejected"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    row = next((row for row in r.json() if row["id"] == PROSPECT_ID), None)
    if row is not None:
        print(f"*** CONFIRMED: prospect {PROSPECT_ID} is now status=rejected. ***")
    else:
        raise RuntimeError(f"Prospect {PROSPECT_ID} not found at status=rejected -- reject may not have taken.")


if __name__ == "__main__":
    main()
