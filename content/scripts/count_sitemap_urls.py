"""One-off: counts <url> entries in the live production sitemap.xml."""

import os
import re

import requests

SITE_URL = os.environ.get("SITE_URL", "https://tulo.io")

r = requests.get(f"{SITE_URL.rstrip('/')}/sitemap.xml", timeout=30)
r.raise_for_status()
count = len(re.findall(r"<url>", r.text))
print(f"{SITE_URL}/sitemap.xml: {count} <url> entries")
