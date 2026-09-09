"""Per-template-type prompt construction for the Batch API content pipeline.

Each template type gets:
- A JSON Schema, enforced via `output_config.format` (real decoding-level
  structured output, not just tool-choice biasing). The pilot run first
  used forced tool-choice, which turned out NOT to be a strict guarantee:
  ~24% of pilot results had array/object fields rendered as plain strings
  containing "<parameter name=...>" tag fragments (a tool-calling format
  leaking into the output) instead of real JSON arrays -- confirmed
  reproducible even across retries with an added anti-corruption prompt
  instruction. Switching to output_config's json_schema format resolved
  this in direct testing (see content/scripts/PILOT_BATCH_STATUS.md for
  the full pilot writeup) since it constrains the actual token decoding,
  not just the model's inclination to fill out a tool call correctly.
  output_config requires additionalProperties: false on every object and
  only supports minItems of 0 or 1 (see to_strict_schema below) -- the
  SCHEMA_BY_TYPE dicts keep richer minItems values for documentation/
  tooling clarity, and get stripped down at request-build time.
- A real, already-published example (pulled directly from
  backend/app/seed_templates.py's SEED_PAGES) for tone/depth calibration.
- A shared style guide (see STYLE_GUIDE below) covering rules that apply
  across every template type, most importantly the double-dash ban -- see
  seed_templates.py's _check_no_double_dashes, which raises at import time
  for any "--" in any content string. A batch that reintroduces that pattern
  at scale would fail the depth-check import immediately.

Schema field names and required-vs-optional status are cross-checked against
frontend/lib/types.ts (the TypeScript contract the frontend actually renders)
and backend/app/seed_templates.py's _REQUIRED_CONTENT_FIELDS (the fields
_check_content_depth() enforces as non-empty on every live page). Getting
this mapping wrong is the single highest-leverage mistake to avoid here --
see the design doc's own note on this.
"""

from __future__ import annotations

import copy
import json

MODEL = "claude-sonnet-5"

# ---------------------------------------------------------------------------
# Shared style guide, included in every request's system prompt.
# ---------------------------------------------------------------------------

STYLE_GUIDE = """You are writing content for Tulo, a food and recipe website. Match the voice \
and depth of the example below exactly -- specific, practical, no filler, no \
generic "food blog" preamble about memories or feelings.

Hard rules, enforced by an automated check that will reject a whole batch if violated:
- NEVER use a double-dash ("--") anywhere, for any reason (not as an em dash, \
not as a parenthetical). It reads as an obvious AI-writing tell. If you want an \
aside, use a comma, a colon, or parentheses instead.
- Never write in first person or reference "I" cooking something, testing it, or \
having a memory of it. This site has no author persona.
- Every FAQ answer, tip, and note must be a real, specific, useful fact -- not a \
restatement of the question, and not generic advice that could apply to any dish.
- image_alt must be a real, specific description of what the photo would show, \
never the bare search term repeated as a caption.
- Numbers (temperatures, times, ratios, quantities) must be realistic and internally \
consistent (a "40-50 minute roast" step and a "cook_time_minutes" field that says \
15 would be a real content-depth bug, not just a style nit).
- Titles must follow the exact convention used by the template type's example below \
(e.g. ingredient hub pages are the bare ingredient name, not "X Recipe"; how-to \
pages are phrased as "How to ___"; definition pages ask "What Is ___?"). Do not \
default to appending "Recipe" to a title unless the page is actually a \
recipe_or_dish page.

Return your answer as a single, complete, valid JSON object matching the \
required schema. Do not write any prose before or after the JSON.

Every array field (steps, faqs, ingredients, tips_and_variations, etc.) must be \
a real, properly nested JSON array value, e.g. ["first item", "second item"] or \
[{"question": "...", "answer": "..."}, ...]. Never represent a list as a plain \
string, and never use any XML-like <parameter name="..."> tags anywhere in the \
output -- that syntax belongs to a different format and must not appear here."""


def _example_block(example: dict) -> str:
    return json.dumps(example, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Reusable JSON-Schema fragments
# ---------------------------------------------------------------------------

FAQ_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "answer": {"type": "string"},
    },
    "required": ["question", "answer"],
}

LINK_REF_SCHEMA = {
    "type": ["object", "null"],
    "properties": {
        "title": {"type": "string"},
        "slug": {"type": "string"},
    },
    "required": ["title", "slug"],
}

# Every one of these fields is required by frontend/lib/types.ts but is
# either computed live at serve time (see BATCH_CONTENT_PIPELINE_PLAN.md's
# "what's already automatic" section, e.g. an ingredient hub's recipe_slugs)
# or left for a future human-curation pass -- never something this pipeline
# should ask the model to author. Missing them from a schema entirely (as
# an earlier version of this file did) isn't the same as an empty value:
# a genuinely missing key crashed a real page (how-to-make-garlic-confit)
# because the frontend assumes related_technique_slugs is always an array,
# not sometimes absent. These two shared fragments make sure every schema
# declares -- and requires -- these fields with the one value they should
# ever take.
ALWAYS_EMPTY_SLUGS_ARRAY = {
    "type": "array",
    "items": {"type": "string"},
    "description": "Always return an empty array here -- this cross-linking is computed automatically after generation, or curated by hand later; never populate it yourself.",
}
ALWAYS_NULL_SLUG = {
    "type": "null",
    "description": "Always null -- resolved automatically after generation or left for human curation later, never generated by you.",
}

