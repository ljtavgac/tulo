"""Throwaway diagnostic: checks the current real state of prospect #38
(the butter-vs-shortening-vs-oil HARO article opportunity) and whether
the new inline review card actually renders for it on the live outreach
portal. Deleted after use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_check_38.py
"""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/admin/outreach-queue/list.json", auth=auth, params={"status": "all"}, timeout=30)
    r.raise_for_status()
    rows = r.json()
    row = next((r_ for r_ in rows if r_["id"] == 38), None)
    print("prospect #38:", row)

    if row:
        for show in [row["status"], "all"]:
            page = requests.get(f"{base}/admin/outreach-queue", auth=auth, params={"show": show}, timeout=30)
            has_card = f'id="38"' in page.text or "/38&" in page.text or f"prospect_id=38" in page.text
            has_review = "article-review" in page.text and "butter-vs-shortening" in page.text.lower()
            print(f"show={show!r}: status={page.status_code} prospect_38_link_present={has_card} inline_review_present={has_review}")


if __name__ == "__main__":
    main()
