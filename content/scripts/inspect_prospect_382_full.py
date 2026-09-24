"""One-off: prints the full subject/body_preview/source_query for prospect
#382 so a follow-up script can rewrite them now that the real reporter
email has been recovered from the raw HARO digest excerpt the user pasted
(see diagnose_haro_ingestion_status.py -- #382/383/384 all show
contact_email=None because the digest was truncated at
_MAX_INGESTED_QUERY_CHARS=8000 right before item #14's Email: line).

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/inspect_prospect_382_full.py
"""

from __future__ import annotations

import os

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
PROSPECT_ID = 382


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "queued"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    row = next((row for row in r.json() if row["id"] == PROSPECT_ID), None)
    if row is None:
        raise RuntimeError(f"Prospect {PROSPECT_ID} not found at status=queued")

    for k, v in row.items():
        print(f"{k!r}: {v!r}")


if __name__ == "__main__":
    main()