NUTRITION_PER_UNIT_SCHEMA = {
    "type": "object",
    "properties": {
        "calories": {"type": "number"},
        "protein_g": {"type": "number"},
        "carbs_g": {"type": "number"},
        "fat_g": {"type": "number"},
    },
    "required": ["calories", "protein_g", "carbs_g", "fat_g"],
}

RECIPE_INGREDIENT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "base_qty": {"type": "number"},
        "unit_us": {"type": "string"},
        "base_qty_metric": {"type": "number"},
        "unit_metric": {"type": "string"},
        "hub_slug": {
            "type": ["string", "null"],
            "description": "Leave null; hub linking is resolved automatically after generation.",
        },
        "nutrition_per_unit": NUTRITION_PER_UNIT_SCHEMA,
    },
    "required": ["name", "base_qty", "unit_us", "base_qty_metric", "unit_metric", "hub_slug"],
}

PAN_SIZE_OPTION_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "description": "e.g. '9x5-inch loaf pan', '9-inch round cake pan'."},
        "area_sq_in": {
            "type": "number",
            "description": "Baking-surface area in square inches: length x width for a rectangular pan, or pi x radius^2 for a round one. Must be arithmetically correct for the stated dimensions -- this drives real bake-time scaling math, not just a label.",
        },
    },
    "required": ["label", "area_sq_in"],
}

PAN_SIZE_SCHEMA = {
    "type": ["object", "null"],
    "description": (
        "Only for a recipe actually baked in a shaped pan or dish where a reader "
        "might reasonably substitute a different size (a loaf, cake, casserole, "
        "tart, gratin, etc.) -- never for stovetop, grilled, no-bake/chilled, or "
        "mixed-drink recipes, and never when the dish's exact shape doesn't matter "
        "(e.g. a skillet sear). Leave null for every recipe that isn't baked in a "
        "specific shaped vessel; do not force this field to be non-null."
    ),
    "properties": {
        "current": {**PAN_SIZE_OPTION_SCHEMA, "description": "The pan size as written in the recipe's own instructions."},
        "alternatives": {
            "type": "array",
            "description": (
                "At least one genuinely common substitute pan of the SAME shape "
                "family as current (loaf-for-loaf, round-for-round, square/"
                "rectangular-for-square/rectangular) -- the area-ratio scaling this "
                "feeds only makes sense for a same-shape-of-bake swap. Most recipes "
                "baked in a standard pan size DO have at least one common swap "
                "(9x13 <-> 9x9 or 8x8 baking dish, 9x5 <-> 8x4 loaf pan, 9-inch <-> "
                "8-inch or 10-inch round cake/springform/tart pan) -- actually look "
                "for one before leaving this empty; an empty array here means the "
                "'Using a different pan?' selector won't render at all, which should "
                "be rare, not the default. Only leave empty for a genuinely unusual "
                "pan/dish shape with no common substitute (a bundt pan, a specific "
                "casserole dish shape, a trifle bowl). Never fabricate a size that "
                "isn't a real, commonly stocked pan just to fill this."
            ),
            "items": PAN_SIZE_OPTION_SCHEMA,
        },
    },
    "required": ["current", "alternatives"],
}

# ---------------------------------------------------------------------------
# Per-template-type schemas, examples, and extra per-row context builders.
# ---------------------------------------------------------------------------

