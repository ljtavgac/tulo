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


def main() -> None:
    for url in PAGE_URLS:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        print(f"\n{url} -> {r.status_code}")
        if r.status_code != 200:
            continue
        m = re.search(r'<meta property="og:image" content="([^"]+)"', r.text)
        if m:
            print(f"  og:image: {m.group(1)}")
        else:
            print("  og:image not found")


if __name__ == "__main__":
    main()
