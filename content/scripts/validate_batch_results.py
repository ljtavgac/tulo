"""Validates a downloaded batch results file: schema-required-field
presence, real recursive type-checking against the schema (not just
presence/non-emptiness -- see validation.py's docstring for why that
distinction matters), the site's depth-check bar, double-dashes, title
convention per type, and category_link/technique_link slug existence.
Read-only, no network calls, no repo writes.

Usage:
    python3 content/scripts/validate_batch_results.py <csv> <results.jsonl>

The CSV is needed to map each result's custom_id back to its row's
template_type -- output_config's response has no tool name to infer that
from the way the pilot's original tool-choice-based results did.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import (  # noqa: E402
    build_id_to_row,
    extract_existing_pages,
    load_id_to_row_from_manifest,
)
from prompt_templates import MAX_TOKENS_BY_TYPE  # noqa: E402
from validation import extract_content, validate_content  # noqa: E402

# A result that used most of its max_tokens budget is one length-variance
# retry away from a real truncation (stop_reason: max_tokens, invalid
# cut-off JSON) -- exactly what happened to recipe_or_dish before its
# budget was bumped 4096 -> 6144 -> 8192. Flag it here, before that
# variance actually bites on a future run of the same template type.
TOKEN_HEADROOM_WARN_THRESHOLD = 0.85

TITLE_PATTERN_BY_TYPE = {
    "howto_technique": re.compile(r"^How to ", re.IGNORECASE),
    "definition": re.compile(r"^What Is ", re.IGNORECASE),
    "comparison": re.compile(r" vs\.? ", re.IGNORECASE),
    "substitute": re.compile(r"^Best Substitutes for ", re.IGNORECASE),
    "category_roundup": re.compile(r"Recipes$", re.IGNORECASE),
}


def main() -> None:
    csv_path = Path(sys.argv[1])
    results_path = Path(sys.argv[2])
    with results_path.open() as f:
        results = [json.loads(l) for l in f]

    existing_slugs, collections, techniques = extract_existing_pages()
    collection_slugs = {c["slug"] for c in collections}
    technique_slugs = {t["slug"] for t in techniques}

    manifest_path = Path(__file__).parent / "output" / f"{csv_path.stem}_manifest.json"
    if manifest_path.exists():
        id_to_row = load_id_to_row_from_manifest(csv_path, manifest_path)
    else:
        print(f"WARNING: no manifest at {manifest_path}, re-deriving custom_ids -- "
              "only safe if seed_templates.py hasn't changed since this batch was built.")
        id_to_row = build_id_to_row(csv_path, existing_slugs)

    total_input_tokens = 0
    total_output_tokens = 0
    issues: list[str] = []
    clean_ids: list[str] = []
    bad_ids: set[str] = set()
    high_headroom: list[tuple[str, int, int]] = []  # (custom_id, output_tokens, budget)

    for r in results:
        custom_id = r["custom_id"]
        if r["result"]["type"] != "succeeded":
            issues.append(f"[{custom_id}] request-level error: {r['result']}")
            bad_ids.add(custom_id)
            continue

        row = id_to_row.get(custom_id)
        if row is None:
            issues.append(f"[{custom_id}] no matching CSV row found -- can't determine template_type")
            bad_ids.add(custom_id)
            continue
        template_type = row["template_type"]

        message = r["result"]["message"]
        usage = message.get("usage", {})
        total_input_tokens += usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_output_tokens += output_tokens

        budget = MAX_TOKENS_BY_TYPE.get(template_type)
        if budget and output_tokens / budget >= TOKEN_HEADROOM_WARN_THRESHOLD:
            high_headroom.append((custom_id, output_tokens, budget))

        try:
            content = extract_content(message)
        except (ValueError, json.JSONDecodeError) as e:
            issues.append(f"[{custom_id}] couldn't extract content: {e}")
            bad_ids.add(custom_id)
            continue

        row_issues = validate_content(custom_id, template_type, content, collection_slugs, technique_slugs)

        title = content.get("title", "") if isinstance(content.get("title"), str) else ""
        pattern = TITLE_PATTERN_BY_TYPE.get(template_type)
        if pattern and not pattern.search(title):
            row_issues.append(f"[{custom_id}] title {title!r} doesn't match expected {template_type} convention")

        if row_issues:
            bad_ids.add(custom_id)
            issues.extend(row_issues)
        else:
            clean_ids.append(custom_id)

    INPUT_COST = 1.0
    OUTPUT_COST = 5.0
    actual_cost = (total_input_tokens / 1_000_000 * INPUT_COST) + (total_output_tokens / 1_000_000 * OUTPUT_COST)

    print(f"Total results: {len(results)} | clean: {len(clean_ids)} | with issues: {len(bad_ids)}")
    print(f"Actual usage: {total_input_tokens} input tokens, {total_output_tokens} output tokens")
    print(f"Actual cost (batch pricing): ${actual_cost:.4f}")
    print()
    print(f"Issues found: {len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    if not issues:
        print("  (none -- all results pass schema + type + depth-check + convention checks)")
    print()
    print(f"custom_ids needing a fix-pass: {sorted(bad_ids)}")
    print()
    if high_headroom:
        print(f"WARNING: {len(high_headroom)} result(s) used >={TOKEN_HEADROOM_WARN_THRESHOLD:.0%} "
              "of their max_tokens budget -- one attempt-to-attempt length variance away from a real "
              "truncation. Consider raising that template type's MAX_TOKENS_BY_TYPE entry before the next batch:")
        for custom_id, output_tokens, budget in high_headroom:
            print(f"  - [{custom_id}] {output_tokens}/{budget} tokens ({output_tokens / budget:.0%})")
    else:
        print(f"No result used >={TOKEN_HEADROOM_WARN_THRESHOLD:.0%} of its max_tokens budget.")


if __name__ == "__main__":
    main()
