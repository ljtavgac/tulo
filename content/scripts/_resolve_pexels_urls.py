"""Temporary: resolves Pexels photo-page URLs (pexels.com/photo/...) to
their direct CDN image URL (images.pexels.com/...) by reading the page's
og:image meta tag -- the format the backend's override-image endpoint
requires."""

from __future__ import annotations

import re
import sys

import requests

PAGE_URLS = [
    "https://www.pexels.com/photo/two-clear-glass-jars-743984/",
    "https://www.pexels.com/photo/a-person-scooping-powder-from-a-jar-6944061/",
]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def main() -> None:
    for url in PAGE_URLS:
        r = requests.get(url, timeout=30, headers=HEADERS)
        print(f"\n{url} -> {r.status_code}")
        if r.status_code != 200:
            print(f"  body snippet: {r.text[:300]!r}")
            continue
        m = re.search(r'<meta property="og:image" content="([^"]+)"', r.text)
        if m:
            print(f"  og:image: {m.group(1)}")
        else:
            print("  og:image not found")


if __name__ == "__main__":
    main()
