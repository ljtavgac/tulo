"""Throwaway verification helper: fetches real rendered HTML from a
locally-running Next.js instance (started against the real staging
backend by .github/workflows/_verify-recipe-jsonld.yml) and extracts each
page's actual JSON-LD script tag content. Delete after use.
"""
import json
import re
import sys
import urllib.request

slugs = sys.argv[1].split(",")
for slug in slugs:
    url = f"http://localhost:3000/food/recipes/{slug}"
    print("=" * 60)
    print(f"=== {slug} ({url}) ===")
    print("=" * 60)
    html = urllib.request.urlopen(url, timeout=30).read().decode()
    # Non-greedy match, scoped to this specific script type -- safe even
    # when the whole document is emitted as a single line.
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html)
    if not blocks:
        print("NO JSON-LD SCRIPT TAGS FOUND")
        continue
    for i, block in enumerate(blocks):
        data = json.loads(block)
        print(f"--- block {i + 1}/{len(blocks)} (@type={data.get('@type')}) ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print()
