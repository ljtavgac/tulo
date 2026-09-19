"""Throwaway: checks the current body of the live latte (117) and
Southern Living (122) replies to see which already has a lead-in
sentence before the numbered list, then patches whichever doesn't via
update-content (preserves the already-verified numbered/placeholder
structure -- no need to re-draft from scratch for a wording tweak).
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
    by_id = {row["id"]: row for row in rows}

    for target_id in (117, 122):
        row = by_id.get(target_id)
        if not row:
            print(f"id={target_id}: not found")
            continue
        print(f"\n--- id={target_id} status={row['status']} ---")
        print(f"subject: {row['subject']!r}")
        print(f"body:\n{row['body_preview']}")


if __name__ == "__main__":
    main()
