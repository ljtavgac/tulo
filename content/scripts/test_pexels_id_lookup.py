"""One-off test: Pexels CDN URLs embed a real, public numeric photo ID in
the path itself (https://images.pexels.com/photos/<id>/pexels-photo-<id>.jpeg),
unlike Unsplash's opaque CDN hash (confirmed unusable -- see
test_unsplash_id_lookup.py). Tests whether that ID can be used directly
against Pexels' GET /v1/photos/:id to recover real attribution for a photo
that was never captured with any -- without ever touching the image itself."""

import os
import re

import requests

PEXELS_ACCESS_KEY = os.environ["PEXELS_ACCESS_KEY"]

TEST_URLS = [
    "https://images.pexels.com/photos/5059700/pexels-photo-5059700.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",  # smoked-haddock-chowder
]

for url in TEST_URLS:
    m = re.search(r"/photos/(\d+)/", url)
    photo_id = m.group(1)
    print(f"URL: {url}")
    print(f"  extracted id: {photo_id}")
    r = requests.get(
        f"https://api.pexels.com/v1/photos/{photo_id}",
        headers={"Authorization": PEXELS_ACCESS_KEY},
        timeout=10,
    )
    print(f"  GET /v1/photos/{photo_id} -> {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"    photographer: {data.get('photographer')}")
        print(f"    photographer_url: {data.get('photographer_url')}")
        print(f"    src.large matches original? {data.get('src', {}).get('large') == url.split('?')[0] + '?auto=compress&cs=tinysrgb&h=650&w=940'}")
        print(f"    src: {data.get('src')}")
    else:
        print(f"    body: {r.text[:300]}")
    print()
