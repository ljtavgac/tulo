"""One-off: counts <url> entries in a live sitemap.xml, and optionally
checks for specific <loc> substrings (CHECK_URLS, comma-separated)."""

import os
import re

import requests

SITE_URL = os.environ.get("SITE_URL", "https://tulo.io")
CHECK_URLS = [u.strip() for u in os.environ.get("CHECK_URLS", "").split(",") if u.strip()]

r = requests.get(f"{SITE_URL.rstrip('/')}/sitemap.xml", timeout=30)
r.raise_for_status()
count = len(re.findall(r"<url>", r.text))
print(f"{SITE_URL}/sitemap.xml: {count} <url> entries")

for url in CHECK_URLS:
    found = f"<loc>{url}</loc>" in r.text
    print(f"  {'FOUND' if found else 'MISSING'}: {url}")
