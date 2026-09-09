"""Validates a downloaded batch results file: schema-required-field
presence, real recursive type-checking against the schema (not just
presence/non-emptiness -- see validation.py's docstring for why that
distinction matters), the site's depth-check bar, double-dashes, title
convention per type, and category_link/technique_link slug existence.
Read-only, no network calls, no repo writes.

Usage:
    python3 content/scripts/validate_batch_results.py <results.jsonl>
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import extract_existing_pages  # noqa: E402
from prompt_templates import TOOL_NAME_BY_TYPE  # noqa: E402
from validation import validate_content  # noqa: E402

TITLE_PATTERN_BY_TYPE = {
    "howto_technique": re.compile(r"^How to ", re.IGNORECASE),
    "definition": re.compile(r"^What Is ", re.IGNORECASE),
    "comparison": re.compile(r" vs\.? ", re.IGNORECASE),
    "substitute": re.compile(r"^Best Substitutes for ", re.IGNORECASE),
    "category_roundup": re.compile(r"Recipes$", re.IGNORECASE),
}


def main() -> None:
    results_path = Path(sys.argv[1])
    with results_path.open() as f:
        results = [json.loads(l) for l in f]

    _, collections, techniques = extract_existing_pages()
    collection_slugs = {c["slug"] for c in collections}
    technique_slugs = {t["slug"] for t in techniques}

    total_input_tokens = 0
    total_output_tokens = 0
    issues: list[str] = []
    clean_ids: list[str] = []
    bad_ids: set[str] = set()

    for r in results:
        custom_id = r["custom_id"]
        if r["result"]["type"] != "succeeded":
            issues.append(f"[{custom_id}] request-level error: {r['result']}")
            bad_ids.add(custom_id)
            continue

        message = r["result"]["message"]
        usage = message.get("usage", {})
        total_input_tokens += usage.get("input_tokens", 0)
        total_output_tokens += usage.get("output_tokens", 0)

        tool_uses = [c for c in message["content"] if c["type"] == "tool_use"]
        if len(tool_uses) != 1:
            issues.append(f"[{custom_id}] expected exactly 1 tool_use block, got {len(tool_uses)}")
            bad_ids.add(custom_id)
            continue
        tool_use = tool_uses[0]
        content = tool_use["input"]
        template_type = next((t for t, n in TOOL_NAME_BY_TYPE.items() if n == tool_use["name"]), None)
        if template_type is None:
            issues.append(f"[{custom_id}] unrecognized tool name {tool_use['name']!r}")
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


if __name__ == "__main__":
    main()
