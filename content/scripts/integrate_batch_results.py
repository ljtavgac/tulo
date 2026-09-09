"""Phase 2 integration: takes a validated batch results file and inserts new
pages into backend/app/seed_templates.py's SEED_PAGES list, in the same
literal-Python-dict style already used there. Does not call any API and
does not touch the live database directly -- resync_content() (see
seed_templates.py) is what pushes this into production, on the backend's
next deploy/startup.

Usage:
    python3 content/scripts/integrate_batch_results.py \
        content/pilot_batch_50.csv content/scripts/output/pilot_batch_50_final.jsonl \
        --skip custom_id_1 custom_id_2

Only rows that pass validate_batch_results.py's checks should be passed in
here -- this script does not re-fix anything, it only serializes and inserts.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import extract_existing_pages, slugify as _slugify  # noqa: E402
from prompt_templates import TOOL_NAME_BY_TYPE  # noqa: E402


def slugify(title: str, template_type: str | None = None) -> str:
    """Wraps build_batch_requests.slugify to drop a trailing "recipe" from
    recipe_or_dish titles before slugifying -- every existing recipe slug
    (banana-nut-bread, parmesan-crusted-chicken, ...) omits that word even
    though the title itself always includes it (e.g. "Banana Nut Bread
    Recipe"); a naive slugify would produce "lomo-saltado-recipe" instead
    of matching that established convention. template_type defaults to None
    (no stripping) so this still exactly reproduces build_batch_requests.py's
    original custom_id derivation when re-deriving the id_to_title mapping
    below."""
    if template_type == "recipe_or_dish":
        title = re.sub(r"\s+recipe$", "", title, flags=re.IGNORECASE)
    return _slugify(title)

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_TEMPLATES_PATH = REPO_ROOT / "backend" / "app" / "seed_templates.py"

# Fields that belong in `content` for each template type come straight from
# the model's tool_use input (already schema-validated); `title` is pulled
# out separately since it's a top-level SEED_PAGES key, not a content field.


def py_literal(value, indent: int = 0) -> str:
    """Renders a JSON-parsed value (dict/list/str/int/float/bool/None) as
    valid Python source, double-quoted like the rest of seed_templates.py
    (json.dumps already produces valid Python string-literal syntax)."""
    pad = "    " * indent
    inner_pad = "    " * (indent + 1)
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = [inner_pad + json.dumps(k) + ": " + py_literal(v, indent + 1) + "," for k, v in value.items()]
        return "{\n" + "\n".join(lines) + "\n" + pad + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        lines = [inner_pad + py_literal(v, indent + 1) + "," for v in value]
        return "[\n" + "\n".join(lines) + "\n" + pad + "]"
    raise TypeError(f"Can't render {type(value)}")


def format_page_entry(slug: str, template_type: str, title: str, batch_number: int, content: dict) -> str:
    return (
        "    {\n"
        f'        "slug": {json.dumps(slug)},\n'
        f'        "template_type": {json.dumps(template_type)},\n'
        f'        "title": {json.dumps(title)},\n'
        f'        "batch_number": {batch_number},\n'
        f'        "content": {py_literal(content, indent=2)},\n'
        "    },\n"
    )


def main() -> None:
    csv_path = Path(sys.argv[1])
    results_path = Path(sys.argv[2])
    skip_ids = set()
    if "--skip" in sys.argv:
        skip_ids = set(sys.argv[sys.argv.index("--skip") + 1:])

    with csv_path.open() as f:
        rows_by_title = {row["title"]: row for row in csv.DictReader(f)}

    with results_path.open() as f:
        results = [json.loads(l) for l in f]

    existing_slugs, _, _ = extract_existing_pages()
    taken_slugs = set(existing_slugs)

    # Rebuild custom_id -> row title mapping the same way build_batch_requests
    # did, so we know each result's original queue row (for batch_number).
    id_to_title = {}
    taken_for_ids = set(existing_slugs)
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            base = slugify(row["title"])
            candidate = base
            n = 2
            while candidate in taken_for_ids:
                candidate = f"{base}-{n}"
                n += 1
            taken_for_ids.add(candidate)
            id_to_title[candidate] = row["title"]

    new_entries = []
    skipped = []
    for r in results:
        custom_id = r["custom_id"]
        if custom_id in skip_ids:
            skipped.append(custom_id)
            continue
        message = r["result"]["message"]
        tool_use = next(c for c in message["content"] if c["type"] == "tool_use")
        template_type = next(t for t, n in TOOL_NAME_BY_TYPE.items() if n == tool_use["name"])
        content = dict(tool_use["input"])
        title = content.pop("title")

        row = rows_by_title.get(id_to_title.get(custom_id, ""), {})
        batch_number = int(row.get("batch_number") or 1)

        slug = slugify(title, template_type)
        base = slug
        n = 2
        while slug in taken_slugs:
            slug = f"{base}-{n}"
            n += 1
        taken_slugs.add(slug)

        new_entries.append(format_page_entry(slug, template_type, title, batch_number, content))

    text = SEED_TEMPLATES_PATH.read_text()
    # Anchor on the exact text following SEED_PAGES's closing bracket, not a
    # bare "]\n" search -- that substring also matches nested list closings
    # inside page content (and even `list[tuple[str, str]] = []` type hints
    # in the functions defined right after SEED_PAGES), so a naive rindex
    # would insert in the wrong place.
    anchor = "\n]\n\n\ndef _find_double_dashes"
    if anchor not in text:
        raise ValueError("Expected SEED_PAGES closing-bracket anchor not found -- file structure changed")
    closing_bracket = text.index(anchor) + 1  # +1 to land right after the leading \n, at the "]"

    header = (
        "\n    # --- Batch API pilot (2026-09-09): 50-title cross-section, generated\n"
        "    # via content/scripts/build_batch_requests.py + Batch API, integrated via\n"
        "    # content/scripts/integrate_batch_results.py. See\n"
        "    # content/scripts/PILOT_BATCH_STATUS.md for the full pilot record.\n"
    )
    new_text = (
        text[:closing_bracket]
        + header
        + "".join(new_entries)
        + text[closing_bracket:]
    )
    SEED_TEMPLATES_PATH.write_text(new_text)

    print(f"Inserted {len(new_entries)} new pages into {SEED_TEMPLATES_PATH}")
    if skipped:
        print(f"Skipped (as requested): {skipped}")


if __name__ == "__main__":
    main()
