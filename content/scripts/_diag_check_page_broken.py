"""Throwaway diagnostic: checks the live prod frontend URL and the
backend's /pages/<slug> API response for the batch-12 HARO article, to
see exactly what "broken" means (404? 500? a frontend render crash? bad
JSON from the backend?). Deleted after use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    python3 content/scripts/_diag_check_page_broken.py
"""

from __future__ import annotations

import os

import requests

SLUG = "butter-vs-shortening-vs-oil-for-greasing-pans-which-works-best"
PROD_URL = f"https://tulo.io/food/comparisons/{SLUG}"


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")

    print(f"--- GET {PROD_URL} ---")
    try:
        r = requests.get(PROD_URL, timeout=15)
        print("status:", r.status_code)
        print("first 2000 chars of body:")
        print(r.text[:2000])
    except requests.RequestException as e:
        print("request failed:", e)

    print(f"\n--- GET {base}/pages/{SLUG} (backend API, prod's own data source) ---")
    try:
        r2 = requests.get(f"{base}/pages/{SLUG}", timeout=15)
        print("status:", r2.status_code)
        print(r2.text[:3000])
    except requests.RequestException as e:
        print("request failed:", e)


if __name__ == "__main__":
    main()
