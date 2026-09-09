"""One-off repair: adds TS-required cross-linking fields that
prompt_templates.py's schemas omitted entirely (found via a live crash on
how-to-make-garlic-confit -- frontend expects related_technique_slugs to
always be an array, and it was missing from the content dict altogether,
not just empty). Every field this adds is one the site's own automatic
cross-linking (see BATCH_CONTENT_PIPELINE_PLAN.md's "what's already
automatic" section) either computes live at serve time or leaves for
future human curation -- [] / null is the genuinely correct value here,
not a placeholder, matching every hand-authored page's own convention
(e.g. banana-nut-bread's "technique_link": None, "related_recipe_slugs": []).

Only touches pages inside the "Batch API pilot" block, identified by slug,
so this can't accidentally reformat or affect any hand-authored page.
"""

import re
from pathlib import Path

SEED_TEMPLATES_PATH = Path(__file__).resolve().parents[2] / "backend" / "app" / "seed_templates.py"

# field -> literal Python source to insert if missing
DEFAULTS_BY_TYPE = {
    "recipe_or_dish": {"related_recipe_slugs": "[]"},
    "ingredient_hub": {"substitute_page_slug": "None", "recipe_slugs": "[]", "related_ingredient_slugs": "[]"},
    "howto_technique": {"recipe_slugs": "[]", "related_technique_slugs": "[]"},
    "definition": {"substitute_page_slug": "None", "related_recipe_slugs": "[]"},
    "comparison": {"item_a_link": "None", "item_b_link": "None"},
    "substitute": {"hub_page_slug": "None", "recipe_slugs": "[]"},
    "category_roundup": {"related_collection_slugs": "[]"},
}


def main() -> None:
    text = SEED_TEMPLATES_PATH.read_text()
    pilot_start = text.index("Batch API pilot")
    head, pilot_block = text[:pilot_start], text[pilot_start:]

    # Split the pilot block into individual page entries so each one can be
    # patched independently -- entries are separated by "    {\n        \"slug\"".
    entry_pattern = re.compile(r'(?=    \{\n        "slug")')
    parts = entry_pattern.split(pilot_block)
    header, entries = parts[0], parts[1:]

    patched_count = 0
    new_entries = []
    for entry in entries:
        template_type_match = re.search(r'"template_type": "([^"]+)"', entry)
        template_type = template_type_match.group(1)
        defaults = DEFAULTS_BY_TYPE[template_type]

        # The content dict's closing brace is the last "        },\n    },\n"
        # in the entry (content dict closes one level in from the page
        # entry's own closing brace). Insert new keys just before it.
        content_close = entry.rindex("        },\n    },\n")
        insertion = "".join(
            f'            "{field}": {value},\n'
            for field, value in defaults.items()
            if f'"{field}":' not in entry
        )
        if insertion:
            entry = entry[:content_close] + insertion + entry[content_close:]
            patched_count += 1
        new_entries.append(entry)

    new_pilot_block = header + "".join(new_entries)
    SEED_TEMPLATES_PATH.write_text(head + new_pilot_block)
    print(f"Patched {patched_count} page(s) with missing required link fields.")


if __name__ == "__main__":
    main()
