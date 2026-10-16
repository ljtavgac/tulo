"""One-off, read-only: verifies the live https://tulo.io/ HTML no longer
has the removed intro paragraph, while title, meta description,
canonical, and both WebSite + Organization JSON-LD blocks are intact.

Usage: python3 content/scripts/_verify_paragraph_removed.py
"""

import json
import re
import urllib.request

URL = "https://tulo.io/"

EXPECTED_TITLE = "Tulo — Recipes, Ingredient Guides &amp; Kitchen Tools"
EXPECTED_DESCRIPTION = (
    "Recipes that scale to your serving size, plus ingredient guides, "
    "how-to techniques, substitutes, and free kitchen tools."
)
REMOVED_PARAGRAPH_SNIPPET = "Tulo is a cooking reference built around the recipe you already have in mind"


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (paragraph-removal-verify)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    title_match = re.search(r"<title>(.*?)</title>", html)
    found_title = title_match.group(1) if title_match else None
    print(f"<title>: {found_title!r}")
    print(f"Title matches expected: {found_title == EXPECTED_TITLE}")

    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\'][^>]*/?>', html)
    found_desc = desc_match.group(1) if desc_match else None
    print(f"\nmeta description: {found_desc!r}")
    print(f"Description matches expected: {found_desc == EXPECTED_DESCRIPTION}")

    canonical_match = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*>', html)
    print(f"\ncanonical <link> tag: {canonical_match.group(0) if canonical_match else 'NOT FOUND'}")

    print(f"\nRemoved paragraph still present (should be False): {REMOVED_PARAGRAPH_SNIPPET in html}")

    blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    types_found = []
    for b in blocks:
        try:
            types_found.append(json.loads(b).get("@type"))
        except json.JSONDecodeError:
            types_found.append("PARSE_ERROR")
    print(f"\nld+json block count: {len(blocks)}")
    print(f"@type values found: {types_found}")
    print(f"Organization present: {'Organization' in types_found}")
    print(f"WebSite present: {'WebSite' in types_found}")


if __name__ == "__main__":
    main()
