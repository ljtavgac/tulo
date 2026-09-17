"""Temporary: verifies the debug-page-image fix is live on staging by
re-hitting the exact URL the user reported failing."""

from __future__ import annotations

import os

import requests

SLUG = "rutabaga-recipes"


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    token = os.environ["ADMIN_TASK_TOKEN"]

    r = requests.get(f"{base}/health", timeout=15)
    print(f"GET /health -> {r.status_code} {r.json() if r.status_code == 200 else ''}")

    r = requests.get(f"{base}/admin/debug-page-image", params={"token": token, "slug": SLUG}, timeout=30)
    print(f"GET /admin/debug-page-image?slug={SLUG} -> {r.status_code}")
    print(r.text[:500])


if __name__ == "__main__":
    main()
