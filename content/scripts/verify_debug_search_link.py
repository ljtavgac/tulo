"""One-off: confirms the new "debug search" link actually renders on the
outreach portal's article-review card for a real
status=article_pending_review row (the ultra-processed-foods article,
prospect #384), rather than trusting the deploy blind.

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/verify_debug_search_link.py
"""

from __future__ import annotations

import os
import re

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue",
        params={"show": "article_pending_review"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    html = r.text

    if "debug-page-image" not in html:
        print("*** NOT FOUND: no debug-page-image link anywhere on the page. ***")
        return

    m = re.search(r'<a href="(/admin/debug-page-image\?token=[^"]*&slug=how-to-reduce-ultra-processed[^"]*)"', html)
    if m:
        print(f"*** CONFIRMED: debug search link present for the ultra-processed article: {m.group(1)!r} ***")
    else:
        print("debug-page-image links exist on the page, but not matched to the ultra-processed article's slug specifically -- other matches:")
        for m2 in re.finditer(r'<a href="(/admin/debug-page-image\?[^"]*)"', html):
            print(f"  {m2.group(1)}")


if __name__ == "__main__":
    main()
