"""Throwaway: rejects every still-queued outreach prospect that has no
contact_email -- the credible-but-unreachable candidates queued before
the daily_outreach_sourcing.py pipeline was changed to skip those
outright instead of queuing them. Deleted after use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_reject_no_email.py
"""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "queued"}, auth=auth, timeout=30)
    r.raise_for_status()
    targets = [row for row in r.json() if not (row.get("contact_email") or "").strip()]

    print(f"{len(targets)} queued prospect(s) with no contact_email -- rejecting:")
    for row in targets:
        resp = requests.get(
            f"{base}/admin/outreach-queue/decide",
            auth=auth,
            params={"prospect_id": row["id"], "status": "rejected", "show": "queued"},
            timeout=30,
            allow_redirects=False,
        )
        ok = resp.status_code == 303
        print(f"  id={row['id']} {row.get('target_domain')} {'OK' if ok else f'FAILED ({resp.status_code})'}")


if __name__ == "__main__":
    main()
