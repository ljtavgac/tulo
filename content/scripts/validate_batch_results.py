"""Validates a downloaded batch results file against the same depth/schema
bar seed_templates.py enforces, plus a few pipeline-specific checks (title
convention per type, category_link/technique_link slug existence, no
double-dashes). Read-only, no network calls, no repo writes -- a Phase 2
precursor to decide whether the fix-pass is needed and how big it is.

Usage:
    python3 content/scripts/validate_batch_results.py <results.jsonl>
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import extract_existing_pages  # noqa: E402
from prompt_templates import SCHEMA_BY_TYPE, TOOL_NAME_BY_TYPE  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

DEPTH_FIELDS_BY_TYPE = {
    "recipe_or_dish": ["tips_and_variations", "storage_and_reheating", "reader_tips", "faqs", "step_notes", "image_alt"],
    "ingredient_hub": ["buying_tips", "pairing_suggestions", "faqs", "image_alt"],
    "howto_technique": ["intro", "common_mistakes", "equipment", "faqs", "image_alt"],
    "definition": ["faqs", "image_alt"],
    "comparison": ["faqs", "image_alt"],
    "substitute": ["faqs", "image_alt"],
    "category_roundup": ["faqs", "sub_categories"],
}

TITLE_PATTERN_BY_TYPE = {
    "howto_technique": re.compile(r"^How to ", re.IGNORECASE),
    "definition": re.compile(r"^What Is ", re.IGNORECASE),
    "comparison": re.compile(r" vs\.? ", re.IGNORECASE),
    "substitute": re.compile(r"^Best Substitutes for ", re.IGNORECASE),
    "category_roundup": re.compile(r"Recipes$", re.IGNORECASE),
}


def find_double_dashes(value, location: str, hits: list) -> None:
    if isinstance(value, str):
        if "--" in value:
            hits.append((location, value[:80]))
    elif isinstance(value, dict):
        for k, v in value.items():
            find_double_dashes(v, f"{location}.{k}", hits)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            find_double_dashes(v, f"{location}[{i}]", hits)


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
    template_type_by_custom_id = {}

    # We don't have the row->template_type mapping in the results file itself
    # (custom_id only), so infer it from which tool was called.
    for r in results:
        custom_id = r["custom_id"]
        if r["result"]["type"] != "succeeded":
            issues.append(f"[{custom_id}] request-level error: {r['result']}")
            continue

        message = r["result"]["message"]
        usage = message.get("usage", {})
        total_input_tokens += usage.get("input_tokens", 0)
        total_output_tokens += usage.get("output_tokens", 0)

        tool_uses = [c for c in message["content"] if c["type"] == "tool_use"]
        if len(tool_uses) != 1:
            issues.append(f"[{custom_id}] expected exactly 1 tool_use block, got {len(tool_uses)}")
            continue
        tool_use = tool_uses[0]
        tool_name = tool_use["name"]
        content = tool_use["input"]

        template_type = next((t for t, n in TOOL_NAME_BY_TYPE.items() if n == tool_name), None)
        if template_type is None:
            issues.append(f"[{custom_id}] unrecognized tool name {tool_name!r}")
            continue
        template_type_by_custom_id[custom_id] = template_type

        schema = SCHEMA_BY_TYPE[template_type]
        # technique_link/category_link are nullable LinkRefs -- null is the
        # correct value whenever no genuine match exists, not a gap. Only
        # check the key is present at all, not that it's non-null.
        nullable_ok_fields = {"step_notes", "variety_notes", "link_terms", "technique_link", "category_link"}
        for field in schema["required"]:
            if field not in content:
                issues.append(f"[{custom_id}] missing required key: {field}")
            elif field not in nullable_ok_fields and content[field] in (None, "", [], {}):
                issues.append(f"[{custom_id}] empty required field: {field}")

        for field in DEPTH_FIELDS_BY_TYPE[template_type]:
            if field == "image_alt":
                continue  # already covered by schema-required check above
            if not content.get(field):
                issues.append(f"[{custom_id}] fails depth check (would fail _check_content_depth): {field}")

        dash_hits: list = []
        find_double_dashes(content, custom_id, dash_hits)
        for location, snippet in dash_hits:
            issues.append(f"[{custom_id}] double-dash found at {location}: {snippet!r}")

        title = content.get("title", "")
        pattern = TITLE_PATTERN_BY_TYPE.get(template_type)
        if pattern and not pattern.search(title):
            issues.append(f"[{custom_id}] title {title!r} doesn't match expected {template_type} convention")

        if template_type == "recipe_or_dish":
            cat_link = content.get("category_link")
            if cat_link and cat_link.get("slug") not in collection_slugs:
                issues.append(f"[{custom_id}] category_link points to nonexistent slug: {cat_link}")
            tech_link = content.get("technique_link")
            if tech_link and tech_link.get("slug") not in technique_slugs:
                issues.append(f"[{custom_id}] technique_link points to nonexistent slug: {tech_link}")
            has_nutrition = content.get("nutrition_note") or any(
                ing.get("nutrition_per_unit") for ing in content.get("ingredients", [])
            )
            if not has_nutrition:
                issues.append(f"[{custom_id}] no nutrition (note or per_unit)")

        if template_type == "category_roundup":
            for card in content.get("recipe_cards", []):
                if not card.get("image_alt"):
                    issues.append(f"[{custom_id}] recipe_card {card.get('title')!r} missing image_alt")

    INPUT_COST = 1.0
    OUTPUT_COST = 5.0
    actual_cost = (total_input_tokens / 1_000_000 * INPUT_COST) + (total_output_tokens / 1_000_000 * OUTPUT_COST)

    print(f"Total results: {len(results)}")
    print(f"Actual usage: {total_input_tokens} input tokens, {total_output_tokens} output tokens")
    print(f"Actual cost (batch pricing): ${actual_cost:.4f}")
    print()
    print(f"Issues found: {len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    if not issues:
        print("  (none -- all 50 results pass schema + depth-check + convention checks)")


if __name__ == "__main__":
    main()
