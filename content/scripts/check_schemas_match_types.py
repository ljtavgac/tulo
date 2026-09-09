"""Guards against the exact bug that caused a real production crash
(how-to-make-garlic-confit and how-to-saute-spinach both 404'd/failed to
render because HOWTO_TECHNIQUE_SCHEMA never declared `related_technique_slugs`
at all -- not empty, entirely absent -- and the frontend assumes it's always
an array): parses frontend/lib/types.ts directly for each content
interface's required (non-optional, no trailing `?`) fields, and checks
every one is present in the matching SCHEMA_BY_TYPE dict's `properties`
AND `required` list.

Deliberately does NOT hand-maintain a second copy of "what's required" --
that duplication is exactly what let the two lists drift apart the first
time. Run this before ever submitting a real batch, and any time
prompt_templates.py's schemas change.

Usage:
    python3 content/scripts/check_schemas_match_types.py
Exits non-zero if any gap is found.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from prompt_templates import SCHEMA_BY_TYPE  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
TYPES_TS_PATH = REPO_ROOT / "frontend" / "lib" / "types.ts"

INTERFACE_TO_TEMPLATE_TYPE = {
    "RecipeContent": "recipe_or_dish",
    "IngredientHubContent": "ingredient_hub",
    "HowToContent": "howto_technique",
    "DefinitionContent": "definition",
    "ComparisonContent": "comparison",
    "SubstituteContent": "substitute",
    "CategoryRoundupContent": "category_roundup",
}


def extract_required_fields(interface_name: str, text: str) -> list[str]:
    match = re.search(rf"export interface {interface_name} \{{(.*?)\n\}}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Couldn't find interface {interface_name} in {TYPES_TS_PATH}")
    body = match.group(1)
    required = []
    for line in body.splitlines():
        line = line.strip()
        field_match = re.match(r"(\w+)(\??):\s", line)
        if field_match and not field_match.group(2):
            required.append(field_match.group(1))
    return required


def main() -> None:
    text = TYPES_TS_PATH.read_text()
    problems = []

    for interface_name, template_type in INTERFACE_TO_TEMPLATE_TYPE.items():
        required_fields = extract_required_fields(interface_name, text)
        schema = SCHEMA_BY_TYPE[template_type]
        props = set(schema["properties"].keys())
        required_set = set(schema["required"])

        for field in required_fields:
            if field == "title":
                continue  # every schema declares title separately, not part of *Content
            if field not in props:
                problems.append(f"{template_type}: {interface_name}.{field} is required but missing from schema properties entirely")
            elif field not in required_set:
                problems.append(f"{template_type}: {interface_name}.{field} is required but not in schema['required']")

    if problems:
        print(f"FOUND {len(problems)} SCHEMA GAP(S):")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)
    print("All schemas cover every required field from their matching types.ts interface.")


if __name__ == "__main__":
    main()
