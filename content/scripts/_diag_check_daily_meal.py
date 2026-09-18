"""Throwaway: finds the 'Daily Meal' prospect(s) in the outreach queue and
dumps full records to check why it didn't spin off additional
content_opportunity article suggestions the way the Southern Living retest
did. Deleted after use."""

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
        domain = (row.get("target_domain") or "")
        subject = (row.get("subject") or "")
        query = (row.get("source_query") or "")
        if "daily meal" in domain.lower() or "daily meal" in subject.lower() or "daily meal" in query.lower():
            print(f"\n--- id={row.get('id')} ---")
            for k, v in row.items():
                print(f"{k}: {v!r}")


if __name__ == "__main__":
    main()
