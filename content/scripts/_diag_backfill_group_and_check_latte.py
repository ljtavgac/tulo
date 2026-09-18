"""Throwaway: (1) backfills source_group_id onto the already-queued
Southern Living content_opportunity items (78/79/80), which predate the
source_group_id field, so the portal's new 'linked items' note shows up
for them; (2) fetches the freshly re-drafted daily-meal/latte prospect
to check the max_tokens=8192 fix actually produced a clean result this
time. Deleted after use."""

from __future__ import annotations

import os
import uuid

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    group_id = uuid.uuid4().hex
    for prospect_id in (78, 79, 80):
        r = requests.get(
            f"{base}/admin/outreach-queue/update-source-group",
            params={"prospect_id": prospect_id, "source_group_id": group_id, "show": "all"},
            auth=auth, timeout=30, allow_redirects=False,
        )
        print(f"backfill group on id={prospect_id} -> status={r.status_code}")

    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    for row in sorted(rows, key=lambda r: r.get("id") or 0):
        query = (row.get("source_query") or "").lower()
        if "latte" in query:
            print(f"\n--- id={row.get('id')} ---")
            for k, v in row.items():
                print(f"{k}: {v!r}")


if __name__ == "__main__":
    main()
