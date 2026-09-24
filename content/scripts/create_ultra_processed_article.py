"""One-off: clicks "Create Article" for outreach prospect #384 (the
same POST the portal's own button sends) now that its source_query has
been broadened to include "how much is too much" -- see
update_ultra_processed_source_query.py. This flips the prospect's
status to article_requested and (per outreach_queue_create_article in
backend/app/main.py) auto-dispatches .github/workflows/generate-haro-
article.yml, which actually generates and pushes the page to staging.

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/create_ultra_processed_article.py
"""

from __future__ import annotations

import os

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
PROSPECT_ID = 384


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "article_pending"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    before = next((row for row in r.json() if row["id"] == PROSPECT_ID), None)
    if before is None:
        raise RuntimeError(f"Prospect {PROSPECT_ID} not found at status=article_pending -- already moved on?")
    print(f"Confirmed source_query before Create Article: {before['source_query']!r}\n")

    r = requests.post(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/create-article",
        data={"prospect_id": PROSPECT_ID, "show": "article_pending"},
        auth=AUTH, timeout=30, allow_redirects=False,
    )
    print(f"create-article -> HTTP {r.status_code}")
    r.raise_for_status()

    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "article_requested"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    after = next((row for row in r.json() if row["id"] == PROSPECT_ID), None)
    if after is None:
        raise RuntimeError(f"Prospect {PROSPECT_ID} did not move to status=article_requested -- check the response above.")
    print(f"\n*** CONFIRMED: prospect {PROSPECT_ID} is now status=article_requested, generation workflow dispatched. ***")


if __name__ == "__main__":
    main()
