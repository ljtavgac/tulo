"""Throwaway: fetches the full record for prospect id=72 (target_domain
'Daily Meal') to determine its real source digest/outlet, since it
wasn't created by any diagnostic test run this session -- it must have
come through the live inbound webhook from a real forwarded digest.
Deleted after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    for row in rows:
        if row.get("id") == 72:
            for k, v in row.items():
                print(f"{k}: {v!r}")
            return
    print("id=72 not found")


if __name__ == "__main__":
    main()
