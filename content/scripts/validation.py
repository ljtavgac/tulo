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

from prompt_templates import ALWAYS_EMPTY_SLUGS_ARRAY, ALWAYS_NULL_SLUG, SCHEMA_BY_TYPE

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
# Derived from the schemas themselves (any field whose type accepts "null",
# plus the shared ALWAYS_EMPTY_SLUGS_ARRAY / ALWAYS_NULL_SLUG marker
# objects) rather than hand-maintained: a hand-typed version of this set
# drifted out of sync with prompt_templates.py's actual schemas twice
# (once missing the newly-added slug/LinkRef fields, once missing
# pan_size), both only caught by a validator false-positive after the
# fact. A field that's nullable in the schema is nullable-OK here
# automatically, with no second list to remember to update.
#
# The one thing that genuinely can't be derived this way: a field with no
# "null" in its type at all, that's still allowed to be an empty
# string/array by deliberate content design (an empty string is a valid
# value, not a missing one). Kept as a small, explicit residual set --
# if a new nullable LinkRef/slug field is added to a schema, it needs no
# update here; only a new *non-nullable-typed* optional-content field does.
_NON_STRUCTURAL_NULLABLE_FIELDS = {"variety_notes", "link_terms"}


def _is_nullable_schema(schema: dict) -> bool:
    if schema is ALWAYS_NULL_SLUG or schema is ALWAYS_EMPTY_SLUGS_ARRAY:
        return True
    node_type = schema.get("type")
    types = [node_type] if isinstance(node_type, str) else (node_type or [])
    return "null" in types


def _compute_nullable_ok_fields() -> set[str]:
    fields = set(_NON_STRUCTURAL_NULLABLE_FIELDS)
    for schema in SCHEMA_BY_TYPE.values():
        for name, sub_schema in schema.get("properties", {}).items():
            if _is_nullable_schema(sub_schema):
                fields.add(name)
    return fields


NULLABLE_OK_FIELDS = _compute_nullable_ok_fields()

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


def _force_auto_resolved_fields(template_type: str, content: dict) -> None:
    """Forces every "always empty/null, resolved automatically" field back
    to its empty state, in place -- regardless of what the model actually
    returned. Exists because of a real bug: hibachi-style-vegetables-and-
    noodles shipped with 7 ingredients' `hub_slug` set to invented slugs
    ("zucchini", "onion", "garlic", ...) that don't match any real
    ingredient hub page, even though the schema's own description says
    "Leave null; hub linking is resolved automatically after generation."
    A schema instruction is not an enforcement mechanism -- output_config
    guarantees the *type* is right (a string or null), never that the
    *value* is a real slug, and this is proof the model can and does
    ignore a "leave this empty" instruction even under strict-schema
    generation. Rather than trust compliance and hope validation catches
    every case, every field with this exact design contract gets forced
    here, at the one choke point every integration path already calls
    through for step_notes -- so a future non-compliant generation can
    reach storage with a wrong type, but never with a wrong slug value in
    one of these fields.

    hub_slug isn't one of the shared ALWAYS_EMPTY_SLUGS_ARRAY/
    ALWAYS_NULL_SLUG marker schemas (it's per-ingredient, not a top-level
    content field), so it's handled by name here rather than picked up by
    the schema walk below.

    Rebuilds the ingredients list with fresh dicts rather than mutating
    the existing ones in place -- `content` itself is already a copy (see
    normalize_for_storage below), but that's only a shallow copy, so the
    nested ingredient dicts and the list holding them are still the same
    objects the caller's original content dict points to. Mutating those
    in place would silently change data out from under any caller still
    holding a reference to the pre-normalization content (e.g. code that
    validates, then normalizes, then re-inspects the original for
    comparison or logging)."""
    if template_type == "recipe_or_dish" and "ingredients" in content:
        content["ingredients"] = [
            {**ingredient, "hub_slug": None} if isinstance(ingredient, dict) else ingredient
            for ingredient in content["ingredients"]
        ]

    schema = SCHEMA_BY_TYPE[template_type]
    for name, sub_schema in schema.get("properties", {}).items():
        if sub_schema is ALWAYS_EMPTY_SLUGS_ARRAY:
            content[name] = []
        elif sub_schema is ALWAYS_NULL_SLUG:
            content[name] = None


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
    _force_auto_resolved_fields(template_type, content)
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
    hub_slugs: set = frozenset(),
) -> list[str]:
    """Full validation for one page's content: schema-required-key presence,
    type conformance (recursive), non-emptiness for depth-check-required
    fields, double-dash ban, and category_link/technique_link/hub_slug
    existence. Returns a list of issue strings; empty means clean.

    Runs before normalize_for_storage() at every real call site, so this
    is what actually surfaces a hub_slug violation like the one on
    hibachi-style-vegetables-and-noodles for a human to see -- normalize_
    for_storage() will force it back to null regardless either way, but
    silently, which would hide that the model didn't follow the "leave
    null" instruction rather than surfacing it as a real signal worth
    noticing (e.g. to tighten the prompt)."""
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
        for ing in content.get("ingredients", []):
            if not isinstance(ing, dict):
                continue
            hub_slug = ing.get("hub_slug")
            if hub_slug and hub_slug not in hub_slugs:
                issues.append(
                    f"[{custom_id}] ingredient {ing.get('name')!r} has hub_slug "
                    f"{hub_slug!r}, which doesn't match any real ingredient hub page "
                    "(schema says leave this null -- the model didn't)"
                )

    if template_type == "category_roundup":
        for card in content.get("recipe_cards", []):
            if isinstance(card, dict) and not card.get("image_alt"):
                issues.append(f"[{custom_id}] recipe_card {card.get('title')!r} missing image_alt")

    return issues