RECIPE_OR_DISH_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Natural recipe title, e.g. 'Banana Nut Bread Recipe'."},
        "meta_description": {"type": "string"},
        "hero_image_query": {"type": "string", "description": "A short, literal stock-photo search phrase for this dish."},
        "image_alt": {"type": "string"},
        "why_it_works": {"type": "string"},
        "prep_time_minutes": {"type": "integer"},
        "cook_time_minutes": {"type": "integer"},
        "total_time_minutes": {"type": "integer"},
        "servings": {"type": "integer"},
        "ingredients": {"type": "array", "items": RECIPE_INGREDIENT_SCHEMA, "minItems": 3},
        "instructions": {"type": "array", "items": {"type": "string"}, "minItems": 4},
        "step_notes": {
            "type": "array",
            "description": "A short 'why this step matters' technique note for at least 2 of the most technique-relevant steps. Each entry names one instruction's 0-based index. seed_templates.py stores this as a step-index-keyed map (Record<string, string> in frontend/lib/types.ts) -- an open-ended dictionary keyed by arbitrary step numbers can't be expressed as a strict JSON schema (no fixed property names), so this array form is converted back to that map shape at integration time.",
            "items": {
                "type": "object",
                "properties": {
                    "step_index": {"type": "integer", "description": "0-based index into the instructions array this note explains."},
                    "note": {"type": "string"},
                },
                "required": ["step_index", "note"],
            },
        },
        "tips_and_variations": {"type": "array", "items": {"type": "string"}, "minItems": 3},
        "storage_and_reheating": {"type": "string"},
        "reader_tips": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 3},
        "faqs": {"type": "array", "items": FAQ_SCHEMA, "minItems": 3},
        "technique_link": {
            **LINK_REF_SCHEMA,
            "description": "Set only if the recipe genuinely relies on one of the existing how-to techniques listed in the prompt context; otherwise null.",
        },
        "category_link": {
            **LINK_REF_SCHEMA,
            "description": "Set to one of the existing collections listed in the prompt context if this dish clearly belongs to it; otherwise null. Never invent a new collection.",
        },
        "related_recipe_slugs": ALWAYS_EMPTY_SLUGS_ARRAY,
        "pan_size": PAN_SIZE_SCHEMA,
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt", "why_it_works",
        "prep_time_minutes", "cook_time_minutes", "total_time_minutes", "servings",
        "ingredients", "instructions", "step_notes", "tips_and_variations",
        "storage_and_reheating", "reader_tips", "faqs", "technique_link", "category_link",
        "related_recipe_slugs", "pan_size",
    ],
}

INGREDIENT_HUB_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "The bare ingredient name, e.g. 'Chives'."},
        "meta_description": {"type": "string"},
        "hero_image_query": {"type": "string"},
        "image_alt": {"type": "string"},
        "description": {"type": "string"},
        "substitutes": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "ratio": {"type": "string"},
                    "note": {"type": "string"},
                    "ratio_multiplier": {
                        "type": ["number", "null"],
                        "description": "A precise 'amount of substitute per 1 unit of original' multiplier, or null if the substitute can't be reduced to one.",
                    },
                },
                "required": ["name", "ratio", "note", "ratio_multiplier"],
            },
        },
        "storage": {"type": "string"},
        "uses": {"type": "string"},
        "nutrition_note": {"type": "string"},
        "buying_tips": {"type": "string"},
        "pairing_suggestions": {"type": "string"},
        "variety_notes": {
            "type": "string",
            "description": "Only include real content here if a genuine variety distinction exists (e.g. chives vs. garlic chives). Use an empty string if none applies.",
        },
        "faqs": {"type": "array", "items": FAQ_SCHEMA, "minItems": 3},
        "substitute_page_slug": ALWAYS_NULL_SLUG,
        "recipe_slugs": ALWAYS_EMPTY_SLUGS_ARRAY,
        "related_ingredient_slugs": ALWAYS_EMPTY_SLUGS_ARRAY,
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt", "description",
        "substitutes", "storage", "uses", "nutrition_note", "buying_tips",
        "pairing_suggestions", "variety_notes", "faqs",
        "substitute_page_slug", "recipe_slugs", "related_ingredient_slugs",
    ],
}

HOWTO_TECHNIQUE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Phrased as 'How to ___', e.g. 'How to Cook Spaghetti Squash'."},
        "meta_description": {"type": "string"},
        "hero_image_query": {"type": "string"},
        "image_alt": {"type": "string"},
        "intro": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}, "minItems": 4},
        "common_mistakes": {"type": "array", "items": {"type": "string"}, "minItems": 2},
        "equipment": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "faqs": {"type": "array", "items": FAQ_SCHEMA, "minItems": 3},
        "recipe_slugs": ALWAYS_EMPTY_SLUGS_ARRAY,
        "related_technique_slugs": ALWAYS_EMPTY_SLUGS_ARRAY,
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt", "intro",
        "steps", "common_mistakes", "equipment", "faqs",
        "recipe_slugs", "related_technique_slugs",
    ],
}

DEFINITION_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Phrased as 'What Is ___?', matching the example."},
        "meta_description": {"type": "string"},
        "hero_image_query": {"type": "string"},
        "image_alt": {"type": "string"},
        "direct_answer": {"type": "string"},
        "expanded_explanation": {"type": "string"},
        "usage_origin": {"type": "string"},
        "substitute_note": {"type": "string"},
        "link_terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Only for technique/verb-based terms whose word forms (gerund, past tense) differ from the title's bare noun. Empty array if not applicable.",
        },
        "faqs": {"type": "array", "items": FAQ_SCHEMA, "minItems": 3},
        "substitute_page_slug": ALWAYS_NULL_SLUG,
        "related_recipe_slugs": ALWAYS_EMPTY_SLUGS_ARRAY,
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt", "direct_answer",
        "expanded_explanation", "usage_origin", "substitute_note", "link_terms", "faqs",
        "substitute_page_slug", "related_recipe_slugs",
    ],
}

