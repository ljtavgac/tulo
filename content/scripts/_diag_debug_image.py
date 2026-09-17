"""Temporary: reproduces the reported 500 on /admin/debug-page-image for
a real slug, to see the actual status/response body (and, if the page is
a category_roundup, the shape of its recipe_cards) before touching any
code."""

from __future__ import annotations

import os

import requests

SLUG = "rutabaga-recipes"


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    token = os.environ["ADMIN_TASK_TOKEN"]

    r = requests.get(f"{base}/admin/debug-page-image", params={"token": token, "slug": SLUG}, timeout=30)
    print(f"GET /admin/debug-page-image?slug={SLUG} -> {r.status_code}")
    print(r.text[:3000])

    print("\n--- raw page content ---")
    r2 = requests.get(f"{base}/pages/{SLUG}", timeout=30)
    print(f"GET /pages/{SLUG} -> {r2.status_code}")
    if r2.ok:
        data = r2.json()
        print(f"template_type: {data.get('template_type')}")
        content = data.get("content", {})
        print(f"content keys: {list(content.keys())}")
        if "recipe_cards" in content:
            print(f"recipe_cards count: {len(content['recipe_cards'])}")
            if content["recipe_cards"]:
                print(f"first card keys: {list(content['recipe_cards'][0].keys())}")
                print(f"first card: {content['recipe_cards'][0]}")


if __name__ == "__main__":
    main()
