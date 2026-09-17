"""One-off cleanup: rejects every queued, non-example haro_reply prospect
that isn't a real HARO/Connectively digest -- the backlog from forwarding
being set on the whole inbox (fixed now to only forward HARO mail, per the
user), which queued 30+ GitHub Actions notifications, Google/Snov.io
account-security alerts, marketing email, and phishing-pattern spam
alongside the one real digest.

Rule, not a guess: a real HARO digest's subject always starts with "HARO
Queries for" (see the sample subject "HARO Queries for September 17, 2026
- Morning Edition" that surfaced in this same backlog) -- Connectively's
own digest format hasn't been seen yet, so this only recognizes HARO's
pattern for now. Everything else queued as haro_reply and not an example
row gets rejected; nothing is deleted, sent, or approved -- reject only
flips status, same as clicking Reject in the portal, so it stays fully
reversible via the portal's own "undo" link per row if this over-rejects
something.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/reject_noise_haro_prospects.py
"""

from __future__ import annotations

import os

import requests


def _is_real_haro_digest(subject: str) -> bool:
    # Stored subject is "[Draft needed] Re: <original subject>" -- strip
    # that prefix before matching against HARO's own digest format.
    original = subject.removeprefix("[Draft needed] Re: ")
    return original.startswith("HARO Queries for")


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
    rows = [row for row in r.json() if not row["is_example"]]

    to_keep = [row for row in rows if _is_real_haro_digest(row["subject"])]
    to_reject = [row for row in rows if not _is_real_haro_digest(row["subject"])]

    print(f"{len(rows)} queued, non-example haro_reply rows total.")
    print(f"Keeping {len(to_keep)} real HARO digest(s):")
    for row in to_keep:
        print(f"  KEEP  id={row['id']}  {row['subject']!r}")

    print(f"Rejecting {len(to_reject)} noise row(s):")
    for row in to_reject:
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
