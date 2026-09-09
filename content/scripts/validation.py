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
import math
import re

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
#
# The ALWAYS_EMPTY_SLUGS_ARRAY / ALWAYS_NULL_SLUG fields (see
# prompt_templates.py) belong here too -- their whole design is "always []
# or null, resolved automatically after generation or curated by hand
# later" -- treating one as a validation failure would be flagging the
# schema working exactly as intended.
NULLABLE_OK_FIELDS = {
    "variety_notes", "link_terms", "technique_link", "category_link",
    "related_recipe_slugs", "substitute_page_slug", "recipe_slugs",
    "related_ingredient_slugs", "related_technique_slugs", "item_a_link",
    "item_b_link", "hub_page_slug", "related_collection_slugs", "pan_size",
}

# A pan's stated area must be within this fraction of what its label's
# literal dimensions compute to, or it's flagged -- the model is doing real
# arithmetic here (length x width, or pi x r^2) to drive actual bake-time
# scaling math client-side, so a wrong number isn't just cosmetic the way a
# slightly-off prose sentence would be.
PAN_AREA_TOLERANCE = 0.05


def _expected_pan_area_sq_in(label: str) -> float | None:
    """Parses a pan label's literal dimensions and returns the geometrically
    correct area, or None if the label doesn't contain a recognizable
    rectangular ("9x13") or round ("9-inch", "9 inch") measurement -- e.g. a
    label like "trifle bowl" or "tube pan" with no clean dimensions in it
    isn't checked, since there's nothing to compute against."""
    rect = re.search(r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)", label, re.IGNORECASE)
    if rect:
        return float(rect.group(1)) * float(rect.group(2))
    round_ = re.search(r"(\d+(?:\.\d+)?)[\s-]*inch(?:es)?\b", label, re.IGNORECASE)
    if round_ and "x" not in label.lower():
        radius = float(round_.group(1)) / 2
        return math.pi * radius * radius
    return None


def check_pan_size_math(pan_size: dict, path: str, issues: list) -> None:
    for key in ("current", *(f"alternatives[{i}]" for i in range(len(pan_size.get("alternatives", []))))):
        option = pan_size["current"] if key == "current" else pan_size["alternatives"][int(key.split("[")[1][:-1])]
        if not isinstance(option, dict) or "label" not in option or "area_sq_in" not in option:
            continue  # already reported by check_schema_types
        expected = _expected_pan_area_sq_in(option["label"])
        if expected is None:
            continue
        actual = option["area_sq_in"]
        if not isinstance(actual, (int, float)) or abs(actual - expected) > expected * PAN_AREA_TOLERANCE:
            issues.append(
                f"{path}.{key}: area_sq_in={actual} doesn't match what "
                f"{option['label']!r}'s stated dimensions compute to (~{expected:.1f})"
            )


def extract_content(message: dict) -> dict:
    """Pulls the generated content dict out of a Messages API response,
    supporting both response shapes this pipeline has used:
    - output_config (current): a `text` content block holding a JSON string.
    - forced tool-choice (the pilot's original mechanism, kept for backward
      compatibility with already-downloaded historical results files): a
      `tool_use` content block's `input`.
    Raises ValueError if neither shape is found, or output_config's response
    has more than one content block of a kind (a `thinking` block ahead of
    the `text` block is normal and skipped)."""
    tool_uses = [c for c in message["content"] if c["type"] == "tool_use"]
    if tool_uses:
        if len(tool_uses) != 1:
            raise ValueError(f"expected exactly 1 tool_use block, got {len(tool_uses)}")
        return tool_uses[0]["input"]

    text_blocks = [c for c in message["content"] if c["type"] == "text"]
    if len(text_blocks) != 1:
        raise ValueError(f"expected exactly 1 text block, got {len(text_blocks)}")
    return json.loads(text_blocks[0]["text"])


def normalize_for_storage(template_type: str, content: dict) -> dict:
    """Converts generation-time-only shapes back to what seed_templates.py
    actually stores, at the one shared choke point every integration path
    must call. This exists because of a real regression: a one-off
    integration script (generate_companion_recipes.py) reimplemented
    insertion without this step and shipped step_notes as a raw list,
    crashing resync_content() the same way the original garlic-confit bug
    did. Both integrate_batch_results.py and generate_companion_recipes.py
    call this now instead of each re-deriving it.

    step_notes travels through generation as a list of {step_index, note}
    objects (output_config's strict schema can't express an open-ended
    dict keyed by arbitrary step numbers -- see prompt_templates.py's
    RECIPE_OR_DISH_SCHEMA comment) but is stored as an int-keyed dict
    (frontend/lib/types.ts's Record<string, string>)."""
    content = dict(content)
    if template_type == "recipe_or_dish" and isinstance(content.get("step_notes"), list):
        content["step_notes"] = {entry["step_index"]: entry["note"] for entry in content["step_notes"]}
    return content


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
        pan_size = content.get("pan_size")
        if isinstance(pan_size, dict):
            check_pan_size_math(pan_size, custom_id, issues)

    if template_type == "category_roundup":
        for card in content.get("recipe_cards", []):
            if isinstance(card, dict) and not card.get("image_alt"):
                issues.append(f"[{custom_id}] recipe_card {card.get('title')!r} missing image_alt")

    return issues
