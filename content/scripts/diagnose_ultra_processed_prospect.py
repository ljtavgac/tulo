"""One-off diagnostic: find the "ultra-processed food" outreach
opportunity currently in the queue and print its full record, so the
target article, its slug/template_type, and the exact HARO/reporter
questions it's meant to answer can be seen directly instead of guessed.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/diagnose_ultra_processed_prospect.py
"""

from __future__ import annotations

import json
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
    print(f"Total rows in queue: {len(rows)}\n")

    matches = [
        row for row in rows
        if "ultra" in json.dumps(row).lower() and "process" in json.dumps(row).lower()
    ]
    print(f"Rows mentioning 'ultra' + 'process': {len(matches)}\n")
    for row in matches:
        print(json.dumps(row, indent=2, default=str))
        print()


if __name__ == "__main__":
    main()
