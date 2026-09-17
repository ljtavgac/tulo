"""Temporary diagnostic: dumps every outreach prospect (all pitch types,
all statuses) to stdout via /admin/outreach-queue/list.json, to check
whether the 17 real tool_pitch prospects from add_outreach_prospects.py
are actually still in the database or not. Not part of the permanent
toolset -- delete once the mystery here is resolved."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/admin/outreach-queue/list.json", auth=auth, params={"status": "all"}, timeout=30)
    r.raise_for_status()
    rows = r.json()

    print(f"Total rows: {len(rows)}")
    for row in rows:
        print(
            f"id={row['id']} pitch_type={row['pitch_type']} domain={row['target_domain']} "
            f"is_example={row['is_example']} status={row['status']} sent_at={row['sent_at']} "
            f"send_error={row['send_error']}"
        )


if __name__ == "__main__":
    main()
