"""General-purpose one-off: rejects a specific, explicit list of outreach
prospect IDs via the same /admin/outreach-queue/decide endpoint the
portal's own Reject button calls -- for a case (like a confirmed-duplicate
digest resend) that needs one exact set of IDs rejected, not a rule a
script can apply automatically. Nothing is deleted, sent, or approved;
reject only flips status, reversible via the portal's own undo link per
row.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/reject_prospects.py --ids 146,147,148,149
"""

from __future__ import annotations

import argparse
import os

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", required=True, help="Comma-separated prospect IDs to reject")
    args = parser.parse_args()
    ids = [int(x) for x in args.ids.split(",") if x.strip()]

    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(
        f"{base}/admin/outreach-queue/list.json",
        auth=auth,
        params={"status": "all"},
        timeout=30,
    )
    r.raise_for_status()
    by_id = {row["id"]: row for row in r.json()}

    for prospect_id in ids:
        row = by_id.get(prospect_id)
        if row is None:
            print(f"  SKIP  id={prospect_id}  not found")
            continue
        resp = requests.get(
            f"{base}/admin/outreach-queue/decide",
            auth=auth,
            params={"prospect_id": prospect_id, "status": "rejected", "show": "all"},
            timeout=30,
            allow_redirects=False,
        )
        ok = resp.status_code == 303
        print(f"  {'rejected' if ok else f'FAILED ({resp.status_code})'}  id={prospect_id}  {row['subject']!r}")


if __name__ == "__main__":
    main()
