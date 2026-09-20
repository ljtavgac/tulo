"""One-off: confirms the file-size difference between a bare Pexels photo
URL (no sizing query params) and the same photo with the sizing params
fetch_stock_images.py always appends -- to verify the root cause of two
pages' slow LCP before fixing it."""

import requests

URLS = [
    "https://images.pexels.com/photos/743984/pexels-photo-743984.jpeg",
    "https://images.pexels.com/photos/743984/pexels-photo-743984.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
    "https://images.pexels.com/photos/8477743/pexels-photo-8477743.jpeg",
    "https://images.pexels.com/photos/8477743/pexels-photo-8477743.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
]

for url in URLS:
    r = requests.head(url, timeout=20, allow_redirects=True)
    size = r.headers.get("content-length")
    size_kb = f"{int(size) / 1024:.0f} KB" if size else "unknown"
    print(f"{url}\n  status={r.status_code} content-length={size_kb}\n")
