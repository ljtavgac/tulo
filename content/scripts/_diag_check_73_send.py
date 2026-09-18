"""Throwaway: fetches prospect id=73's full record to diagnose why an
approved Featured.com reply with a manually-added contact_email didn't
actually send. Deleted after use."""

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
        if row.get("id") == 73:
            for k, v in row.items():
                print(f"{k}: {v!r}")
            return
    print("id=73 not found")


if __name__ == "__main__":
    main()
