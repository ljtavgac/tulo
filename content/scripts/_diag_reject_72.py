"""Throwaway: rejects prospect id=72, the original pre-fix daily-meal/
latte reply (drafted before the many-sub-question format, content_
opportunity extension, and source_group_id linking all existed) --
superseded by the clean re-draft at id=82 plus its 5 linked content_
opportunity siblings (83-87). Deleted after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    r = requests.get(
        f"{base}/admin/outreach-queue/decide",
        params={"prospect_id": 72, "status": "rejected", "show": "all"},
        auth=auth, timeout=30, allow_redirects=False,
    )
    print(f"reject id=72 -> status={r.status_code}")


if __name__ == "__main__":
    main()
