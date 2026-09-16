"""One-off repair, mirroring patch_missing_link_fields.py's approach: adds
two new TS-required cross-linking fields (frontend/lib/types.ts) that every
existing definition/comparison page in SEED_PAGES predates and therefore
lacks entirely -- not just empty, absent from the dict -- which crashes
RelatedLinks (reads `slugs.length`) the moment either template renders.

hub_page_slug (definition): the ingredient_hub page for the term a
definition page defines, e.g. "What Is Lard?" -> the "lard" hub. Populated
with a real slug ONLY where the definition's own term (title with "What
Is "/trailing "?" stripped) exactly, case-insensitively matches a real hub
page's title -- the same conservative, exact-match-only discipline
_resolve_hub_slug uses in backend/app/main.py, chosen after this session's
own #2 near-miss heuristic produced ~60-70% false positives on manual
sampling. Confirmed via a one-off scan: 7 of 55 definition pages get a real
match this way (lard, yuzu, searing, creme-fraiche, mezcal, branzino,
double-cream); the other 48 get None, same as every hand-authored page's
own convention for a cross-link that doesn't exist yet.

related_recipe_slugs (comparison): no safe non-fuzzy derivation exists yet
(would need item_a_link/item_b_link populated first, which is itself 0/29
today -- a separate, already-reported content gap). Every comparison page
gets [] here, a real "not populated" value pending that content decision,
not a placeholder.
"""

import re
from pathlib import Path

SEED_TEMPLATES_PATH = Path(__file__).resolve().parents[2] / "backend" / "app" / "seed_templates.py"

# definition slug -> ingredient_hub slug, from the exact-title-match scan
# described above. Hand-verified, not derived at patch time, so a future
# hub rename/addition can't silently change what this script does.
DEFINITION_HUB_MATCHES = {
    "what-is-lard": "lard",
    "what-is-yuzu": "yuzu",
    "what-is-searing": "searing",
    "what-is-cr-me-fra-che": "creme-fraiche",
    "what-is-mezcal": "mezcal",
    "what-is-branzino": "branzino",
    "what-is-double-cream": "double-cream",
}


def main() -> None:
    text = SEED_TEMPLATES_PATH.read_text()

    entry_pattern = re.compile(r'(?=    \{\n        "slug")')
    parts = entry_pattern.split(text)
    header, entries = parts[0], parts[1:]

    patched_count = 0
    new_entries = []
    for entry in entries:
        slug_match = re.search(r'"slug": "([^"]+)"', entry)
        type_match = re.search(r'"template_type": "([^"]+)"', entry)
        slug, template_type = slug_match.group(1), type_match.group(1)

        if template_type == "definition" and '"hub_page_slug":' not in entry:
            hub_slug = DEFINITION_HUB_MATCHES.get(slug)
            value = f'"{hub_slug}"' if hub_slug else "None"
            insertion = f'            "hub_page_slug": {value},\n'
        elif template_type == "comparison" and '"related_recipe_slugs":' not in entry:
            insertion = '            "related_recipe_slugs": [],\n'
        else:
            insertion = ""

        if insertion:
            content_close = entry.rindex("        },\n    },\n")
            entry = entry[:content_close] + insertion + entry[content_close:]
            patched_count += 1
        new_entries.append(entry)

    SEED_TEMPLATES_PATH.write_text(header + "".join(new_entries))
    print(f"Patched {patched_count} page(s) with missing hub_page_slug/related_recipe_slugs.")


if __name__ == "__main__":
    main()
