"""Temporary diagnostic: checks the real, live production data for
baking-soda-substitute -- is it actually published, and where does it
fall in the /food/substitutes index's pagination (12 per page, newest
id first). /pages is public, no auth needed. Not part of the permanent
toolset -- delete once the mystery here is resolved.
"""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["PROD_BACKEND_BASE_URL"].rstrip("/")

    r = requests.get(f"{base}/pages/baking-soda-substitute", timeout=30)
    print(f"GET /pages/baking-soda-substitute -> {r.status_code}")
    if r.status_code == 200:
        page = r.json()
        print(f"  title={page.get('title')!r}")
        print(f"  image_url={page.get('image_url')!r}")

    offset = 0
    page_num = 1
    while True:
        r = requests.get(
            f"{base}/pages",
            params={"template_type": "substitute", "paged": "true", "limit": 12, "offset": offset},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        slugs = [item["slug"] for item in data["items"]]
        print(f"Page {page_num} (offset={offset}): {slugs}")
        if "baking-soda-substitute" in slugs:
            print(f"  ^ FOUND on page {page_num}, position {slugs.index('baking-soda-substitute') + 1}")
        if not data["has_more"]:
            break
        offset = data["next_offset"]
        page_num += 1


if __name__ == "__main__":
    main()
