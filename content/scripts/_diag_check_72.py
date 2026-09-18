"""Throwaway: fetches the full record for prospects id=72 (target_domain
'Daily Meal', not created by any diagnostic test run this session -- so
it must have come through the live inbound webhook from a real
forwarded digest) and id=74 (the Connectively rerun's one drafted
opportunity, to see exactly what fired). Also lists every id currently
present, to check whether id=74 actually exists. Deleted after use."""

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
    ids_present = sorted(row.get("id") for row in rows)
    print(f"all ids present ({len(ids_present)} total): {ids_present}")
    for target_id in (72, 74):
        print(f"\n--- id={target_id} ---")
        found = False
        for row in rows:
            if row.get("id") == target_id:
                found = True
                for k, v in row.items():
                    print(f"{k}: {v!r}")
        if not found:
            print(f"id={target_id} not found")


if __name__ == "__main__":
    main()
