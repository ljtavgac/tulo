"""One-off: fetches the real rendered HTML for a slug across every known
template route and reports the actual hero <img src> plus the
attribution figcaption -- for comparing what a live frontend (prod or
staging) is actually serving, not what the backend API or git says."""

import os
import re
import sys

import requests

FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "https://tulo.io")
SLUGS = sys.argv[1:] or ["bbq-rub"]

ROUTES = [
    "food/recipes",
    "food/ingredients",
    "food/how-to",
    "food/what-is",
    "food/comparisons",
    "food/substitutes",
    "food/collections",
]

IMG_SRC_RE = re.compile(r'<img[^>]*\bsrc="([^"]+)"', re.DOTALL)
FIGCAPTION_RE = re.compile(r"<figcaption[^>]*>(.*?)</figcaption>", re.DOTALL)

for slug in SLUGS:
    found = False
    for route in ROUTES:
        url = f"{FRONTEND_BASE_URL.rstrip('/')}/{route}/{slug}"
        try:
            r = requests.get(url, timeout=20)
        except requests.RequestException as e:
            print(f"{slug} @ {route}: request failed: {e}")
            continue
        if r.status_code != 200:
            continue
        found = True
        img_m = IMG_SRC_RE.search(r.text)
        cap_m = FIGCAPTION_RE.search(r.text)
        print(f"{slug} ({url}):")
        print(f"  img src: {img_m.group(1) if img_m else 'NONE FOUND'}")
        print(f"  figcaption: {cap_m.group(1).strip() if cap_m else 'NONE FOUND'}")
        break
    if not found:
        print(f"{slug}: no 200 response on any known route")
