"""Temporary: fetches the real, live production page HTML directly (not
through the backend API) to see exactly what image URL is actually
embedded in the served HTML, plus response headers that might reveal a
CDN/edge cache sitting in front of the domain and ignoring Vercel's own
revalidation."""

from __future__ import annotations

import re

import requests

URL = "https://tulo.io/food/comparisons/baking-powder-vs-baking-soda"


def main() -> None:
    r = requests.get(URL, timeout=30, headers={"Cache-Control": "no-cache"})
    print(f"GET {URL} -> {r.status_code}")
    print("\n--- Response headers ---")
    for k, v in r.headers.items():
        print(f"{k}: {v}")

    html = r.text
    print(f"\n--- HTML length: {len(html)} ---")

    # Find every image URL referenced anywhere in the page (pexels/unsplash
    # CDN links, whether in <img src>, srcset, or Next.js's serialized
    # props payload).
    urls = sorted(set(re.findall(r'https://images\.(?:pexels|unsplash)\.com/[^"\'\\ ]+', html)))
    print(f"\n--- image URLs found in HTML ({len(urls)}) ---")
    for u in urls:
        print(u)

    if not urls:
        # No stock-photo URL at all -- print a slice around any hero/image
        # marker so we can see what's actually rendering instead.
        idx = html.find("image_url")
        print("\nNo pexels/unsplash URL found. Snippet around 'image_url' (if any):")
        print(html[max(0, idx - 200): idx + 200] if idx != -1 else "(not found in HTML at all)")


if __name__ == "__main__":
    main()