COMPARISON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Phrased as 'X vs. Y: What's the Difference?', matching the example."},
        "meta_description": {"type": "string"},
        "hero_image_query": {"type": "string"},
        "image_alt": {"type": "string"},
        "item_a_name": {"type": "string"},
        "item_b_name": {"type": "string"},
        "comparison_table": {
            "type": "array",
            "minItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "attribute": {"type": "string"},
                    "item_a": {"type": "string"},
                    "item_b": {"type": "string"},
                },
                "required": ["attribute", "item_a", "item_b"],
            },
        },
        "verdict": {"type": "string"},
        "sections": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["heading", "body"],
            },
        },
        "faqs": {"type": "array", "items": FAQ_SCHEMA, "minItems": 3},
        "item_a_link": ALWAYS_NULL_SLUG,
        "item_b_link": ALWAYS_NULL_SLUG,
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt", "item_a_name",
        "item_b_name", "comparison_table", "verdict", "sections", "faqs",
        "item_a_link", "item_b_link",
    ],
}

SUBSTITUTE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Phrased as 'Best Substitutes for ___', matching the example."},
        "meta_description": {"type": "string"},
        "hero_image_query": {"type": "string"},
        "image_alt": {"type": "string"},
        "ranked_substitutes": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "ratio": {"type": "string"},
                    "best_for": {"type": "string"},
                    "note": {"type": "string"},
                    "ratio_multiplier": {"type": ["number", "null"]},
                },
                "required": ["name", "ratio", "best_for", "note", "ratio_multiplier"],
            },
        },
        "baking_vs_cooking_note": {"type": "string"},
        "faqs": {"type": "array", "items": FAQ_SCHEMA, "minItems": 3},
        "hub_page_slug": ALWAYS_NULL_SLUG,
        "recipe_slugs": ALWAYS_EMPTY_SLUGS_ARRAY,
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt",
        "ranked_substitutes", "baking_vs_cooking_note", "faqs",
        "hub_page_slug", "recipe_slugs",
    ],
}

CATEGORY_ROUNDUP_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Phrased as 'X Recipes' (plural collection), matching the example."},
        "meta_description": {"type": "string"},
        "intro": {"type": "string"},
        "recipe_cards": {
            "type": "array",
            "minItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "slug": {
                        "type": ["string", "null"],
                        "description": "Null (this is a real dish that doesn't have its own Tulo page yet).",
                    },
                    "description": {"type": "string"},
                    "image_query": {"type": "string"},
                    "image_alt": {"type": "string"},
                },
                "required": ["title", "slug", "description", "image_query", "image_alt"],
            },
        },
        "sub_categories": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["label", "items"],
            },
        },
        "faqs": {"type": "array", "items": FAQ_SCHEMA, "minItems": 2},
        "related_collection_slugs": ALWAYS_EMPTY_SLUGS_ARRAY,
    },
    "required": ["title", "meta_description", "intro", "recipe_cards", "sub_categories", "faqs", "related_collection_slugs"],
}

# ---------------------------------------------------------------------------
# Real published examples, trimmed of comments, for calibration.
# Pulled directly from backend/app/seed_templates.py (banana-nut-bread,
# chives, how-to-cook-spaghetti-squash, what-is-tahini, cappuccino-vs-latte,
# baking-soda-substitute, eggplant-recipes).
# ---------------------------------------------------------------------------

