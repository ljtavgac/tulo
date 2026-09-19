"""One-off test: can the CDN asset ID embedded in an images.unsplash.com URL
(the "photo-<timestamp>-<hash>" segment) be used directly against Unsplash's
GET /photos/:id API to recover real attribution -- or is that a different,
unrelated identifier from the public short photo ID (e.g. "eOvv766AhLw")
used in unsplash.com/photos/<id> URLs and the API's own "id" field?

Tests against a handful of real, currently-live CDN URLs from this site's
own manual_override pages (known to have no attribution stored)."""

import os
import re
import sys

import requests

UNSPLASH_ACCESS_KEY = os.environ["UNSPLASH_ACCESS_KEY"]

TEST_URLS = [
    "https://images.unsplash.com/photo-1592180387432-d735c59eee1a?crop=entropy",  # yuzu-kosho
    "https://images.unsplash.com/photo-1611354574034-9655b5b72d59?crop=entropy",  # bbq-rub (original)
    "https://images.unsplash.com/photo-1604925496719-ff4e81f35282?crop=entropy",  # melongene
]

for url in TEST_URLS:
    m = re.search(r"/photo-([\w-]+)", url)
    asset_id = m.group(1)
    print(f"URL: {url}")
    print(f"  extracted asset id: {asset_id!r}")
    r = requests.get(
        f"https://api.unsplash.com/photos/{asset_id}",
        headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
        timeout=10,
    )
    print(f"  GET /photos/{asset_id} -> {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"    photographer: {data.get('user', {}).get('name')}")
        print(f"    profile: {data.get('user', {}).get('links', {}).get('html')}")
    else:
        print(f"    body: {r.text[:300]}")
    print()
