"""Throwaway: checks ids 89-93 (the new latte content_opportunity
group) against 85/86 (the old orphaned duplicates from the now-rejected
reply 82's group -- same grind-size and cheap-tools ideas), then rejects
whichever of 85/86 turn out to be exact-title duplicates of something in
89-93. Deleted after use."""

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
    by_id = {row["id"]: row for row in rows}

    for target_id in (85, 86, 89, 90, 91, 92, 93):
        row = by_id.get(target_id)
        if row:
            print(f"id={target_id}: status={row['status']!r} title={row.get('proposed_title')!r} group={row.get('source_group_id')!r}")
        else:
            print(f"id={target_id}: not found")

    new_titles = {by_id[i]["proposed_title"] for i in (89, 90, 91, 92, 93) if i in by_id and by_id[i].get("proposed_title")}
    for old_id in (85, 86):
        old = by_id.get(old_id)
        if old and old.get("status") != "rejected" and old.get("proposed_title") in new_titles:
            rr = requests.get(
                f"{base}/admin/outreach-queue/decide",
                params={"prospect_id": old_id, "status": "rejected", "show": "all"},
                auth=auth, timeout=30, allow_redirects=False,
            )
            print(f"reject duplicate id={old_id} ({old['proposed_title']!r}) -> status={rr.status_code}")
        else:
            print(f"id={old_id}: no duplicate match found, leaving as-is")


if __name__ == "__main__":
    main()
