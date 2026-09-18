"""Throwaway: lists queued prospects missing contact_email, so real web
research can be done to find real addresses. Read-only. Deleted after use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_missing_emails.py
"""

from __future__ import annotations

import json
import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/admin/outreach-queue/list.json", auth=auth, params={"status": "queued"}, timeout=30)
    r.raise_for_status()
    rows = r.json()
    missing = [row for row in rows if not row.get("contact_email") and not row.get("is_example")]
    print(f"{len(rows)} queued total, {len(missing)} missing contact_email\n")
    for row in missing:
        print(json.dumps({
            "id": row["id"],
            "pitch_type": row["pitch_type"],
            "target_domain": row["target_domain"],
            "contact_name": row.get("contact_name"),
            "subject": row["subject"],
            "source_query": row.get("source_query"),
        }, indent=2))
        print("---")


if __name__ == "__main__":
    main()
