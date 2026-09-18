"""Throwaway: lists the most recent outreach prospects with full detail
(id, target_domain, subject, contact_email, pitch_type, status) to
identify a specific item the user is looking at in the portal and check
the result of the Featured.com/Connectively pipeline rerun. Deleted
after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    rows = sorted(rows, key=lambda x: x.get("id", 0), reverse=True)
    for row in rows[:20]:
        print(
            f"id={row.get('id')} status={row.get('status')} pitch_type={row.get('pitch_type')} "
            f"target_domain={row.get('target_domain')!r} contact_email={row.get('contact_email')!r} "
            f"subject={row.get('subject')!r}"
        )


if __name__ == "__main__":
    main()
