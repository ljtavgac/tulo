"""Throwaway: sets source_platform='HARO' on prospect id=72 (the 'Daily
Meal' latte-technique query), per the user's confirmation of its real
source. Deleted after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    r = requests.get(
        f"{base}/admin/outreach-queue/update-source-platform",
        params={"prospect_id": 72, "source_platform": "HARO"},
        auth=auth,
        timeout=60,
        allow_redirects=False,
    )
    print(f"prospect_id=72 platform='HARO' status={r.status_code}")


if __name__ == "__main__":
    main()
