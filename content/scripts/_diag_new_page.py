"""Throwaway diagnostic: checks the new HARO-generated comparison page from
both the staging backend (raw JSON) and the staging frontend (rendered
HTML) to find out why the frontend URL reportedly doesn't load. Delete
after use.
"""
import os
import sys

import requests

SLUG = "butter-vs-shortening-vs-oil-for-greasing-pans-which-works-best"

backend_base = os.environ["BACKEND_BASE_URL"].rstrip("/")
frontend_base = os.environ.get("FRONTEND_BASE_URL", "https://tulo-git-staging-tulo1.vercel.app").rstrip("/")

print(f"=== Backend: GET {backend_base}/pages/{SLUG} ===")
r = requests.get(f"{backend_base}/pages/{SLUG}", timeout=30)
print(f"status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"template_type: {data.get('template_type')}")
    print(f"title: {data.get('title')}")
    print(f"status field: {data.get('status')}")
    content = data.get("content", {})
    print(f"content keys: {list(content.keys())}")
    print(f"image_url: {content.get('image_url')!r}")
else:
    print(r.text[:1000])

print()
frontend_url = f"{frontend_base}/food/comparisons/{SLUG}"
print(f"=== Frontend: GET {frontend_url} ===")
r2 = requests.get(frontend_url, timeout=30, allow_redirects=True)
print(f"status: {r2.status_code}")
print(f"final url: {r2.url}")
print(r2.text[:500])

print()
existing_url = f"{frontend_base}/food/comparisons/cappuccino-vs-latte"
print(f"=== Frontend (control, existing page): GET {existing_url} ===")
r3 = requests.get(existing_url, timeout=30, allow_redirects=True)
print(f"status: {r3.status_code}")
print(f"final url: {r3.url}")
print(r3.text[:500])
