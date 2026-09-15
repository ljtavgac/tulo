"""Prints, for one page's JSON (as returned by GET /pages/{slug}), each
ingredient's hub_slug and whether it has swappable substitutes -- reads
the JSON from stdin. Built for verify-prod-pages.yml's own use (avoids
embedding multi-line Python directly in that workflow's YAML, which
breaks its block-scalar indentation), but plain stdin-in/stdout-out so
it's usable for any /pages/{slug} response, from any environment.

Usage:
    curl ... /pages/some-slug | python3 content/scripts/print_swap_fields.py
"""

from __future__ import annotations

import json
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        print(f"  FETCH/PARSE FAILED: {e}")
        return

    ingredients = data.get("content", {}).get("ingredients", [])
    if not ingredients:
        print("  (no ingredients field -- not a recipe_or_dish page, or page not found)")
        return

    for ing in ingredients:
        hub = ing.get("hub_slug")
        subs = ing.get("available_substitutes")
        if hub and subs:
            tag = f"  <-- SWAPPABLE ({len(subs)} substitute(s), hub={hub})"
        elif hub:
            tag = f"  (hub={hub}, no swappable substitutes)"
        else:
            tag = ""
        print(f"  {ing['name']!r}{tag}")


if __name__ == "__main__":
    main()
