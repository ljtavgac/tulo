"""Throwaway: dumps full detail (status, subject, body_preview,
source_group_id, target_slug) for the Southern Living reply (122) and its
two content_opportunity siblings (123, 124) so the exact duplicate-reply
state can be inspected before writing a corrective patch. Deleted after
use."""

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

    for target_id in (117, 122, 123, 124):
        row = by_id.get(target_id)
        if not row:
            print(f"id={target_id}: not found")
            continue
        print(f"--- id={target_id} ---")
        print(f"  status={row.get('status')!r}")
        print(f"  source_group_id={row.get('source_group_id')!r}")
        print(f"  proposed_title={row.get('proposed_title')!r}")
        print(f"  proposed_template_type={row.get('proposed_template_type')!r}")
        print(f"  target_slug={row.get('target_slug')!r}")
        print(f"  subject={row.get('subject')!r}")
        print(f"  body_preview={row.get('body_preview')!r}")
        print()


if __name__ == "__main__":
    main()
