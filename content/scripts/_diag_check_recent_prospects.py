"""Throwaway: prints the most recent outreach prospects (any pitch_type,
any status) so a human/agent can see what the ingest-email webhook
actually did with a just-forwarded digest, without portal access.
Deleted after use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_check_recent_prospects.py
"""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=30)
    r.raise_for_status()
    rows = sorted(r.json(), key=lambda row: row.get("created_at") or "", reverse=True)

    print(f"{len(rows)} total prospect(s) in the queue. Most recent 15:\n")
    for row in rows[:15]:
        print(
            f"id={row['id']} pitch_type={row['pitch_type']} status={row['status']} "
            f"created_at={row.get('created_at')}\n"
            f"  domain={row['target_domain']!r} contact_email={row.get('contact_email')!r}\n"
            f"  source_query={row.get('source_query')!r}\n"
            f"  subject={row.get('subject')!r}\n"
            f"  body_preview={(row.get('body_preview') or '')[:300]!r}\n"
        )


if __name__ == "__main__":
    main()
