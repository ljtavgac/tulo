"""One-off, read-only: fetches the live https://tulo.io/ HTML and checks
for Organization and WebSite JSON-LD <script type="application/ld+json">
blocks, printing each one found in full.

Usage: python3 content/scripts/_check_homepage_jsonld.py
"""

import json
import re
import urllib.request

URL = "https://tulo.io/"


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (jsonld-check)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    print(f"Found {len(blocks)} ld+json <script> block(s) on {URL}\n")
    for i, raw in enumerate(blocks, 1):
        print(f"--- block {i} (raw) ---")
        print(raw.strip())
        try:
            parsed = json.loads(raw)
            print(f"--- block {i} parsed @type: {parsed.get('@type')!r} ---")
        except json.JSONDecodeError as e:
            print(f"--- block {i} failed to parse: {e} ---")
        print()

    has_org = any('"@type":"Organization"' in b.replace(" ", "") or '"@type": "Organization"' in b for b in blocks)
    has_website = any('"@type":"WebSite"' in b.replace(" ", "") or '"@type": "WebSite"' in b for b in blocks)
    print(f"Organization JSON-LD present: {has_org}")
    print(f"WebSite JSON-LD present: {has_website}")


if __name__ == "__main__":
    main()
