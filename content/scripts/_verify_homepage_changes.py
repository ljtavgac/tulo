"""One-off, read-only: verifies the live https://tulo.io/ HTML carries
the new title, meta description, visible intro paragraph, and both
Organization + WebSite JSON-LD blocks.

Usage: python3 content/scripts/_verify_homepage_changes.py
"""

import json
import re
import urllib.request

URL = "https://tulo.io/"

EXPECTED_TITLE = "Tulo — Recipes, Ingredient Guides & Kitchen Tools"
EXPECTED_DESCRIPTION = (
    "Recipes that scale to your serving size, plus ingredient guides, "
    "how-to techniques, substitutes, and free kitchen tools."
)
EXPECTED_PARAGRAPH_SNIPPET = "Tulo is a cooking reference built around the recipe you already have in mind"


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (homepage-verify)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    title_match = re.search(r"<title>(.*?)</title>", html)
    print(f"<title>: {title_match.group(1) if title_match else 'NOT FOUND'!r}")
    print(f"Title matches expected: {title_match and title_match.group(1) == EXPECTED_TITLE}")

    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\'][^>]*/?>', html)
    found_desc = desc_match.group(1) if desc_match else None
    print(f"\nmeta description: {found_desc!r}")
    print(f"Description matches expected: {found_desc == EXPECTED_DESCRIPTION}")

    print(f"\nIntro paragraph present: {EXPECTED_PARAGRAPH_SNIPPET in html}")

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

    for b in blocks:
        try:
            parsed = json.loads(b)
            if parsed.get("@type") == "Organization":
                print(f"\nOrganization block: {json.dumps(parsed, indent=2)}")
        except json.JSONDecodeError:
            pass


if __name__ == "__main__":
    main()
