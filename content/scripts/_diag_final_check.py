"""Throwaway: minimal final check -- live frontend status code, plus
prospect #38's current status after triggering _resolve_pending_articles.
Deleted after use."""

from __future__ import annotations

import os

import requests

PROD_URL = "https://tulo.io/food/comparisons/butter-vs-shortening-vs-oil-for-greasing-pans-which-works-best"


def main() -> None:
    r = requests.get(PROD_URL, timeout=15)
    print(f"FRONTEND_STATUS={r.status_code}")

    base = os.environ["STAGING_BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    requests.get(f"{base}/admin/outreach-queue", auth=auth, timeout=60)
    r2 = requests.get(f"{base}/admin/outreach-queue/list.json", auth=auth, params={"status": "all"}, timeout=30)
    row = next((x for x in r2.json() if x["id"] == 38), None)
    print(f"PROSPECT_STATUS={row['status'] if row else 'NOT FOUND'}")
    if row and row["status"] == "queued":
        print(f"SUBJECT={row['subject']!r}")
        print(f"BODY={row['body_preview']!r}")


if __name__ == "__main__":
    main()
