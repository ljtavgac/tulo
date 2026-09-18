"""Throwaway diagnostic: compares the broken batch-12 page's backend API
response against a known-working comparison page's, to isolate what's
actually different (status field? missing content key? something else).
Deleted after use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    python3 content/scripts/_diag_compare_working_page.py
"""

from __future__ import annotations

import json
import os

import requests

BROKEN_SLUG = "butter-vs-shortening-vs-oil-for-greasing-pans-which-works-best"
WORKING_SLUG = "baking-powder-vs-baking-soda"  # a real, known-live comparison page


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")

    for slug in (BROKEN_SLUG, WORKING_SLUG):
        r = requests.get(f"{base}/pages/{slug}", timeout=15)
        print(f"\n=== {slug} ===")
        print("status code:", r.status_code)
        try:
            data = r.json()
        except Exception as e:
            print("not JSON:", e, r.text[:500])
            continue
        print("page.status:", data.get("status"))
        print("content top-level keys:", sorted(data.get("content", {}).keys()))
        # Print full content as pretty JSON to a labeled block for full inspection
        print("--- full content ---")
        print(json.dumps(data.get("content"), indent=2)[:6000])


if __name__ == "__main__":
    main()
