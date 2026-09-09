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

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import (  # noqa: E402
    build_id_to_row,
    extract_existing_pages,
    load_id_to_row_from_manifest,
    slugify as _slugify,
)
from validation import extract_content, normalize_for_storage  # noqa: E402


def slugify_for_page(title: str, template_type: str) -> str:
    """Wraps build_batch_requests.slugify to drop a trailing "recipe" from
    recipe_or_dish titles before slugifying -- every existing recipe slug
    (banana-nut-bread, parmesan-crusted-chicken, ...) omits that word even
    though the title itself always includes it (e.g. "Banana Nut Bread
    Recipe"); a naive slugify would produce "lomo-saltado-recipe" instead
    of matching that established convention. Only for deriving the final
    page slug from the model's generated title -- NOT used for custom_id
    derivation (build_id_to_row's plain slugify, from the raw queue
    keyword, is a separate, intentionally different mapping)."""
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

    with results_path.open() as f:
        results = [json.loads(l) for l in f]

    existing_slugs, _, _, _ = extract_existing_pages()
    taken_slugs = set(existing_slugs)

    manifest_path = Path(__file__).parent / "output" / f"{csv_path.stem}_manifest.json"
    if manifest_path.exists():
        id_to_row = load_id_to_row_from_manifest(csv_path, manifest_path)
    else:
        print(f"WARNING: no manifest at {manifest_path}, re-deriving custom_ids -- "
              "only safe if seed_templates.py hasn't changed since this batch was built.")
        id_to_row = build_id_to_row(csv_path, existing_slugs)

    # Snapshot of slugs that existed BEFORE this run -- distinct from
    # taken_slugs below, which gets mutated as this run assigns slugs to
    # its own new entries. Needed to tell apart the two collision cases:
    # "this exact page is already live" (skip, don't reinsert) vs. "two
    # different pages in this run happen to slugify the same" (a real new
    # duplicate-topic collision, not a re-run).
    originally_existing_slugs = set(existing_slugs)

    new_entries = []
    skipped = []
    for r in results:
        custom_id = r["custom_id"]
        if custom_id in skip_ids:
            skipped.append(custom_id)
            continue
        row = id_to_row.get(custom_id)
        if row is None:
            raise ValueError(f"[{custom_id}] no matching CSV row found -- can't determine template_type")
        template_type = row["template_type"]
        batch_number = int(row.get("batch_number") or 1)

        content = normalize_for_storage(template_type, extract_content(r["result"]["message"]))
        title = content.pop("title")
        candidate_slug = slugify_for_page(title, template_type)

        # Guards against a real regression: re-running this script against
        # a results file that's already been (fully or partially)
        # integrated used to silently insert the same page again under a
        # "-2"-suffixed slug (the collision-resolution loop below treats
        # ANY taken slug as "a different page happens to collide," which
        # is wrong for this specific case). Checking against the slug set
        # as it existed before this run started -- not the mutated
        # taken_slugs below -- catches "this exact page is already live"
        # directly, with no dependence on any particular CSV having a
        # status column (pilot_batch_50.csv, e.g., never had one).
        if candidate_slug in originally_existing_slugs:
            print(f"SKIPPING [{custom_id}]: slug {candidate_slug!r} already exists in "
                  "seed_templates.py -- already integrated in a prior run, not inserting again.")
            skipped.append(custom_id)
            continue

        slug = candidate_slug
        base = slug
        n = 2
        if slug in taken_slugs:
            print(f"WARNING [{custom_id}]: slug {slug!r} collides with another NEW page in this "
                  "same run (or a pre-existing page under a different title) -- this may be the "
                  "same real-world topic generated twice (see the corn-starch / "
                  "Flourless-Chocolate-Cake collisions found in the pilot). Assigning a suffixed "
                  "slug rather than silently merging, but review this pair before trusting both.")
        while slug in taken_slugs:
            slug = f"{base}-{n}"
            n += 1
        taken_slugs.add(slug)

        new_entries.append(format_page_entry(slug, template_type, title, batch_number, content))

    if not new_entries:
        print(f"Nothing to insert -- all {len(results)} result(s) were already published or skipped. "
              f"{SEED_TEMPLATES_PATH} left untouched.")
        if skipped:
            print(f"Skipped (as requested or already published): {skipped}")
        return

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

    # Dynamic, not hand-copied from the original pilot's header comment --
    # a hardcoded "pilot" description here would silently mislabel every
    # later real batch, which reuses this same script.
    today = date.today().isoformat()
    header = (
        f"\n    # --- Batch: {csv_path.name} ({today}), generated via\n"
        "    # content/scripts/build_batch_requests.py + Batch API, integrated via\n"
        "    # content/scripts/integrate_batch_results.py.\n"
    )
    new_text = (
        text[:closing_bracket]
        + header
        + "".join(new_entries)
        + text[closing_bracket:]
    )

    # Sanity check the insertion actually did what it should have, before
    # writing anything to disk: exactly len(new_entries) more top-level
    # pages should exist afterward, no more, no less. Catches both the
    # insertion-anchor bug (wrong location silently duplicating or
    # dropping content) and a double-integration slipping past the
    # status-column guard above for any reason.
    #
    # Counts only a top-level page's own "slug": key (immediately
    # followed by "template_type":, the same pattern
    # build_batch_requests.extract_existing_pages() already uses) rather
    # than every "slug": substring in the file -- a naive full-file count
    # is a real false positive, found by actually running this against
    # the 150-title batch: a recipe's own category_link/technique_link
    # LinkRefs and a category_roundup's recipe_cards entries both carry
    # their own nested "slug" keys, so 147 new pages legitimately added
    # 190 "slug": occurrences (28 from LinkRefs, 15 from two collections'
    # recipe_cards), not 147 -- the old count-everything check would have
    # refused a perfectly good insertion.
    top_level_pattern = re.compile(r'"slug":\s*"[^"]+",\s*\n\s*"template_type":')
    before_count = len(top_level_pattern.findall(text))
    after_count = len(top_level_pattern.findall(new_text))
    if after_count - before_count != len(new_entries):
        raise ValueError(
            f"Sanity check failed: expected exactly {len(new_entries)} new pages, but "
            f"top-level page count went from {before_count} to {after_count} "
            f"(delta {after_count - before_count}). Not writing -- investigate before re-running."
        )

    SEED_TEMPLATES_PATH.write_text(new_text)

    print(f"Inserted {len(new_entries)} new pages into {SEED_TEMPLATES_PATH} "
          f"({before_count} -> {after_count} total pages)")
    if skipped:
        print(f"Skipped (as requested or already published): {skipped}")


if __name__ == "__main__":
    main()
