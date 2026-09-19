"""One-off: confirms the generic Unsplash credit is actually live on prod
for a sample of the 30 previously-uncredited pages, by fetching the real
rendered HTML (not the backend API)."""

import os
import re
import sys

import requests

FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "https://tulo.io")
SLUGS = sys.argv[1:] or ["bbq-rub", "yuzu-kosho", "cassoulet"]

for slug in SLUGS:
    for path in (f"/food/ingredients/{slug}", f"/food/recipes/{slug}", f"/food/collections/{slug}"):
        url = FRONTEND_BASE_URL.rstrip("/") + path
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            continue
        m = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", r.text, re.DOTALL)
        print(f"{slug} ({url}): {m.group(1).strip() if m else 'NO FIGCAPTION FOUND'}")
        break
    else:
        print(f"{slug}: no 200 response on any known path")
