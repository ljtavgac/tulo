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

# StockPhotoSlot always wraps the hero image + its caption in one
# <figure>...<img .../>...<figcaption>...</figcaption></figure> block --
# scoping to that specific figure avoids matching an unrelated <img> that
# happens to appear earlier in the page (the site logo in the header, for
# instance -- a bug in an earlier version of this script).
FIGURE_RE = re.compile(r"<figure[^>]*>.*?</figure>", re.DOTALL)
IMG_SRC_RE = re.compile(r'<img[^>]*\bsrc="([^"]+)"')
FIGCAPTION_RE = re.compile(r"<figcaption[^>]*>(.*?)</figcaption>", re.DOTALL)
IMG_URL_PARAM_RE = re.compile(r"[?&]url=([^&]+)")


def _real_src(raw_src: str) -> str:
    """Unwraps Next/Image's /_next/image?url=<encoded>&... proxy path to
    the actual source URL it's serving, when present."""
    m = IMG_URL_PARAM_RE.search(raw_src)
    if not m:
        return raw_src
    from urllib.parse import unquote

    return unquote(m.group(1))


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
        fig_m = FIGURE_RE.search(r.text)
        img_m = IMG_SRC_RE.search(fig_m.group(0)) if fig_m else None
        cap_m = FIGCAPTION_RE.search(fig_m.group(0)) if fig_m else None
        print(f"{slug} ({url}):")
        print(f"  hero img src: {_real_src(img_m.group(1)) if img_m else 'NONE FOUND (no <figure> block matched)'}")
        print(f"  figcaption: {cap_m.group(1).strip() if cap_m else 'NONE FOUND'}")
        break
    if not found:
        print(f"{slug}: no 200 response on any known route")
