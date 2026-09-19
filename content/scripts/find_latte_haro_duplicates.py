"""One-off investigation: lists every haro_reply prospect (any status)
whose subject/source_query/target_domain mentions "latte" or "Daily
Meal" -- read-only, no side effects -- so a human can see the full
history before deciding what (if anything) to reject as a duplicate of
an already-sent submission.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/find_latte_haro_duplicates.py
"""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(
        f"{base}/admin/outreach-queue/list.json",
        auth=auth,
        params={"status": "all", "pitch_type": "haro_reply"},
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json()

    def is_match(row: dict) -> bool:
        haystack = " ".join(
            str(row.get(k) or "") for k in ("subject", "source_query", "target_domain", "proposed_title")
        ).lower()
        return "latte" in haystack or "daily meal" in haystack

    matches = sorted((row for row in rows if is_match(row)), key=lambda r: r.get("created_at") or "")

    print(f"{len(matches)} haro_reply row(s) mentioning 'latte' or 'Daily Meal':\n")
    for row in matches:
        print(f"id={row['id']}  status={row['status']}  created_at={row.get('created_at')}  group={row.get('source_group_id')}")
        print(f"  target_domain: {row.get('target_domain')}")
        print(f"  subject:       {row.get('subject')}")
        print(f"  source_query:  {(row.get('source_query') or '')[:200]!r}")
        print(f"  sent_at:       {row.get('sent_at')}")
        print()


if __name__ == "__main__":
    main()
