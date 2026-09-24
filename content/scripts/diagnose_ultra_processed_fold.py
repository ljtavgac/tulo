"""One-off diagnostic: dumps the full current record for outreach
prospects #382 (the original bundled 3-question manual reply), #383
(the "What Are Ultra-Processed Foods?" content_opportunity), and #384
(the "How to Reduce..." content_opportunity, whose source_query was
broadened to also cover "how much is too much") -- to see exactly what
_resolve_pending_articles actually did to each, rather than guessing
from the portal's rendered HTML.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/diagnose_ultra_processed_fold.py
"""

from __future__ import annotations

import json
import os

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
IDS = [382, 383, 384]


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "all"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    rows = {row["id"]: row for row in r.json() if row["id"] in IDS}

    for pid in IDS:
        row = rows.get(pid)
        if row is None:
            print(f"id={pid}: NOT FOUND\n")
            continue
        print(f"=== id={pid} ===")
        print(json.dumps(row, indent=2, default=str))
        print()


if __name__ == "__main__":
    main()
