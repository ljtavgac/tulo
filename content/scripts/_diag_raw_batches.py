"""Temporary: calls /admin/debug-pages-raw against production to see the
literal raw query batches for template_type=substitute at offset 0 and
offset 12, to find why the paged endpoint behaves differently on
production than an identical local reproduction."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["PROD_BACKEND_BASE_URL"].rstrip("/")
    token = os.environ["PROD_ADMIN_TASK_TOKEN"]

    r = requests.get(f"{base}/health", timeout=30)
    print(f"GET /health -> {r.status_code} {r.json() if r.status_code == 200 else ''}")

    for offset in (0, 12):
        r = requests.get(
            f"{base}/admin/debug-pages-raw",
            params={"token": token, "template_type": "substitute", "offset": offset, "limit": 12},
            timeout=30,
        )
        print(f"\noffset={offset}: {r.status_code}")
        if r.status_code == 200:
            for row in r.json():
                print(f"  id={row['id']} slug={row['slug']!r} unpublished={row['unpublished']}")


if __name__ == "__main__":
    main()
