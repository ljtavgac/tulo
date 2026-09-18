"""Throwaway diagnostic: lists all outreach prospects on staging and finds
any matching the "best way to cook bacon" HARO query (by source_query/
subject/contact_name), to check whether a fallback row already existed
from this morning's real digest run before _diag_bacon_query.py's
one-off replay created its own test row. Deleted after use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_list_bacon.py
"""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/admin/outreach-queue/list.json", auth=auth, params={"status": "all"}, timeout=30)
    r.raise_for_status()
    rows = r.json()
    print(f"{len(rows)} total prospects")

    hits = [
        row for row in rows
        if "bacon" in (row.get("source_query") or "").lower()
        or "bacon" in (row.get("subject") or "").lower()
        or "edwards" in (row.get("contact_name") or "").lower()
    ]
    print(f"\n{len(hits)} matching row(s):")
    for row in hits:
        print(f"\nid={row['id']} status={row['status']} created_at={row.get('created_at')}")
        print(f"  pitch_type={row.get('pitch_type')} contact_name={row.get('contact_name')!r} contact_email={row.get('contact_email')!r}")
        print(f"  subject={row.get('subject')!r}")
        print(f"  body_preview={row.get('body_preview')!r}")
        print(f"  source_query={row.get('source_query')!r}")


if __name__ == "__main__":
    main()
