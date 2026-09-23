"""One-off diagnostic: confirm whether the new
`Disallow: /food/tools/recipe-generator?ingredients=` rule (committed to
main in af3b215) has actually reached production, since a push to main
only triggers Vercel's own auto-deploy -- it doesn't confirm the build
finished. Fetches the live robots.txt directly.

Usage:
    FRONTEND_BASE_URL=https://tulo.io \
    python3 content/scripts/check_robots_txt.py
"""

from __future__ import annotations

import os

import requests

FRONTEND_BASE_URL = os.environ["FRONTEND_BASE_URL"].rstrip("/")


def main() -> None:
    url = f"{FRONTEND_BASE_URL}/robots.txt"
    r = requests.get(url, timeout=20)
    print(f"GET {url} -> HTTP {r.status_code}\n")
    print(r.text)
    print()
    if "food/tools/recipe-generator?ingredients=" in r.text:
        print("*** New disallow rule IS live in production. ***")
    else:
        print("*** New disallow rule is NOT yet live -- deploy likely still pending or failed. ***")


if __name__ == "__main__":
    main()
