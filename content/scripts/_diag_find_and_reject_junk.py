"""Throwaway: finds the "[Draft needed] Re: Welcome to HARO..." junk row
(a HARO account-verification email that slipped through as a
placeholder) and rejects it. Deleted after use."""

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
    matches = [row for row in rows if "welcome to haro" in (row.get("subject") or "").lower()]
    if not matches:
        print("no matching junk row found")
        return
    for row in matches:
        prospect_id = row["id"]
        rr = requests.get(
            f"{base}/admin/outreach-queue/decide",
            params={"prospect_id": prospect_id, "status": "rejected"},
            auth=auth,
            timeout=60,
            allow_redirects=False,
        )
        print(f"found id={prospect_id} subject={row.get('subject')!r} -> reject status={rr.status_code}")


if __name__ == "__main__":
    main()
