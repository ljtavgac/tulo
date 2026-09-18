"""Throwaway: prints prospect id=70 (the manual-submission test row) in
full, to verify contact_email is null and the subject carries the
"[Manual submission -- ...]" prefix. Deleted after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=30)
    r.raise_for_status()
    for row in r.json():
        if row["id"] == 70:
            for k, v in row.items():
                print(f"  {k}={v!r}")
            return
    print("id=70 not found")


if __name__ == "__main__":
    main()
