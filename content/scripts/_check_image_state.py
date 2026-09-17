"""Temporary: directly checks GET /pages/<slug> (public endpoint, no
token) on both prod and staging for the two just-overridden pages, to
verify what image_url is actually being served right now -- ground
truth check after the user reported no visible change despite the
override endpoint reporting success twice."""

from __future__ import annotations

import os

import requests

SLUGS = ["baking-powder-vs-baking-soda", "baking-soda-substitute"]


def check(label: str, base: str) -> None:
    print(f"\n=== {label} ({base}) ===")
    for slug in SLUGS:
        r = requests.get(f"{base}/pages/{slug}", timeout=30)
        if r.status_code != 200:
            print(f"{slug}: HTTP {r.status_code}")
            continue
        data = r.json()
        content = data.get("content", {})
        print(f"{slug}: image_url={content.get('image_url')!r}")
        print(f"{slug}: image_attribution={content.get('image_attribution')!r}")


def main() -> None:
    prod = os.environ.get("PROD_BACKEND_BASE_URL")
    staging = os.environ.get("BACKEND_BASE_URL")
    if prod:
        check("PROD", prod.rstrip("/"))
    if staging:
        check("STAGING", staging.rstrip("/"))


if __name__ == "__main__":
    main()
