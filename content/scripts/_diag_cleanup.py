"""Throwaway: rejects the test prospect row (id=59) created by
_diag_bacon_query.py's one-off replay, since it was only created to
diagnose why the pipeline produced no real row for that query -- not a
real prospect. Deleted after use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_cleanup.py
"""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(
        f"{base}/admin/outreach-queue/decide",
        auth=auth,
        params={"prospect_id": 59, "status": "rejected", "show": "queued"},
        timeout=30,
        allow_redirects=False,
    )
    print("status:", r.status_code)


if __name__ == "__main__":
    main()