EXAMPLES = {
    "recipe_or_dish": {
        "title": "Banana Nut Bread Recipe",
        "meta_description": "A moist banana nut bread recipe using extra-ripe bananas, ready in about an hour. Includes a live serving-size scaler and US/metric unit toggle.",
        "hero_image_query": "banana nut bread",
        "image_alt": "A moist banana nut bread recipe using extra-ripe bananas, ready in about an hour. Includes a live serving-size scaler and US/metric unit toggle.",
        "why_it_works": "Extra-ripe, well-spotted bananas add natural sweetness and moisture, so this loaf stays tender without drying out, and a quick one-bowl method means less cleanup.",
        "prep_time_minutes": 15,
        "cook_time_minutes": 60,
        "total_time_minutes": 75,
        "servings": 10,
        "ingredients": [
            {"name": "bananas, mashed", "base_qty": 3, "unit_us": "medium ripe", "base_qty_metric": 3, "unit_metric": "medium ripe", "hub_slug": None, "nutrition_per_unit": {"calories": 105, "protein_g": 1.3, "carbs_g": 27.0, "fat_g": 0.4}},
            {"name": "all-purpose flour", "base_qty": 1.5, "unit_us": "cups", "base_qty_metric": 190, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 455, "protein_g": 13.0, "carbs_g": 95.0, "fat_g": 1.2}},
            {"name": "walnuts, chopped", "base_qty": 1, "unit_us": "cup", "base_qty_metric": 120, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 765, "protein_g": 18.0, "carbs_g": 16.0, "fat_g": 76.0}},
        ],
        "instructions": [
            "Preheat the oven to 350°F (175°C). Grease a 9x5-inch loaf pan.",
            "In a large bowl, mash the ripe bananas with a fork until smooth.",
            "Add the flour and mix until just combined, don't overmix, or the bread will turn out dense.",
            "Fold in the chopped walnuts.",
            "Bake for 55-65 minutes, until a toothpick inserted into the center comes out clean.",
        ],
        "step_notes": [
            {"step_index": 2, "note": "Overmixing once the flour is added develops gluten, which is what makes quick breads turn dense and tough instead of tender."},
            {"step_index": 4, "note": "The toothpick test in the very center, not near the edge, is what actually confirms doneness; the edges bake through well before the center does."},
        ],
        "tips_and_variations": [
            "Very ripe, heavily spotted (almost black) bananas give noticeably more flavor than yellow ones, don't toss bananas just because they've browned.",
            "Swap up to half the flour for whole wheat flour for a heartier crumb.",
            "No walnuts on hand? Pecans work as a 1:1 swap.",
        ],
        "storage_and_reheating": "Store cooled bread tightly wrapped at room temperature for up to 4 days, or in the refrigerator for up to a week. To freeze, wrap tightly in plastic wrap, then foil, for up to 3 months.",
        "reader_tips": [
            "Room-temperature eggs and butter blend into the batter more evenly than cold ones, since this one-bowl method has no creaming step to work out lumps.",
            "If the top browns too fast before the center sets, tent it loosely with foil for the last 15 minutes.",
        ],
        "faqs": [
            {"question": "Can I freeze banana nut bread?", "answer": "Yes. Wrap the fully cooled loaf tightly in plastic wrap, then foil, and freeze for up to 3 months."},
            {"question": "Why is my banana bread dense or gummy?", "answer": "The most common cause is overmixing once the flour is added; stir only until the streaks of flour disappear."},
            {"question": "Can I use frozen bananas?", "answer": "Yes. Thaw them completely first and drain off the excess liquid before mashing."},
        ],
        "technique_link": None,
        "category_link": None,
        "related_recipe_slugs": [],
        "pan_size": {
            "current": {"label": "9x5-inch loaf pan", "area_sq_in": 45},
            "alternatives": [
                {"label": "8x4-inch loaf pan", "area_sq_in": 32},
                {"label": "9-inch round cake pan", "area_sq_in": 64},
            ],
        },
    },
    "ingredient_hub": {
        "title": "Chives",
        "meta_description": "What chives are, the best substitutes with ratios, how to store them so they don't wilt, and how to use them without losing their flavor.",
        "hero_image_query": "fresh chives",
        "image_alt": "What chives are, the best substitutes with ratios, how to store them so they don't wilt, and how to use them without losing their flavor.",
        "description": "Chives (Allium schoenoprasum) are the mildest member of the onion family, grown for their thin, hollow, grass-like green stems. They deliver a delicate onion flavor without the sharpness of scallions or raw onion.",
        "substitutes": [
            {"name": "Scallion greens (green onion tops)", "ratio": "1:1", "note": "Slightly stronger onion flavor, but the closest visual and flavor match.", "ratio_multiplier": 1.0},
            {"name": "Leek greens, finely minced", "ratio": "1:1", "note": "Milder and slightly sweeter; mince very finely since leek greens are more fibrous.", "ratio_multiplier": 1.0},
        ],
        "storage": "Fresh chives wilt quickly. Wrap loosely in a damp paper towel and store in a sealed container in the refrigerator crisper drawer for about a week.",
        "uses": "Snip with scissors directly onto finished dishes, baked potatoes, scrambled eggs, soups, and salads. Add at the very end since chives lose flavor if cooked long.",
        "nutrition_note": "Chives are low in calories and used in small quantities, but contain vitamin K, vitamin C, and modest vitamin A.",
        "buying_tips": "Look for bright green, firm stems with no yellowing or sliminess at the cut ends. Buy in small bunches since they wilt within a few days.",
        "pairing_suggestions": "Pairs naturally with sour cream, creme fraiche, and butter in potato and egg dishes, and with mild white fish or chicken.",
        "variety_notes": "Garlic chives (Chinese chives) are a different plant entirely, flat, wider leaves and a mild garlic flavor rather than onion.",
        "faqs": [
            {"question": "Are chives and green onions the same thing?", "answer": "No. Chives are a distinct, thinner herb never eaten beyond the green stem; green onions have both a white bulb and green top, both eaten."},
            {"question": "Can I substitute dried chives for fresh?", "answer": "Yes, but expect a real drop in flavor and color. Use about a third of the amount called for fresh."},
            {"question": "Do chives regrow after you cut them?", "answer": "Yes, if grown as a live plant. Snip stems about an inch above the soil and a healthy plant regrows within about two weeks."},
        ],
    },
    "howto_technique": {
        "title": "How to Cook Spaghetti Squash",
        "meta_description": "How to roast spaghetti squash so it separates into tender strands, plus the most common mistake that leaves it mushy or undercooked.",
        "hero_image_query": "roasted spaghetti squash",
        "image_alt": "How to roast spaghetti squash so it separates into tender strands, plus the most common mistake that leaves it mushy or undercooked.",
        "intro": "Spaghetti squash only takes on its signature noodle-like strands with the right roasting setup, cut wrong or roasted the wrong way up and it turns mushy or stays undercooked in the center.",
        "steps": [
            "Preheat the oven to 400°F (200°C).",
            "Slice the spaghetti squash in half lengthwise, from stem to base.",
            "Scoop out the seeds and stringy pulp from the center with a spoon.",
            "Drizzle the cut sides with olive oil and season with salt and pepper.",
            "Place both halves cut-side down on a parchment-lined baking sheet.",
            "Roast for 40-50 minutes, until the skin gives slightly when pressed and a fork slides in easily.",
        ],
        "common_mistakes": [
            "Roasting cut-side up: cut-side down traps steam and keeps the flesh moist.",
            "Undercooking: if a fork doesn't glide through easily, the strands come out short and won't separate cleanly.",
        ],
        "equipment": ["Sharp chef's knife", "Baking sheet", "Fork"],
        "faqs": [
            {"question": "Can I microwave spaghetti squash instead of roasting it?", "answer": "Yes, it's faster but the strands turn out softer and wetter."},
            {"question": "How do I know when spaghetti squash is done?", "answer": "A fork should slide into the flesh with almost no resistance, and the skin gives slightly when pressed."},
            {"question": "Why did my spaghetti squash come out watery?", "answer": "It naturally holds a lot of water. Salt the scraped strands and let them sit in a colander for 5-10 minutes before serving."},
        ],
    },
    "definition": {
        "title": "What Is Tahini? (And How to Use It)",
        "meta_description": "Tahini is a smooth paste made from ground sesame seeds. What it is, how it's used, and the best substitute if you're out.",
        "hero_image_query": "tahini paste jar",
        "image_alt": "Tahini is a smooth paste made from ground sesame seeds. What it is, how it's used, and the best substitute if you're out.",
        "direct_answer": "Tahini is a smooth paste made from toasted, ground sesame seeds, similar in consistency to thin peanut butter, with a nutty, slightly bitter flavor and no added sweetness.",
        "expanded_explanation": "It's a foundational ingredient in Middle Eastern and Mediterranean cooking, made by grinding hulled sesame seeds, sometimes lightly toasted first, into a smooth, pourable paste.",
        "usage_origin": "Tahini is the base for hummus and baba ganoush, gets whisked into dressings and sauces, and shows up in desserts like halva.",
        "substitute_note": "Sunflower seed butter is the closest nut-free substitute, though it lacks tahini's distinct roasted-sesame flavor.",
        "link_terms": [],
        "faqs": [
            {"question": "Is tahini the same as peanut butter?", "answer": "No. Tahini is made from sesame seeds and has a nuttier, slightly bitter flavor with no sweetness; peanut butter is sweeter and made from peanuts."},
            {"question": "Why does tahini separate in the jar?", "answer": "Like natural peanut butter, tahini's oil naturally separates and rises to the top during storage. Stir thoroughly before each use."},
            {"question": "Does tahini need to be refrigerated?", "answer": "An unopened jar can be stored in a cool pantry. Once opened, refrigerating extends freshness."},
        ],
    },
    "comparison": {
        "title": "Cappuccino vs. Latte: What's the Difference?",
        "meta_description": "Cappuccino vs. latte: the real difference is the milk-to-foam ratio. A side-by-side comparison to help you order, or make, the right one.",
        "hero_image_query": "cappuccino and latte side by side",
        "image_alt": "Cappuccino vs. latte: the real difference is the milk-to-foam ratio. A side-by-side comparison to help you order, or make, the right one.",
        "item_a_name": "Cappuccino",
        "item_b_name": "Latte",
        "comparison_table": [
            {"attribute": "Espresso", "item_a": "1-2 shots", "item_b": "1-2 shots"},
            {"attribute": "Steamed milk", "item_a": "Roughly equal part to the espresso", "item_b": "Much larger proportion, 2-3x the espresso"},
            {"attribute": "Milk foam", "item_a": "Thick, deep foam layer", "item_b": "Thin foam layer, just enough to cap the drink"},
            {"attribute": "Typical size", "item_a": "5-6 oz", "item_b": "8-12+ oz"},
        ],
        "verdict": "Choose a cappuccino for a stronger, more concentrated coffee-forward drink with a distinct foam texture. Choose a latte for a milkier, smoother, more mellow drink.",
        "sections": [
            {"heading": "Cappuccino", "body": "Built in roughly equal thirds of espresso, steamed milk, and milk foam, defined by that thick foam cap."},
            {"heading": "Latte", "body": "Mostly steamed milk with a shot or two of espresso and a thin layer of foam."},
        ],
        "faqs": [
            {"question": "Which has more caffeine, a cappuccino or a latte?", "answer": "Neither, caffeine comes entirely from the espresso shots, and both drinks typically use the same 1-2 shots."},
            {"question": "Can I make either one without an espresso machine?", "answer": "Yes, with a moka pot for the coffee base and a handheld frother for the milk."},
            {"question": "Which one should I order if I don't like a strong coffee taste?", "answer": "A latte, the higher milk-to-espresso ratio mellows the coffee flavor considerably."},
        ],
        "item_a_link": None,
        "item_b_link": None,
    },
    "substitute": {
        "title": "Best Substitutes for Baking Soda",
        "meta_description": "Out of baking soda? Here are four ranked substitutes with exact ratios, including which ones work best for baking vs. general cooking.",
        "hero_image_query": "baking soda box",
        "image_alt": "Out of baking soda? Here are four ranked substitutes with exact ratios, including which ones work best for baking vs. general cooking.",
        "ranked_substitutes": [
            {"name": "Baking powder", "ratio": "Use 3x the amount of baking soda called for", "best_for": "Both baking and cooking", "note": "Baking powder already contains an acid, so it doesn't need the recipe's own acidic ingredient to activate.", "ratio_multiplier": 3.0},
            {"name": "Self-rising flour", "ratio": "Replace the recipe's flour with self-rising flour and omit the baking soda and any added salt", "best_for": "Simple quick breads and biscuits", "note": "Self-rising flour already contains both leavening and salt.", "ratio_multiplier": None},
            {"name": "Potassium bicarbonate + a pinch of salt", "ratio": "1:1, plus a small pinch of salt", "best_for": "Sodium-reduced diets", "note": "Chemically similar leavening action to baking soda without the sodium.", "ratio_multiplier": 1.0},
        ],
        "baking_vs_cooking_note": "The substitutes above are for baking soda's leavening role in baked goods. If a savory recipe calls for a pinch of baking soda for browning, it's best to simply omit it.",
        "faqs": [
            {"question": "Can I use baking powder and baking soda interchangeably?", "answer": "Not 1:1. Use about 3x the amount of baking powder to replace a given amount of baking soda."},
            {"question": "What happens if I leave baking soda out of a recipe entirely?", "answer": "The baked good won't rise properly and will turn out flat and dense."},
            {"question": "Does baking soda go bad?", "answer": "It doesn't spoil, but loses leavening power over time. Test by dropping a pinch into vinegar."},
        ],
    },
    "category_roundup": {
        "title": "Eggplant Recipes",
        "meta_description": "Eggplant recipes organized by cooking method, roasted, fried, grilled, and curried, with a real curated pick instead of an auto-generated list.",
        "intro": "Eggplant's spongy texture takes on flavor differently depending on how it's cooked, roasted until creamy, breaded and fried, or simmered low and slow.",
        "recipe_cards": [
            {"title": "Baba Ganoush", "slug": None, "description": "Smoky, roasted eggplant dip blended with tahini, garlic, and lemon.", "image_query": "baba ganoush", "image_alt": "Smoky, roasted eggplant dip blended with tahini, garlic, and lemon."},
            {"title": "Eggplant Parmesan", "slug": None, "description": "Breaded, fried (or baked) eggplant layered with marinara and melted cheese.", "image_query": "eggplant parmesan", "image_alt": "Breaded, fried (or baked) eggplant layered with marinara and melted cheese."},
            {"title": "Roasted Eggplant with Garlic and Herbs", "slug": None, "description": "The simplest way to cook eggplant, olive oil, high heat, and just enough seasoning.", "image_query": "roasted eggplant", "image_alt": "The simplest way to cook eggplant, olive oil, high heat, and just enough seasoning."},
            {"title": "Eggplant Curry (Baingan Bharta)", "slug": None, "description": "Charred, mashed eggplant simmered with tomatoes, onion, and warm spices.", "image_query": "baingan bharta", "image_alt": "Charred, mashed eggplant simmered with tomatoes, onion, and warm spices."},
            {"title": "Grilled Eggplant Slices", "slug": None, "description": "Salted, grilled eggplant rounds with a quick balsamic glaze.", "image_query": "grilled eggplant", "image_alt": "Salted, grilled eggplant rounds with a quick balsamic glaze."},
        ],
        "sub_categories": [
            {"label": "Mediterranean", "items": ["Baba Ganoush", "Grilled Eggplant Slices"]},
            {"label": "Comfort Food", "items": ["Eggplant Parmesan"]},
        ],
        "faqs": [
            {"question": "How do I keep eggplant from tasting bitter?", "answer": "Modern eggplant varieties are bred to be much less bitter than older ones, so salting is mostly optional today."},
            {"question": "Do I need to peel eggplant before cooking?", "answer": "No, the skin is edible and holds the flesh together during cooking."},
        ],
    },
}

