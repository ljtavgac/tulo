"""Throwaway: rejects prospect id=77, a raw-digest fallback placeholder
row created by an earlier real test of the max_tokens=4096 truncation
bug (already fixed, now max_tokens=8192). Deleted after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    r = requests.get(
        f"{base}/admin/outreach-queue/decide",
        params={"prospect_id": 77, "status": "rejected", "show": "all"},
        auth=auth, timeout=30, allow_redirects=False,
    )
    print(f"reject id=77 -> status={r.status_code}")


if __name__ == "__main__":
    main()
