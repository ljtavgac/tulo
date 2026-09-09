"""Shared validation logic for a single generated page's content dict,
used by both validate_batch_results.py (bulk report) and fix_pass.py
(pass/fail gate for a retry loop). Pulled out to one place after finding
that checking "is field present and non-empty" is not enough: a real batch
result had `steps` (schema type array) rendered as a plain string containing
`<parameter name="item">...` -- a non-empty string that a truthiness check
alone would wave through, but resync_content() breaks on downstream since
it isn't the type the field is supposed to be.
"""

from __future__ import annotations

import json

from prompt_templates import SCHEMA_BY_TYPE

JSON_TYPE_TO_PYTHON = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}

# Legitimately null/empty per field design (nullable LinkRefs, or a note
# field that only applies to some pages) -- NOT the same as "optional in
# TypeScript", since some of these (step_notes) are still required non-empty
# by seed_templates.py's _REQUIRED_CONTENT_FIELDS depth check.
NULLABLE_OK_FIELDS = {"variety_notes", "link_terms", "technique_link", "category_link"}


def check_schema_types(value, schema: dict, path: str, issues: list) -> None:
    expected = schema.get("type")
    if expected is None:
        return
    allowed_types = [expected] if isinstance(expected, str) else expected
    allowed_python_types = tuple(JSON_TYPE_TO_PYTHON[t] for t in allowed_types)
    if not isinstance(value, allowed_python_types):
        issues.append(f"{path}: expected type {allowed_types}, got {type(value).__name__} ({value!r:.60})")
        return
    if isinstance(value, dict) and "properties" in schema:
        for key, sub_schema in schema["properties"].items():
            if key in value:
                check_schema_types(value[key], sub_schema, f"{path}.{key}", issues)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            check_schema_types(item, schema["items"], f"{path}[{i}]", issues)


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


def validate_content(
    custom_id: str,
    template_type: str,
    content: dict,
    collection_slugs: set,
    technique_slugs: set,
) -> list[str]:
    """Full validation for one page's content: schema-required-key presence,
    type conformance (recursive), non-emptiness for depth-check-required
    fields, double-dash ban, and category_link/technique_link slug
    existence. Returns a list of issue strings; empty means clean."""
    issues: list[str] = []
    schema = SCHEMA_BY_TYPE[template_type]

    for field in schema["required"]:
        if field not in content:
            issues.append(f"[{custom_id}] missing required key: {field}")
        elif field not in NULLABLE_OK_FIELDS and content[field] in (None, "", [], {}):
            issues.append(f"[{custom_id}] empty required field: {field}")

    type_issues: list = []
    check_schema_types(content, schema, custom_id, type_issues)
    issues.extend(type_issues)

    dash_hits: list = []
    find_double_dashes(content, custom_id, dash_hits)
    for location, snippet in dash_hits:
        issues.append(f"[{custom_id}] double-dash found at {location}: {snippet!r}")

    if template_type == "recipe_or_dish":
        cat_link = content.get("category_link")
        if cat_link and cat_link.get("slug") not in collection_slugs:
            issues.append(f"[{custom_id}] category_link points to nonexistent slug: {cat_link}")
        tech_link = content.get("technique_link")
        if tech_link and tech_link.get("slug") not in technique_slugs:
            issues.append(f"[{custom_id}] technique_link points to nonexistent slug: {tech_link}")
        has_nutrition = content.get("nutrition_note") or any(
            ing.get("nutrition_per_unit") for ing in content.get("ingredients", []) if isinstance(ing, dict)
        )
        if not has_nutrition:
            issues.append(f"[{custom_id}] no nutrition (note or per_unit)")

    if template_type == "category_roundup":
        for card in content.get("recipe_cards", []):
            if isinstance(card, dict) and not card.get("image_alt"):
                issues.append(f"[{custom_id}] recipe_card {card.get('title')!r} missing image_alt")

    return issues
