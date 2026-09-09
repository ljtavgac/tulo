"""Per-template-type prompt construction for the Batch API content pipeline.

Each template type gets:
- A JSON Schema (used as an Anthropic tool's input_schema, with tool_choice
  forced to that tool) so the model MUST return schema-conformant structured
  output -- not just "please return JSON" prompting. This is a deliberate
  improvement over BATCH_CONTENT_PIPELINE_PLAN.md's original assumption that
  Batch API has "no tool-enforced structured output" -- it does, since each
  batch request is just an ordinary Messages API call under the hood.
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

Return your answer only by calling the provided tool with a complete, valid \
argument object. Do not write any prose outside the tool call.

Every array field (steps, faqs, ingredients, tips_and_variations, etc.) must be \
a real, properly nested JSON array value in the tool call's input, e.g. \
["first item", "second item"] or [{"question": "...", "answer": "..."}, ...]. \
Never represent a list as a plain string, and never use any XML-like \
<parameter name="..."> tags anywhere in the input -- that syntax belongs to a \
different tool-calling format and must not appear in this tool's arguments."""


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
            "type": "object",
            "description": "Map of instruction step index (as a string, 0-based) to a short 'why this step matters' technique note. Include at least 2 entries for the most technique-relevant steps.",
            "additionalProperties": {"type": "string"},
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
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt", "why_it_works",
        "prep_time_minutes", "cook_time_minutes", "total_time_minutes", "servings",
        "ingredients", "instructions", "step_notes", "tips_and_variations",
        "storage_and_reheating", "reader_tips", "faqs", "technique_link", "category_link",
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
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt", "description",
        "substitutes", "storage", "uses", "nutrition_note", "buying_tips",
        "pairing_suggestions", "variety_notes", "faqs",
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
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt", "intro",
        "steps", "common_mistakes", "equipment", "faqs",
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
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt", "direct_answer",
        "expanded_explanation", "usage_origin", "substitute_note", "link_terms", "faqs",
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
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt", "item_a_name",
        "item_b_name", "comparison_table", "verdict", "sections", "faqs",
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
    },
    "required": [
        "title", "meta_description", "hero_image_query", "image_alt",
        "ranked_substitutes", "baking_vs_cooking_note", "faqs",
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
    },
    "required": ["title", "meta_description", "intro", "recipe_cards", "sub_categories", "faqs"],
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
        "step_notes": {
            "2": "Overmixing once the flour is added develops gluten, which is what makes quick breads turn dense and tough instead of tender.",
            "4": "The toothpick test in the very center, not near the edge, is what actually confirms doneness; the edges bake through well before the center does.",
        },
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

TOOL_NAME_BY_TYPE = {
    "recipe_or_dish": "emit_recipe_or_dish_content",
    "ingredient_hub": "emit_ingredient_hub_content",
    "howto_technique": "emit_howto_technique_content",
    "definition": "emit_definition_content",
    "comparison": "emit_comparison_content",
    "substitute": "emit_substitute_content",
    "category_roundup": "emit_category_roundup_content",
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
    "recipe_or_dish": 4096,
    "ingredient_hub": 2500,
    "howto_technique": 2500,
    "definition": 1500,
    "comparison": 2200,
    "substitute": 2000,
    "category_roundup": 2800,
}


def build_request_params(row: dict, collections: list[dict], techniques: list[dict]) -> dict:
    """row is one CONTENT_QUEUE.csv row (dict of column -> value). Returns the
    `params` object for one Batch API request line (matches a normal Messages
    API request body)."""
    template_type = row["template_type"]
    schema = SCHEMA_BY_TYPE[template_type]
    tool_name = TOOL_NAME_BY_TYPE[template_type]
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
        "same style and depth. Call the tool with your answer."
    )

    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS_BY_TYPE[template_type],
        "system": STYLE_GUIDE,
        "messages": [{"role": "user", "content": user_message}],
        "tools": [
            {
                "name": tool_name,
                "description": f"Emit the complete content object for a {template_type} page.",
                "input_schema": schema,
            }
        ],
        "tool_choice": {"type": "tool", "name": tool_name},
    }