SCHEMA_BY_TYPE = {
    "recipe_or_dish": RECIPE_OR_DISH_SCHEMA,
    "ingredient_hub": INGREDIENT_HUB_SCHEMA,
    "howto_technique": HOWTO_TECHNIQUE_SCHEMA,
    "definition": DEFINITION_SCHEMA,
    "comparison": COMPARISON_SCHEMA,
    "substitute": SUBSTITUTE_SCHEMA,
    "category_roundup": CATEGORY_ROUNDUP_SCHEMA,
}

MAX_TOKENS_BY_TYPE = {
    # Bumped from 4096, then again from 6144, after real truncations
    # (stop_reason: max_tokens, invalid cut-off JSON) hit during testing --
    # once pan_size, related_recipe_slugs, and the step_notes array form
    # were added, and again at 6144 on a length-variance retry of the exact
    # same title that had fit comfortably (4189 tokens) the first time.
    # Confirms output length varies enough attempt-to-attempt that a budget
    # needs real margin, not just enough for one successful sample.
    "recipe_or_dish": 8192,
    # The other 5 budgets below were bumped ~35-45% after
    # validate_batch_results.py's new max_tokens-headroom check (added
    # post-pilot) found 12 already-published pilot results that had used
    # 85-100% of these exact budgets -- including what-is-dubai-chocolate
    # finishing at literally 100% of definition's old 1500-token budget.
    # None of these had actually truncated yet, but recipe_or_dish's own
    # history shows that's a matter of which attempt gets unlucky, not
    # whether the risk is real -- so these are fixed proactively here
    # rather than waiting for an actual truncated page to surface the gap.
    "ingredient_hub": 3500,
    "howto_technique": 3500,
    "definition": 2200,
    "comparison": 3000,
    # Bumped again 2800 -> 3800 after preflight_check.py's real
    # pre-batch generation (ahead of the 150-title test run) hit 86%
    # of the 2800 budget on a single real "sesame oil substitute"
    # generation -- proof the 2000 -> 2800 bump wasn't enough margin,
    # caught before any real batch spend rather than after a truncated
    # page shipped.
    "substitute": 3800,
    "category_roundup": 2800,
}


