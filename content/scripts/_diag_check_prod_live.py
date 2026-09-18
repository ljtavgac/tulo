"""Throwaway diagnostic: hits the outreach portal (which runs
_resolve_pending_articles on every load -- checks target_slug against the
real prod URL, and flips status to "queued" with a real drafted email
once it's live) and reports prospect #38's current state. Deleted after
use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_check_prod_live.py
"""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    # Any GET to /admin/outreach-queue runs _resolve_pending_articles first.
    r = requests.get(f"{base}/admin/outreach-queue", auth=auth, timeout=60)
    print("outreach-queue load status:", r.status_code)

    r2 = requests.get(f"{base}/admin/outreach-queue/list.json", auth=auth, params={"status": "all"}, timeout=30)
    r2.raise_for_status()
    row = next((x for x in r2.json() if x["id"] == 38), None)
    print("prospect #38:", row)


if __name__ == "__main__":
    main()
