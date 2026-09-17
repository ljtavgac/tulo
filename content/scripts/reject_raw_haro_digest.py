"""One-off cleanup: rejects the queued, non-example haro_reply row(s) whose
subject matches HARO's own digest format ("HARO Queries for ...") -- the
raw, un-split digest queued before _draft_haro_replies existed. Confirmed
by hand that none of that digest's 20 individual queries were a genuine
fit for Tulo, so there's nothing to draft from it; going forward, new
digests are split into real per-query drafts automatically (or queue
nothing at all if none fit) instead of landing as one raw row like this.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/reject_raw_haro_digest.py
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
        params={"status": "queued", "pitch_type": "haro_reply"},
        timeout=30,
    )
    r.raise_for_status()
    rows = [row for row in r.json() if not row["is_example"] and row["subject"].startswith("HARO Queries for")]

    print(f"{len(rows)} raw HARO digest row(s) to reject.")
    for row in rows:
        resp = requests.get(
            f"{base}/admin/outreach-queue/decide",
            auth=auth,
            params={"prospect_id": row["id"], "status": "rejected", "show": "queued"},
            timeout=30,
            allow_redirects=False,
        )
        ok = resp.status_code == 303
        print(f"  {'rejected' if ok else f'FAILED ({resp.status_code})'}  id={row['id']}  {row['subject']!r}")


if __name__ == "__main__":
    main()