def to_strict_schema(schema: dict) -> dict:
    """output_config's json_schema format requires additionalProperties:
    false on every object schema and only supports minItems of 0 or 1 (see
    module docstring) -- deep-copies and adjusts SCHEMA_BY_TYPE's richer
    schemas to satisfy that without changing the source-of-truth dicts
    (which keep minItems for their own documentation value)."""
    schema = copy.deepcopy(schema)

    def walk(node):
        if not isinstance(node, dict):
            return
        node_type = node.get("type")
        types = [node_type] if isinstance(node_type, str) else (node_type or [])
        if "object" in types and "properties" in node:
            node["additionalProperties"] = False
            for sub_schema in node["properties"].values():
                walk(sub_schema)
        if "array" in types and "items" in node:
            node.pop("minItems", None)
            node.pop("maxItems", None)
            walk(node["items"])

    walk(schema)
    return schema


def build_request_params(row: dict, collections: list[dict], techniques: list[dict]) -> dict:
    """row is one CONTENT_QUEUE.csv row (dict of column -> value). Returns the
    `params` object for one Batch API request line (matches a normal Messages
    API request body)."""
    template_type = row["template_type"]
    schema = SCHEMA_BY_TYPE[template_type]
    example = EXAMPLES[template_type]

    context_lines = [
        f"Target SEO keyword / topic: {row['title']}",
        f"Template type: {template_type}",
    ]
    if row.get("category"):
        context_lines.append(f"Content queue category hint: {row['category']}")
    if row.get("page_purpose"):
        context_lines.append(f"Page purpose: {row['page_purpose']}")

    if template_type == "recipe_or_dish":
        collection_list = "\n".join(f"- {c['title']} (slug: {c['slug']})" for c in collections)
        context_lines.append(
            "Existing collections available for category_link (use one of these exactly, "
            "or null if none genuinely fit, never invent a new one):\n" + collection_list
        )
        technique_list = "\n".join(f"- {t['title']} (slug: {t['slug']})" for t in techniques)
        context_lines.append(
            "Existing how-to pages available for technique_link (use one of these exactly, "
            "or null if the recipe doesn't rely on one of these specific techniques):\n" + technique_list
        )

    user_message = (
        "Write the content for one new Tulo page.\n\n"
        + "\n".join(context_lines)
        + "\n\nHere is a real, already-published example of this template type, showing the "
        "expected tone, depth, and exact field usage:\n\n"
        + _example_block(example)
        + "\n\nNow write a complete, original page for the target keyword/topic above, in the "
        "same style and depth."
    )

    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS_BY_TYPE[template_type],
        "system": STYLE_GUIDE,
        "messages": [{"role": "user", "content": user_message}],
        "output_config": {"format": {"type": "json_schema", "schema": to_strict_schema(schema)}},
    }
