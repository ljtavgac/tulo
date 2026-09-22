"""One-off diagnostic: why kingarthurbaking.com got two separate outreach
prospects (one ~2 days ago, one today) despite the sourcing scripts' own
domain dedup (_existing_domains_and_emails / seen_domains). Prints every
row targeting that domain -- id, pitch_type, source_query, contact_email/
contact_form_url, status, created_at -- so the two rows can be compared
directly instead of guessing from script logs (which only show what a
sourcing script itself evaluated, not rows created by a different pipeline
like the HARO/Connectively inbound-digest ingestion).

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/diagnose_king_arthur_duplicate.py
"""

from __future__ import annotations

import os

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "all"},
        auth=AUTH,
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json()

    matches = [row for row in rows if "kingarthurbaking" in (row.get("target_domain") or "").lower()]
    print(f"Total rows in queue: {len(rows)}")
    print(f"Rows targeting kingarthurbaking.com (by target_domain): {len(matches)}\n")

    # Broader pass, in case a second row exists under a different
    # target_domain string (e.g. a manually-added row recorded "King Arthur
    # Baking" or similar rather than the bare domain) -- checks subject/
    # body_preview/target_domain together so a same-company duplicate
    # wouldn't be missed just because of how target_domain was spelled.
    broader = [
        row for row in rows
        if row not in matches
        and "king arthur" in (
            (row.get("target_domain") or "") + " " +
            (row.get("subject") or "") + " " +
            (row.get("body_preview") or "")
        ).lower()
    ]
    print(f"Additional rows mentioning \"king arthur\" under a different target_domain: {len(broader)}\n")

    for row in sorted(matches, key=lambda r: r.get("created_at") or ""):
        print(f"id={row['id']}")
        print(f"  pitch_type: {row.get('pitch_type')}")
        print(f"  target_domain: {row.get('target_domain')!r}")
        print(f"  source_platform: {row.get('source_platform')}")
        print(f"  source_group_id: {row.get('source_group_id')}")
        print(f"  source_query: {row.get('source_query')!r}")
        print(f"  contact_email: {row.get('contact_email')!r}")
        print(f"  contact_form_url: {row.get('contact_form_url')!r}")
        print(f"  status: {row.get('status')}")
        print(f"  is_example: {row.get('is_example')}")
        print(f"  created_at: {row.get('created_at')}")
        print(f"  subject: {row.get('subject')!r}")
        print()


if __name__ == "__main__":
    main()
