"""
Seeds one hand-authored example page per template type, for the template
review step described in WORKFLOW.md ("build order: templates before
content"). Titles/keywords below are copied from real CONTENT_QUEUE.csv
rows as plain literals, this module never reads or writes that CSV file.

Run standalone with `python -m app.seed_templates`, or it runs
automatically on API startup if the pages table is empty (see main.py).
"""

import copy

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Page

SEED_PAGES = [
    {
        "slug": "homepage",
        "template_type": "homepage",
        "title": "Homepage",
        "batch_number": 0,
        "content": {
            "meta_description": (
                "Tulo is a no-clutter recipe site, ingredients and instructions up "
                "front, plus native serving-size scaling and unit conversion built "
                "into every recipe."
            ),
            "featured_recipe_slugs": ["banana-nut-bread"],
            "category_links": [
                {"title": "Eggplant Recipes", "slug": "eggplant-recipes"},
            ],
            "tool_links": [
                {"title": "Kitchen Measurement Conversion Calculator", "slug": "conversion-calculator"},
                {"title": "Cooking Time & Temperature Guide", "slug": "time-temperature-guide"},
                {"title": "Custom Recipe Generator", "slug": "recipe-generator"},
            ],
            "positioning_statement": (
                "No life story before the recipe. No cross-vertical clutter. "
                "Just the recipe, the ingredient info, and the tools you actually "
                "came here for, visible the moment the page loads."
            ),
        },
    },
    {
        "slug": "banana-nut-bread",
        "template_type": "recipe_or_dish",
        "title": "Banana Nut Bread Recipe",
        "batch_number": 1,
        "content": {
            "meta_description": (
                "A moist banana nut bread recipe using extra-ripe bananas, ready in "
                "about an hour. Includes a live serving-size scaler and US/metric "
                "unit toggle."
            ),
            "hero_image_query": "banana nut bread",
            "why_it_works": (
                "Extra-ripe, well-spotted bananas add natural sweetness and "
                "moisture, so this loaf stays tender without drying out, and "
                "a quick one-bowl method means less cleanup."
            ),
            "prep_time_minutes": 15,
            "cook_time_minutes": 60,
            "total_time_minutes": 75,
            "servings": 10,
            # Areas are baking-surface area (length x width, or pi*r^2),
            # the standard basis for pan substitution -- alternatives are
            # limited to other single-vessel loaf/round pans playing the
            # same role as the original, not something like a muffin tin
            # where the area-ratio time math doesn't actually apply.
            "pan_size": {
                "current": {"label": "9x5-inch loaf pan", "area_sq_in": 45},
                "alternatives": [
                    {"label": "8x4-inch loaf pan", "area_sq_in": 32},
                    {"label": "9-inch round cake pan", "area_sq_in": 64},
                ],
            },
            # Quantities are numeric (base_qty / base_qty_metric) rather than
            # free-text strings so the frontend's serving-size scaler can
            # actually recalculate them, not just relabel a fixed string.
            "ingredients": [
                {"name": "bananas, mashed", "base_qty": 3, "unit_us": "medium ripe", "base_qty_metric": 3, "unit_metric": "medium ripe", "hub_slug": None, "nutrition_per_unit": {"calories": 105, "protein_g": 1.3, "carbs_g": 27.0, "fat_g": 0.4}},
                {"name": "unsalted butter, melted", "base_qty": 1 / 3, "unit_us": "cup", "base_qty_metric": 75, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 1628, "protein_g": 1.9, "carbs_g": 0.1, "fat_g": 184.0}},
                {"name": "granulated sugar", "base_qty": 0.75, "unit_us": "cup", "base_qty_metric": 150, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 774, "protein_g": 0, "carbs_g": 200.0, "fat_g": 0}},
                {"name": "egg, beaten", "base_qty": 1, "unit_us": "large", "base_qty_metric": 1, "unit_metric": "large", "hub_slug": None, "nutrition_per_unit": {"calories": 72, "protein_g": 6.3, "carbs_g": 0.4, "fat_g": 4.8}},
                {"name": "vanilla extract", "base_qty": 1, "unit_us": "tsp", "base_qty_metric": 5, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 12, "protein_g": 0, "carbs_g": 0.5, "fat_g": 0}},
                {"name": "baking soda", "base_qty": 1, "unit_us": "tsp", "base_qty_metric": 5, "unit_metric": "g", "hub_slug": None},
                {"name": "salt", "base_qty": 0.25, "unit_us": "tsp", "base_qty_metric": 1.5, "unit_metric": "g", "hub_slug": None},
                {"name": "all-purpose flour", "base_qty": 1.5, "unit_us": "cups", "base_qty_metric": 190, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 455, "protein_g": 13.0, "carbs_g": 95.0, "fat_g": 1.2}},
                {"name": "walnuts, chopped", "base_qty": 1, "unit_us": "cup", "base_qty_metric": 120, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 765, "protein_g": 18.0, "carbs_g": 16.0, "fat_g": 76.0}},
            ],
            "instructions": [
                "Preheat the oven to 350°F (175°C). Grease a 9x5-inch loaf pan.",
                "In a large bowl, mash the ripe bananas with a fork until smooth.",
                "Stir the melted butter into the mashed banana.",
                "Mix in the sugar, beaten egg, and vanilla extract.",
                "Sprinkle the baking soda and salt over the mixture and stir in.",
                "Add the flour and mix until just combined, don't overmix, or the bread will turn out dense.",
                "Fold in the chopped walnuts.",
                "Pour the batter into the prepared loaf pan.",
                "Bake for 55-65 minutes, until a toothpick inserted into the center comes out clean.",
                "Cool in the pan for 10 minutes, then turn out onto a wire rack to cool completely before slicing.",
            ],
            "step_notes": {
                4: "Baking soda needs to be distributed evenly through the wet mixture before the flour goes in, so the leavening reaction happens uniformly through the batter instead of in pockets.",
                9: "Cooling in the pan first lets the loaf firm up enough to hold its shape when unmolded; moving it to a wire rack after that stops the bottom from steaming against the pan and turning soggy.",
            },
            "tips_and_variations": [
                "Very ripe, heavily spotted (almost black) bananas give noticeably more flavor than yellow ones, don't toss bananas just because they've browned.",
                "Swap up to half the flour for whole wheat flour for a heartier crumb. Going past half makes the loaf noticeably dense.",
                "No walnuts on hand? Pecans work as a 1:1 swap, or leave nuts out entirely, the texture changes slightly but the recipe still holds together.",
                "For extra moisture, add 2 tablespoons of sour cream or plain yogurt along with the wet ingredients.",
            ],
            "reader_tips": [
                "Room-temperature eggs and butter blend into the batter more evenly than cold ones straight from the fridge, since this one-bowl method has no creaming step to work out lumps.",
                "If the top browns too fast before the center sets, tent it loosely with foil for the last 15 minutes rather than pulling the loaf early.",
            ],
            "storage_and_reheating": (
                "Store cooled bread tightly wrapped at room temperature for up to 4 "
                "days, or in the refrigerator for up to a week. To freeze, wrap the "
                "whole loaf or individual slices tightly in plastic wrap, then foil, "
                "and freeze for up to 3 months. Thaw overnight at room temperature, "
                "or microwave a single slice for 15-20 seconds."
            ),
            # nutrition_note intentionally omitted -- superseded by the live
            # nutrition block computed from nutrition_per_unit above.
            "faqs": [
                {
                    "question": "Can I freeze banana nut bread?",
                    "answer": (
                        "Yes. Wrap the fully cooled loaf tightly in plastic wrap, "
                        "then a layer of foil, and freeze for up to 3 months. Thaw "
                        "overnight at room temperature before slicing."
                    ),
                },
                {
                    "question": "Why is my banana bread dense or gummy?",
                    "answer": (
                        "The most common cause is overmixing once the flour is "
                        "added, stir only until the streaks of flour disappear. "
                        "Underbaking is the second most common cause: test with a "
                        "toothpick in the very center of the loaf, not near the edge."
                    ),
                },
                {
                    "question": "Can I use frozen bananas?",
                    "answer": (
                        "Yes, and they work well. Thaw them completely first and "
                        "drain off the excess liquid that collects before mashing, "
                        "or the batter can end up too wet."
                    ),
                },
                {
                    "question": "Can I make this recipe without eggs?",
                    "answer": (
                        "Substitute one flax egg per egg: 1 tablespoon ground "
                        "flaxseed mixed with 3 tablespoons water, rested for 5 "
                        "minutes until it thickens. The crumb will be slightly "
                        "denser, but the loaf still holds together well."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": [],
            # No seeded category genuinely fits banana bread (the only
            # roundup example is eggplant recipes) -- left null rather than
            # linking somewhere unrelated just to fill the slot.
            "category_link": None,
        },
    },
    {
        "slug": "chives",
        "template_type": "ingredient_hub",
        "title": "Chives",
        "batch_number": 1,
        "content": {
            "meta_description": (
                "What chives are, the best substitutes with ratios, how to store "
                "them so they don't wilt, and how to use them without losing their "
                "flavor."
            ),
            "hero_image_query": "fresh chives",
            "description": (
                "Chives (Allium schoenoprasum) are the mildest member of the onion "
                "family, grown for their thin, hollow, grass-like green stems. They "
                "deliver a delicate onion flavor without the sharpness of scallions "
                "or raw onion, which is why they're used as a finishing herb rather "
                "than a base cooking ingredient."
            ),
            "substitutes": [
                {"name": "Scallion greens (green onion tops)", "ratio": "1:1", "note": "Slightly stronger onion flavor, but the closest visual and flavor match.", "ratio_multiplier": 1.0},
                {"name": "Green onion, whole", "ratio": "1:1", "note": "Similar flavor profile to scallion greens, a bit more oniony overall.", "ratio_multiplier": 1.0},
                {"name": "Parsley + a pinch of onion powder", "ratio": "1:1 (as parsley)", "note": "Use for the color/garnish effect without onion flavor; add onion powder separately to taste.", "ratio_multiplier": 1.0},
                {"name": "Leek greens, finely minced", "ratio": "1:1", "note": "Milder and slightly sweeter; mince very finely since leek greens are more fibrous.", "ratio_multiplier": 1.0},
            ],
            "substitute_page_slug": None,
            "storage": (
                "Fresh chives wilt quickly. Wrap loosely in a damp paper towel and "
                "store in a sealed container or bag in the refrigerator crisper "
                "drawer, they'll keep for about a week. For longer storage, snip "
                "and freeze in an airtight bag or ice cube tray with a little water "
                "or oil; frozen chives lose their crisp texture but keep their "
                "flavor well for cooked dishes."
            ),
            "uses": (
                "Snip with scissors directly onto finished dishes, baked potatoes, "
                "scrambled eggs, soups, dips, and salads. Chives lose flavor and turn "
                "dull if cooked for long, so add them at the very end or as a garnish "
                "rather than early in cooking."
            ),
            "nutrition_note": (
                "Chives are low in calories and used in small quantities, but they "
                "contain vitamin K, vitamin C, and modest amounts of vitamin A, "
                "more of a flavor accent than a significant nutrient source at "
                "typical serving sizes."
            ),
            "buying_tips": (
                "Look for bright green, firm stems with no yellowing or "
                "sliminess at the cut ends. Buy in small bunches, they wilt "
                "within a few days, so a bunch used up gradually beats a "
                "large one going slimy in the crisper."
            ),
            "pairing_suggestions": (
                "Pairs naturally with sour cream, crème fraîche, and butter "
                "in potato and egg dishes, and with mild white fish or "
                "chicken where a stronger onion flavor would overpower."
            ),
            "variety_notes": (
                "Garlic chives (Chinese chives) are a different plant "
                "entirely, flat, wider leaves and a mild garlic flavor "
                "rather than onion. They are not a 1:1 swap for standard "
                "chives in flavor, though both work as a garnish."
            ),
            "faqs": [
                {
                    "question": "Are chives and green onions the same thing?",
                    "answer": (
                        "No, though they're often confused. Chives are a distinct, "
                        "thinner herb with a milder flavor and are never eaten "
                        "beyond the green stem. Green onions (scallions) are a "
                        "young onion with both a white bulb end and green top, both "
                        "of which are eaten, and have a noticeably stronger flavor."
                    ),
                },
                {
                    "question": "Can I substitute dried chives for fresh?",
                    "answer": (
                        "You can, but expect a real drop in flavor and color, "
                        "drying mutes chives' flavor more than most herbs. Use "
                        "about a third of the amount called for fresh, and add "
                        "them earlier in cooking rather than as a raw garnish."
                    ),
                },
                {
                    "question": "Do chives regrow after you cut them?",
                    "answer": (
                        "Yes, if grown as a live plant rather than bought pre-cut. "
                        "Snip stems about an inch above the soil, leaving the base "
                        "intact, and a healthy plant will regrow within about two "
                        "weeks."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_ingredient_slugs": ["creme-fraiche"],
        },
    },
    {
        "slug": "how-to-cook-spaghetti-squash",
        "template_type": "howto_technique",
        "title": "How to Cook Spaghetti Squash",
        "batch_number": 1,
        "content": {
            "meta_description": (
                "How to roast spaghetti squash so it separates into tender strands, "
                "plus the most common mistake that leaves it mushy or undercooked."
            ),
            "hero_image_query": "roasted spaghetti squash",
            "intro": (
                "Spaghetti squash only takes on its signature noodle-like "
                "strands with the right roasting setup, cut wrong or "
                "roasted the wrong way up and it turns mushy or stays "
                "undercooked in the center. This walks through the "
                "roasting method that reliably gets long, distinct "
                "strands every time."
            ),
            "steps": [
                "Preheat the oven to 400°F (200°C).",
                "Slice the spaghetti squash in half lengthwise, from stem to base. If the whole squash is hard to cut, microwave it whole for 3-4 minutes first to soften the skin.",
                "Scoop out the seeds and stringy pulp from the center with a spoon, just like a pumpkin.",
                "Drizzle the cut sides with olive oil and season with salt and pepper.",
                "Place both halves cut-side down on a parchment-lined baking sheet.",
                "Roast for 40-50 minutes, until the skin gives slightly when pressed and a fork slides in easily.",
                "Let the squash cool for about 10 minutes, it holds heat and can burn fingers if handled right away.",
                "Using a fork, scrape the flesh lengthwise from the skin. It separates into long, spaghetti-like strands.",
            ],
            "common_mistakes": [
                "Roasting cut-side up: cut-side down traps steam and keeps the flesh moist; cut-side up dries the strands out on the surface while leaving the center undercooked.",
                "Undercooking: if a fork doesn't glide through easily, the strands come out short and won't separate cleanly. Give it the full roasting time rather than checking too early.",
                "Not draining excess moisture: spaghetti squash holds a lot of water. If the dish will sit or be sauced, salt the strands lightly and let them sit in a colander for a few minutes to release extra liquid.",
            ],
            "equipment": ["Sharp chef's knife", "Baking sheet", "Parchment paper (optional)", "Fork"],
            "faqs": [
                {
                    "question": "Can I microwave spaghetti squash instead of roasting it?",
                    "answer": (
                        "Yes, it's faster but the strands turn out softer and wetter. "
                        "Halve and seed it, place cut-side down in a microwave-safe "
                        "dish with an inch of water, and microwave 10-12 minutes for "
                        "an average-size squash, checking for fork-tenderness."
                    ),
                },
                {
                    "question": "How do I know when spaghetti squash is done?",
                    "answer": (
                        "A fork should slide into the flesh with almost no "
                        "resistance, and the skin gives slightly when pressed. If "
                        "the fork meets resistance, the strands will be short and "
                        "won't separate cleanly, give it more time rather than "
                        "pulling it early."
                    ),
                },
                {
                    "question": "Why did my spaghetti squash come out watery?",
                    "answer": (
                        "Spaghetti squash naturally holds a lot of water. Salt the "
                        "scraped strands lightly and let them sit in a colander for "
                        "5-10 minutes before saucing or serving to draw out the "
                        "extra liquid."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_technique_slugs": [],
        },
    },
    {
        "slug": "what-is-tahini",
        "template_type": "definition",
        "title": "What Is Tahini? (And How to Use It)",
        "batch_number": 1,
        "content": {
            "meta_description": (
                "Tahini is a smooth paste made from ground sesame seeds. What it is, "
                "how it's used, and the best substitute if you're out."
            ),
            "hero_image_query": "tahini paste jar",
            "direct_answer": (
                "Tahini is a smooth paste made from toasted, ground sesame seeds, "
                "similar in consistency to thin peanut butter, with a nutty, "
                "slightly bitter flavor and no added sweetness."
            ),
            "expanded_explanation": (
                "It's a foundational ingredient in Middle Eastern and Mediterranean "
                "cooking, made by grinding hulled sesame seeds, sometimes lightly "
                "toasted first, into a smooth, pourable paste, often with a touch of "
                "oil to help it emulsify. Quality varies by roast level and grind, "
                "lighter tahini tastes milder, while darker, more heavily toasted "
                "tahini has a more pronounced, slightly bitter edge."
            ),
            "usage_origin": (
                "Tahini is the base for hummus and baba ganoush, gets whisked into "
                "dressings and sauces (tahini sauce, often with lemon and garlic), "
                "and shows up in both savory dishes and desserts like halva. It "
                "traces back to the Eastern Mediterranean and Middle East, where "
                "sesame has been cultivated and pressed for thousands of years."
            ),
            "substitute_note": "Sunflower seed butter is the closest nut-free substitute, though it lacks tahini's distinct roasted-sesame flavor.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Is tahini the same as peanut butter?",
                    "answer": (
                        "No. Both are smooth, pourable pastes, but tahini is made "
                        "from sesame seeds and has a nuttier, slightly bitter flavor "
                        "with no sweetness, while peanut butter is sweeter and made "
                        "from peanuts, a legume rather than a seed."
                    ),
                },
                {
                    "question": "Why does tahini separate in the jar?",
                    "answer": (
                        "Like natural peanut butter, tahini's oil naturally "
                        "separates and rises to the top during storage. Stir it "
                        "thoroughly (scraping the bottom of the jar) before each "
                        "use, this is normal, not a sign it's gone bad."
                    ),
                },
                {
                    "question": "Does tahini need to be refrigerated?",
                    "answer": (
                        "An unopened jar can be stored in a cool pantry. Once "
                        "opened, refrigerating it extends freshness and slows "
                        "rancidity, though it will thicken and need to come to room "
                        "temperature (or get a quick stir) before it pours easily "
                        "again."
                    ),
                },
            ],
            "related_recipe_slugs": [],
        },
    },
    {
        "slug": "cappuccino-vs-latte",
        "template_type": "comparison",
        "title": "Cappuccino vs. Latte: What's the Difference?",
        "batch_number": 1,
        "content": {
            "meta_description": (
                "Cappuccino vs. latte: the real difference is the milk-to-foam "
                "ratio. A side-by-side comparison to help you order, or make, "
                "the right one."
            ),
            "hero_image_query": "cappuccino and latte side by side",
            "item_a_name": "Cappuccino",
            "item_b_name": "Latte",
            "comparison_table": [
                {"attribute": "Espresso", "item_a": "1-2 shots", "item_b": "1-2 shots"},
                {"attribute": "Steamed milk", "item_a": "Roughly equal part to the espresso", "item_b": "Much larger proportion, 2-3x the espresso"},
                {"attribute": "Milk foam", "item_a": "Thick, deep foam layer (about a third of the drink)", "item_b": "Thin foam layer, just enough to cap the drink"},
                {"attribute": "Typical size", "item_a": "5-6 oz", "item_b": "8-12+ oz"},
                {"attribute": "Texture", "item_a": "Light, airy, more foam than liquid milk", "item_b": "Silky, milk-forward, less foam"},
            ],
            "verdict": (
                "Choose a cappuccino for a stronger, more concentrated coffee-forward "
                "drink with a distinct foam texture. Choose a latte for a milkier, "
                "smoother, more mellow drink, and more room for flavored syrups, "
                "since there's more milk volume to carry them."
            ),
            "sections": [
                {
                    "heading": "Cappuccino",
                    "body": (
                        "Built in roughly equal thirds of espresso, steamed milk, and "
                        "milk foam, the cappuccino is defined by that thick foam cap, "
                        "traditionally spooned or poured on top so it holds its shape."
                    ),
                },
                {
                    "heading": "Latte",
                    "body": (
                        "A latte is mostly steamed milk with a shot or two of espresso "
                        "and a thin layer of foam, the higher milk ratio is also what "
                        "makes lattes the go-to canvas for latte art."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "Which has more caffeine, a cappuccino or a latte?",
                    "answer": (
                        "Neither - caffeine comes entirely from the espresso shots, "
                        "and both drinks typically use the same 1-2 shots. The "
                        "difference is milk volume, not caffeine content, so a "
                        "latte doesn't dilute the caffeine, it just dilutes the "
                        "coffee flavor across more liquid."
                    ),
                },
                {
                    "question": "Can I make either one without an espresso machine?",
                    "answer": (
                        "Yes, with a moka pot for a strong coffee base and a "
                        "handheld frother or a mason jar (shake hot milk, then "
                        "microwave briefly) for the milk. You won't get the same "
                        "microfoam texture as a steam wand, but the ratios still "
                        "translate."
                    ),
                },
                {
                    "question": "Which one should I order if I don't like a strong coffee taste?",
                    "answer": (
                        "A latte - the higher milk-to-espresso ratio mellows the "
                        "coffee flavor considerably compared to a cappuccino's "
                        "thicker foam and more concentrated taste per sip."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "baking-soda-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Baking Soda",
        "batch_number": 1,
        "content": {
            "meta_description": (
                "Out of baking soda? Here are four ranked substitutes with exact "
                "ratios, including which ones work best for baking vs. general "
                "cooking."
            ),
            "hero_image_query": "baking soda box",
            "ranked_substitutes": [
                {
                    "name": "Baking powder",
                    "ratio": "Use 3x the amount of baking soda called for",
                    "best_for": "Both baking and cooking",
                    "note": (
                        "Baking powder already contains an acid, so it doesn't need "
                        "the recipe's own acidic ingredient (buttermilk, lemon juice, "
                        "etc.) to activate the way baking soda does. Using 3x the "
                        "amount roughly matches the leavening power, though texture "
                        "and flavor may shift slightly."
                    ),
                },
                {
                    "name": "Baker's ammonia (ammonium carbonate)",
                    "ratio": "1:1",
                    "best_for": "Thin, crisp baked goods (cookies, crackers)",
                    "note": (
                        "Traditional in some European baking; gives extra crispness "
                        "but has a strong ammonia smell during baking that fully "
                        "dissipates, not ideal for thick or dense baked goods, "
                        "where the smell can linger if it can't escape."
                    ),
                },
                {
                    "name": "Potassium bicarbonate + a pinch of salt",
                    "ratio": "1:1, plus a small pinch of salt",
                    "best_for": "Sodium-reduced diets",
                    "note": (
                        "Chemically similar leavening action to baking soda without "
                        "the sodium; the added pinch of salt approximates baking "
                        "soda's flavor contribution."
                    ),
                },
                {
                    "name": "Self-rising flour",
                    "ratio": "Replace the recipe's flour with self-rising flour and omit the baking soda and any added salt",
                    "best_for": "Simple quick breads and biscuits",
                    "note": (
                        "Self-rising flour already contains both leavening and salt, "
                        "so this only works if you're replacing the recipe's plain "
                        "flour with it, not as a direct add-in alongside the "
                        "regular flour."
                    ),
                },
            ],
            "baking_vs_cooking_note": (
                "The substitutes above are for baking soda's leavening role in baked "
                "goods. If a savory recipe calls for a pinch of baking soda for "
                "browning or tenderizing (stir-fries, caramelizing onions), there "
                "isn't a good direct substitute, it's best to simply omit it there."
            ),
            "faqs": [
                {
                    "question": "Can I use baking powder and baking soda interchangeably?",
                    "answer": (
                        "Not 1:1. Baking powder is weaker per volume and already "
                        "contains its own acid, so use about 3x the amount of "
                        "baking powder to replace a given amount of baking soda, "
                        "and expect a slightly different texture and flavor."
                    ),
                },
                {
                    "question": "What happens if I leave baking soda out of a recipe entirely?",
                    "answer": (
                        "The baked good won't rise properly and will turn out flat "
                        "and dense, since baking soda is what reacts with the "
                        "recipe's acidic ingredients to produce the gas bubbles "
                        "that create lift. It's not safe to just omit it without "
                        "substituting something in its place."
                    ),
                },
                {
                    "question": "Does baking soda go bad?",
                    "answer": (
                        "It doesn't spoil, but it does lose leavening power over "
                        "time, especially once opened. Test it by dropping a "
                        "pinch into vinegar, vigorous fizzing means it's still "
                        "active; a weak reaction means it's time to replace it."
                    ),
                },
            ],
            "hub_page_slug": None,
            "recipe_slugs": [],
        },
    },
    {
        "slug": "eggplant-recipes",
        "template_type": "category_roundup",
        "title": "Eggplant Recipes",
        "batch_number": 1,
        "content": {
            "meta_description": (
                "Eggplant recipes organized by cooking method - roasted, fried, "
                "grilled, and curried - with a real curated pick instead of an "
                "auto-generated list."
            ),
            "intro": (
                "Eggplant's spongy texture takes on flavor differently depending on "
                "how it's cooked, roasted until creamy, breaded and fried, or "
                "simmered low and slow. These are the eggplant recipes worth having "
                "in rotation, organized by cooking method."
            ),
            "recipe_cards": [
                {"title": "Baba Ganoush", "slug": None, "description": "Smoky, roasted eggplant dip blended with tahini, garlic, and lemon.", "image_query": "baba ganoush"},
                {"title": "Eggplant Parmesan", "slug": None, "description": "Breaded, fried (or baked) eggplant layered with marinara and melted cheese.", "image_query": "eggplant parmesan"},
                {"title": "Roasted Eggplant with Garlic and Herbs", "slug": None, "description": "The simplest way to cook eggplant - olive oil, high heat, and just enough seasoning to let it shine.", "image_query": "roasted eggplant"},
                {"title": "Eggplant Curry (Baingan Bharta)", "slug": None, "description": "Charred, mashed eggplant simmered with tomatoes, onion, and warm spices.", "image_query": "baingan bharta"},
                {"title": "Grilled Eggplant Slices", "slug": None, "description": "Salted, grilled eggplant rounds with a quick balsamic glaze.", "image_query": "grilled eggplant"},
                {"title": "Miso-Glazed Eggplant (Nasu Dengaku)", "slug": None, "description": "Broiled eggplant halves topped with a sweet-savory miso glaze.", "image_query": "nasu dengaku"},
            ],
            "sub_categories": [
                {"label": "Mediterranean", "items": ["Baba Ganoush", "Grilled Eggplant Slices"]},
                {"label": "Comfort Food", "items": ["Eggplant Parmesan"]},
                {"label": "Global", "items": ["Eggplant Curry (Baingan Bharta)", "Miso-Glazed Eggplant (Nasu Dengaku)"]},
            ],
            "faqs": [
                {
                    "question": "How do I keep eggplant from tasting bitter?",
                    "answer": (
                        "Modern eggplant varieties are bred to be much less bitter "
                        "than older ones, so salting is mostly optional today. If "
                        "using a large, older, or very seedy eggplant, salt the cut "
                        "flesh, let it sit 20-30 minutes, then blot dry before "
                        "cooking, this also helps it absorb less oil."
                    ),
                },
                {
                    "question": "Do I need to peel eggplant before cooking?",
                    "answer": (
                        "No, the skin is edible and holds the flesh together during "
                        "cooking. Peel it only if a recipe specifically calls for a "
                        "smoother texture (some dips, like baba ganoush, are often "
                        "made without the skin)."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    # --- Batch 2: 10 more of each content template, so the homepage's
    # per-template carousels have more than a single card to show. Topics
    # are pulled from real CONTENT_QUEUE.csv rows (same convention as the
    # batch 1 review set above), written out at a slightly more concise
    # depth than the batch 1 examples to keep this batch reviewable.
    {
        "slug": "parmesan-crusted-chicken",
        "template_type": "recipe_or_dish",
        "title": "Parmesan Crusted Chicken Recipe",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Parmesan crusted chicken with a crisp, cheesy crust and a juicy "
                "center, baked (not fried) in about 30 minutes."
            ),
            "hero_image_query": "parmesan crusted chicken",
            "why_it_works": (
                "A mayonnaise-and-parmesan coating keeps the chicken moist while "
                "it bakes, and gives the panko topping something to cling to so "
                "it turns deeply golden without deep-frying."
            ),
            "prep_time_minutes": 15,
            "cook_time_minutes": 25,
            "total_time_minutes": 40,
            "servings": 4,
            # nutrition_per_unit values below are per 1 unit_us as written
            # (e.g. per medium breast, per cup) -- standard USDA-comparable
            # figures for the named ingredient, same "estimate, not lab
            # analysis" precision as the site's existing nutrition_note
            # prose. Salt/pepper are left without one, same as the prose
            # estimate already excluded their negligible calories.
            "ingredients": [
                {"name": "boneless, skinless chicken breasts", "base_qty": 4, "unit_us": "medium", "base_qty_metric": 4, "unit_metric": "medium", "hub_slug": None, "nutrition_per_unit": {"calories": 215, "protein_g": 40.0, "carbs_g": 0, "fat_g": 5.0}},
                {"name": "mayonnaise", "base_qty": 0.5, "unit_us": "cup", "base_qty_metric": 115, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 1500, "protein_g": 2.0, "carbs_g": 2.0, "fat_g": 165.0}},
                {"name": "grated parmesan", "base_qty": 0.5, "unit_us": "cup", "base_qty_metric": 50, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 431, "protein_g": 38.5, "carbs_g": 3.6, "fat_g": 28.6}},
                {"name": "panko breadcrumbs", "base_qty": 0.75, "unit_us": "cup", "base_qty_metric": 45, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 190, "protein_g": 6.0, "carbs_g": 36.0, "fat_g": 1.0}},
                {"name": "garlic powder", "base_qty": 1, "unit_us": "tsp", "base_qty_metric": 3, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 9, "protein_g": 0.5, "carbs_g": 2.0, "fat_g": 0}},
                {"name": "salt", "base_qty": 0.5, "unit_us": "tsp", "base_qty_metric": 3, "unit_metric": "g", "hub_slug": None},
                {"name": "black pepper", "base_qty": 0.25, "unit_us": "tsp", "base_qty_metric": 0.5, "unit_metric": "g", "hub_slug": None},
            ],
            "instructions": [
                "Preheat the oven to 400°F (200°C) and line a baking sheet with parchment.",
                "Pat the chicken breasts dry and season both sides with salt and pepper.",
                "Stir the mayonnaise, parmesan, and garlic powder together in a small bowl.",
                "Spread the mayonnaise mixture evenly over the top of each chicken breast.",
                "Press panko breadcrumbs on top of the mayonnaise layer so it sticks.",
                "Bake for 22-25 minutes, until the crust is golden and the internal temperature reaches 165°F (74°C).",
                "Let rest for 5 minutes before slicing.",
            ],
            # Indexes match the instructions list above (0-based). Only
            # steps with a real, non-obvious technique reason get one -- not
            # every step, which would just be restating what the step
            # already says.
            "step_notes": {
                1: "A dry surface helps the mayonnaise layer adhere instead of sliding off as it bakes.",
                3: "Mayonnaise is already an emulsified fat, so it bastes the chicken as it bakes and gives the panko something to grip, doing double duty a plain egg wash wouldn't.",
                6: "Resting lets the juices redistribute through the meat instead of running out onto the cutting board the moment it's sliced.",
            },
            "tips_and_variations": [
                "Pound thicker breasts to an even ½-inch thickness first so they cook through at the same rate the crust browns.",
                "For extra crunch, broil for the last 1-2 minutes, watch closely, panko browns fast under a broiler.",
            ],
            "reader_tips": [
                "A wire rack set inside the baking sheet keeps the bottom of the crust from steaming against the pan, so it stays crisp all the way around, not just on top.",
                "Freshly grated parmesan from a block melts and browns better than the pre-shredded kind, which is coated in anti-caking starch.",
            ],
            "storage_and_reheating": (
                "Refrigerate leftovers up to 3 days. Reheat in a 350°F oven or air "
                "fryer to re-crisp the topping, microwaving works but leaves the "
                "crust soft."
            ),
            # nutrition_note intentionally omitted here -- the live nutrition
            # block computed from each ingredient's nutrition_per_unit above
            # supersedes it (see RecipeIngredientsPanel), and showing both
            # would risk two different-looking numbers on the same page.
            "faqs": [
                {
                    "question": "Can I use chicken thighs instead of breasts?",
                    "answer": (
                        "Yes, boneless, skinless thighs work well and are more "
                        "forgiving if slightly overcooked. Cook to the same 165°F "
                        "(74°C) internal temperature; thighs may need a few extra "
                        "minutes depending on thickness."
                    ),
                },
                {
                    "question": "Why is my parmesan crust soggy instead of crisp?",
                    "answer": (
                        "Usually too much moisture in the mayonnaise layer, or "
                        "crowding the baking sheet so steam can't escape. Use a "
                        "single layer with space between pieces, and finish under "
                        "the broiler briefly if the crust needs more color."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": ["chicken-broccoli-rice-casserole", "chicken-al-pastor"],
            "category_link": {"title": "Italian Recipes", "slug": "italian-recipes"},
        },
    },
    {
        "slug": "chicken-broccoli-rice-casserole",
        "template_type": "recipe_or_dish",
        "title": "Chicken Broccoli Rice Casserole Recipe",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "A one-dish chicken, broccoli, and rice casserole with a creamy "
                "sauce and a melted gruyère topping, real ingredients, no canned "
                "soup shortcut."
            ),
            "hero_image_query": "chicken broccoli rice casserole",
            "why_it_works": (
                "Par-cooking the rice and broccoli separately before combining "
                "means everything finishes baking at the same rate, no raw "
                "centers or mushy broccoli from a single long bake."
            ),
            "prep_time_minutes": 20,
            "cook_time_minutes": 35,
            "total_time_minutes": 55,
            "servings": 6,
            "pan_size": {
                "current": {"label": "9x13-inch baking dish", "area_sq_in": 117},
                "alternatives": [
                    {"label": "8x8-inch square dish", "area_sq_in": 64},
                    {"label": "9x9-inch square dish", "area_sq_in": 81},
                ],
            },
            # See parmesan-crusted-chicken above for the nutrition_per_unit
            # convention (per 1 unit_us, USDA-comparable estimate). This
            # recipe is also the Phase B swap pilot (gruyère -> Comté/Swiss
            # Emmental/Fontina, each with its own nutrition_per_unit on the
            # gruyere-cheese hub page) specifically so the live nutrition
            # block can be verified updating from a serving change and an
            # ingredient swap at the same time, not just one or the other.
            "ingredients": [
                {"name": "cooked, shredded chicken", "base_qty": 3, "unit_us": "cups", "base_qty_metric": 420, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 231, "protein_g": 43.4, "carbs_g": 0, "fat_g": 5.0}},
                {"name": "cooked white rice", "base_qty": 3, "unit_us": "cups", "base_qty_metric": 555, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 206, "protein_g": 4.3, "carbs_g": 45.0, "fat_g": 0.4}},
                {"name": "broccoli florets, blanched", "base_qty": 3, "unit_us": "cups", "base_qty_metric": 270, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 31, "protein_g": 2.5, "carbs_g": 6.0, "fat_g": 0.3}},
                {"name": "chicken broth", "base_qty": 1, "unit_us": "cup", "base_qty_metric": 240, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 15, "protein_g": 1.0, "carbs_g": 1.0, "fat_g": 0.5}},
                {"name": "heavy cream", "base_qty": 1, "unit_us": "cup", "base_qty_metric": 240, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 821, "protein_g": 4.9, "carbs_g": 6.6, "fat_g": 88.0}},
                {"name": "grated gruyère cheese", "base_qty": 1.5, "unit_us": "cups", "base_qty_metric": 150, "unit_metric": "g", "hub_slug": "gruyere-cheese", "nutrition_per_unit": {"calories": 445, "protein_g": 32.1, "carbs_g": 0.4, "fat_g": 34.9}},
                {"name": "garlic, minced", "base_qty": 2, "unit_us": "cloves", "base_qty_metric": 2, "unit_metric": "cloves", "hub_slug": None, "nutrition_per_unit": {"calories": 4, "protein_g": 0.2, "carbs_g": 1.0, "fat_g": 0}},
                {"name": "salt and pepper", "base_qty": 1, "unit_us": "to taste", "base_qty_metric": 1, "unit_metric": "to taste", "hub_slug": None},
            ],
            "instructions": [
                "Preheat the oven to 375°F (190°C) and grease a 9x13-inch baking dish.",
                "In a saucepan, simmer the garlic, chicken broth, and heavy cream for 3-4 minutes until slightly thickened.",
                "Stir in half the gruyère until melted, then season with salt and pepper.",
                "Combine the chicken, rice, and broccoli in the baking dish and pour the sauce over, mixing to coat evenly.",
                "Top with the remaining gruyère.",
                "Bake for 25-30 minutes, until bubbling and golden on top.",
            ],
            # See parmesan-crusted-chicken above for the step_notes convention
            # (0-based index into instructions, only non-obvious steps).
            "step_notes": {
                1: "A brief simmer lets the cream reduce slightly so the sauce clings to the rice and chicken instead of pooling thin at the bottom of the dish.",
                2: "Melting only half the gruyère into the sauce, not all of it, keeps the other half free for a browned, bubbling top layer instead of using it all up in a sauce no one sees.",
                5: "Every component going in is already cooked, so this bake is only about melting, coloring, and building flavor, not also cooking raw rice and chicken through, which is why it comes together in half the time of a from-scratch casserole.",
            },
            "tips_and_variations": [
                "Rotisserie chicken makes this a genuine 20-minute-prep weeknight dish.",
                "No gruyère on hand? Sharp cheddar or Swiss both melt similarly well here.",
            ],
            "reader_tips": [
                "Slightly undercook the rice compared to how you'd eat it plain, it finishes softening in the oven and can turn mushy if it's already fully tender going in.",
                "Let the casserole sit for 5 minutes after it comes out of the oven, the sauce thickens slightly as it cools and holds together better when served.",
            ],
            "storage_and_reheating": (
                "Refrigerate up to 4 days. Reheat covered in a 350°F oven to keep "
                "the rice from drying out, or microwave individual portions with a "
                "splash of broth stirred in."
            ),
            # nutrition_note intentionally omitted -- see the comment above
            # this recipe's ingredients list.
            "faqs": [
                {
                    "question": "Can I make this ahead of time?",
                    "answer": (
                        "Yes, assemble it fully, cover, and refrigerate up to a "
                        "day ahead. Bake straight from the fridge, adding about 10 "
                        "extra minutes to the covered bake time."
                    ),
                },
                {
                    "question": "Can I use frozen broccoli?",
                    "answer": (
                        "Yes, thaw and drain it well first, frozen broccoli holds "
                        "extra water that can make the casserole watery if added "
                        "straight from frozen."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": ["parmesan-crusted-chicken"],
            "category_link": None,
        },
    },
    {
        "slug": "fried-green-tomatoes",
        "template_type": "recipe_or_dish",
        "title": "Fried Green Tomatoes Recipe",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Classic Southern fried green tomatoes with a crisp cornmeal "
                "crust - firm, tart green tomatoes sliced, breaded, and "
                "pan-fried until golden."
            ),
            "hero_image_query": "fried green tomatoes",
            "why_it_works": (
                "Unripe green tomatoes are firm and tart, so they hold their "
                "shape in the pan instead of collapsing into mush the way a "
                "ripe, juicy tomato would."
            ),
            "prep_time_minutes": 15,
            "cook_time_minutes": 15,
            "total_time_minutes": 30,
            "servings": 4,
            # "vegetable oil, for frying" is genuinely approximate: the 0.5 cup
            # listed is what's in the pan, not what ends up in the food. Its
            # nutrition_per_unit below is already adjusted to roughly 20%
            # absorption (a standard shallow-pan-frying estimate), not the
            # full poured amount, so it can multiply by the same base_qty
            # everything else uses.
            "ingredients": [
                {"name": "large green tomatoes, sliced ¼-inch thick", "base_qty": 3, "unit_us": "large", "base_qty_metric": 3, "unit_metric": "large", "hub_slug": None, "nutrition_per_unit": {"calories": 33, "protein_g": 1.6, "carbs_g": 7.0, "fat_g": 0.4}},
                {"name": "all-purpose flour", "base_qty": 0.5, "unit_us": "cup", "base_qty_metric": 60, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 455, "protein_g": 13.0, "carbs_g": 95.0, "fat_g": 1.2}},
                {"name": "eggs, beaten", "base_qty": 2, "unit_us": "large", "base_qty_metric": 2, "unit_metric": "large", "hub_slug": None, "nutrition_per_unit": {"calories": 72, "protein_g": 6.3, "carbs_g": 0.4, "fat_g": 4.8}},
                {"name": "cornmeal", "base_qty": 1, "unit_us": "cup", "base_qty_metric": 140, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 442, "protein_g": 9.9, "carbs_g": 94.0, "fat_g": 4.4}},
                {"name": "salt", "base_qty": 1, "unit_us": "tsp", "base_qty_metric": 6, "unit_metric": "g", "hub_slug": None},
                {"name": "vegetable oil, for frying", "base_qty": 0.5, "unit_us": "cup", "base_qty_metric": 120, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 385, "protein_g": 0, "carbs_g": 0, "fat_g": 43.6}},
            ],
            "instructions": [
                "Set up a breading station: flour in one shallow dish, beaten eggs in a second, cornmeal mixed with salt in a third.",
                "Pat the tomato slices dry with paper towels.",
                "Dredge each slice in flour, then egg, then press into the cornmeal to coat both sides.",
                "Heat the oil in a large skillet over medium-high heat until shimmering.",
                "Fry the tomatoes in batches, 3-4 minutes per side, until deeply golden.",
                "Drain on paper towels or a wire rack and season with a little extra salt while still hot.",
            ],
            "step_notes": {
                1: "Drying the tomato slices first keeps the wet surface from turning the flour coating gummy before the egg and cornmeal layers go on.",
                2: "Each layer needs the one before it to stick: flour gives the egg wash something to cling to, and the egg gives the cornmeal something to bind to, skipping straight to cornmeal on a bare slice would mostly fall off in the pan.",
                5: "Salt sticks to the hot, slightly oily crust right out of the pan far better than it does once the tomatoes cool and the surface stops being tacky.",
            },
            "tips_and_variations": [
                "Don't crowd the pan, too many slices at once drops the oil temperature and the crust turns greasy instead of crisp.",
                "A wire rack over a sheet pan keeps the bottom crust from steaming and going soft the way paper towels can.",
            ],
            "reader_tips": [
                "Salt the sliced tomatoes lightly and let them sit on paper towels for 10 minutes before breading, it pulls out excess moisture that would otherwise make the coating soggy.",
                "Keep the oil at a steady medium-high heat, testing it with a pinch of cornmeal, it should sizzle immediately without smoking.",
            ],
            "storage_and_reheating": (
                "Best eaten fresh. Leftovers keep 1-2 days refrigerated; reheat in "
                "a dry skillet or oven to re-crisp, microwaving makes the crust "
                "soft."
            ),
            # nutrition_note intentionally omitted -- superseded by the live
            # nutrition block computed from nutrition_per_unit above.
            "faqs": [
                {
                    "question": "Can I use ripe red tomatoes instead?",
                    "answer": (
                        "Not well - ripe tomatoes are too soft and juicy and will "
                        "fall apart in the breading and the pan. This recipe "
                        "specifically needs firm, unripe green tomatoes."
                    ),
                },
                {
                    "question": "Can I bake these instead of frying?",
                    "answer": (
                        "Yes, though the crust is thinner and less crisp. Bake at "
                        "425°F on a well-oiled sheet pan for about 15 minutes per "
                        "side, or use an air fryer at 400°F for 8-10 minutes per side."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": [],
            "category_link": None,
        },
    },
    {
        "slug": "sushi-bake",
        "template_type": "recipe_or_dish",
        "title": "Sushi Bake Recipe",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "A crowd-size sushi bake with seasoned rice, a creamy baked "
                "imitation crab topping, and nori for scooping, all the sushi "
                "flavor, none of the rolling."
            ),
            "hero_image_query": "sushi bake casserole",
            "why_it_works": (
                "Layering seasoned sushi rice under a baked, creamy seafood "
                "topping delivers the same flavors as a spicy crab roll at "
                "casserole scale, with nori sheets standing in for the seaweed "
                "wrap, scoop and wrap at the table instead of rolling by hand."
            ),
            "prep_time_minutes": 25,
            "cook_time_minutes": 15,
            "total_time_minutes": 40,
            "servings": 6,
            "pan_size": {
                "current": {"label": "9x13-inch baking dish", "area_sq_in": 117},
                "alternatives": [
                    {"label": "8x8-inch square dish", "area_sq_in": 64},
                    {"label": "9x9-inch square dish", "area_sq_in": 81},
                ],
            },
            # "nori sheets, for serving" has no nutrition_per_unit -- a "pack"
            # varies too much by brand (10 vs. 50 sheets) to give a real
            # per-unit figure, and nori itself is calorie-negligible either
            # way. No step_notes on this recipe either: its instructions are
            # mostly plain assembly, and the two real technique insights
            # (press the rice firmly, save some furikake for after baking)
            # already live in reader_tips above -- duplicating them as
            # step_notes wouldn't add anything, and inventing a third,
            # weaker one just to hit a quota isn't worth it.
            "ingredients": [
                {"name": "sushi rice, cooked and seasoned with rice vinegar", "base_qty": 3, "unit_us": "cups", "base_qty_metric": 555, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 210, "protein_g": 4.0, "carbs_g": 46.0, "fat_g": 0.3}},
                {"name": "imitation crab, chopped", "base_qty": 1, "unit_us": "lb", "base_qty_metric": 454, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 410, "protein_g": 36.0, "carbs_g": 55.0, "fat_g": 2.5}},
                {"name": "mayonnaise", "base_qty": 0.75, "unit_us": "cup", "base_qty_metric": 170, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 1500, "protein_g": 2.0, "carbs_g": 2.0, "fat_g": 165.0}},
                {"name": "cream cheese, softened", "base_qty": 4, "unit_us": "oz", "base_qty_metric": 115, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 100, "protein_g": 1.7, "carbs_g": 1.6, "fat_g": 10.0}},
                {"name": "sriracha", "base_qty": 1, "unit_us": "tbsp", "base_qty_metric": 15, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 15, "protein_g": 0.2, "carbs_g": 3.0, "fat_g": 0}},
                {"name": "furikake seasoning", "base_qty": 2, "unit_us": "tbsp", "base_qty_metric": 12, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 20, "protein_g": 1.0, "carbs_g": 2.0, "fat_g": 1.0}},
                {"name": "nori sheets, for serving", "base_qty": 1, "unit_us": "pack", "base_qty_metric": 1, "unit_metric": "pack", "hub_slug": None},
            ],
            "instructions": [
                "Preheat the oven to 400°F (200°C).",
                "Spread the seasoned sushi rice in an even layer in a greased 9x13-inch baking dish and sprinkle with furikake.",
                "Mix the imitation crab, mayonnaise, cream cheese, and sriracha until smooth.",
                "Spread the crab mixture evenly over the rice.",
                "Bake for 12-15 minutes, until bubbling and lightly golden on top.",
                "Cut nori sheets into squares and serve alongside for scooping.",
            ],
            "tips_and_variations": [
                "Real cooked crab or shrimp works in place of imitation crab for a more upscale version.",
                "Add a thin layer of sliced avocado or cucumber under the topping for texture and freshness.",
            ],
            "reader_tips": [
                "Press the rice layer down firmly and evenly before topping it, gaps let the creamy topping sink through instead of baking to a golden finish on top.",
                "Save a little furikake to sprinkle on after baking, not just before, so some of it stays crunchy instead of steaming soft under the topping.",
            ],
            "storage_and_reheating": (
                "Refrigerate up to 3 days. Reheat in the oven at 350°F until warmed "
                "through, the topping can separate slightly in the microwave."
            ),
            # nutrition_note intentionally omitted -- superseded by the live
            # nutrition block computed from nutrition_per_unit above.
            "faqs": [
                {
                    "question": "What do I eat sushi bake with?",
                    "answer": (
                        "Scoop a portion onto a square of nori, wrap it up like a "
                        "hand roll, and eat it immediately, that's the whole "
                        "appeal, the nori stays crisp only briefly once filled."
                    ),
                },
                {
                    "question": "Can I make sushi bake ahead of time?",
                    "answer": (
                        "Assemble the rice and topping separately up to a day "
                        "ahead and refrigerate. Combine and bake just before "
                        "serving so the topping doesn't dry out under a longer bake."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": [],
            "category_link": {"title": "Japanese Recipes", "slug": "japanese-recipes"},
        },
    },
    {
        "slug": "peri-peri-chicken",
        "template_type": "recipe_or_dish",
        "title": "Peri Peri Chicken Recipe",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Spicy, garlicky peri peri chicken marinated in a bird's eye "
                "chile sauce and grilled or baked until charred, a copycat of "
                "the Portuguese-African classic."
            ),
            "hero_image_query": "grilled peri peri chicken thighs",
            "why_it_works": (
                "A long marinade of chile, garlic, lemon, and smoked paprika "
                "penetrates the chicken rather than just coating the surface, so "
                "the heat and char flavor comes through in every bite, not just "
                "the skin."
            ),
            "prep_time_minutes": 20,
            "cook_time_minutes": 35,
            "total_time_minutes": 55,
            "servings": 4,
            # "chicken thighs and drumsticks, bone-in" is priced/weighed with
            # the bone in, which isn't edible, so its nutrition_per_unit
            # below is a rough as-purchased-weight approximation rather
            # than a precise edible-portion figure -- less exact than a
            # boneless cut like the pilot recipes use. The chiles, smoked
            # paprika, and lemon juice are left without one: each
            # contributes well under 1% of the dish's total calories, the
            # same "genuinely negligible" treatment as salt.
            "ingredients": [
                {"name": "chicken thighs and drumsticks, bone-in", "base_qty": 2.5, "unit_us": "lb", "base_qty_metric": 1130, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 800, "protein_g": 68.0, "carbs_g": 0, "fat_g": 54.0}},
                {"name": "red bird's eye chiles, chopped", "base_qty": 3, "unit_us": "whole", "base_qty_metric": 3, "unit_metric": "whole", "hub_slug": None},
                {"name": "garlic cloves", "base_qty": 4, "unit_us": "cloves", "base_qty_metric": 4, "unit_metric": "cloves", "hub_slug": None, "nutrition_per_unit": {"calories": 4, "protein_g": 0.2, "carbs_g": 1.0, "fat_g": 0}},
                {"name": "smoked paprika", "base_qty": 1, "unit_us": "tbsp", "base_qty_metric": 7, "unit_metric": "g", "hub_slug": None},
                {"name": "lemon juice", "base_qty": 3, "unit_us": "tbsp", "base_qty_metric": 45, "unit_metric": "ml", "hub_slug": None},
                {"name": "olive oil", "base_qty": 3, "unit_us": "tbsp", "base_qty_metric": 45, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 119, "protein_g": 0, "carbs_g": 0, "fat_g": 13.5}},
                {"name": "salt", "base_qty": 1, "unit_us": "tsp", "base_qty_metric": 6, "unit_metric": "g", "hub_slug": None},
            ],
            "instructions": [
                "Blend the chiles, garlic, smoked paprika, lemon juice, olive oil, and salt into a smooth marinade.",
                "Coat the chicken pieces in the marinade, cover, and refrigerate at least 2 hours, ideally overnight.",
                "Preheat a grill (or oven to 425°F / 220°C).",
                "Grill over medium-high heat, turning occasionally, for 30-35 minutes until charred and the internal temperature reaches 165°F (74°C). If baking, roast on a sheet pan for the same time.",
                "Baste with any remaining marinade during the last 10 minutes of cooking.",
                "Rest for 5 minutes before serving.",
            ],
            "step_notes": {
                4: "Basting only in the last 10 minutes, not throughout, keeps the marinade's sugars from burning over the full cook time while still building a glossy, charred glaze at the end.",
                5: "The chicken keeps cooking slightly from residual heat during this rest, and the juices settle back through the meat instead of pooling out the moment it's cut.",
            },
            "tips_and_variations": [
                "Adjust the heat by seeding the chiles for a milder version, or adding an extra chile for more fire.",
                "Spatchcocking a whole chicken instead of using pieces cooks more evenly and gets more skin surface charred.",
            ],
            "reader_tips": [
                "Score the chicken pieces lightly before marinating, it helps the sauce reach past the skin instead of just coating the surface.",
                "Baste only with reserved marinade set aside before the raw chicken went in, not the liquid it marinated in, unless that liquid is brought to a boil first.",
            ],
            "storage_and_reheating": (
                "Refrigerate up to 3 days. Reheat in a 350°F oven to keep the skin "
                "from turning soggy; the microwave works but softens the char."
            ),
            # nutrition_note intentionally omitted -- superseded by the live
            # nutrition block computed from nutrition_per_unit above.
            "faqs": [
                {
                    "question": "What does peri peri mean?",
                    "answer": (
                        "\"Peri peri\" (or piri piri) refers to the African bird's "
                        "eye chile pepper the sauce is built on, and by extension "
                        "the sauce and dishes made with it, a Portuguese-African "
                        "flavor tradition, not a specific restaurant brand."
                    ),
                },
                {
                    "question": "Can I use a store-bought peri peri sauce instead?",
                    "answer": (
                        "Yes, swap the homemade marinade for about 1 cup of a "
                        "bottled peri peri sauce and marinate the same way. Flavor "
                        "intensity varies a lot by brand, so taste and adjust with "
                        "extra lemon or chile if it's mild."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": [],
            "category_link": None,
        },
    },
    {
        "slug": "chicken-al-pastor",
        "template_type": "recipe_or_dish",
        "title": "Chicken Al Pastor Recipe",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "A chicken version of al pastor, marinated in dried chiles, "
                "achiote, and pineapple, then seared for the same sweet, "
                "smoky-spicy flavor as the classic pork version, no vertical spit "
                "required."
            ),
            "hero_image_query": "chicken al pastor tacos",
            "why_it_works": (
                "The same guajillo-and-achiote marinade that defines pork al "
                "pastor works just as well on chicken, and pineapple juice in "
                "the marinade both tenderizes the meat and echoes the classic "
                "spit-roasted pineapple garnish."
            ),
            "prep_time_minutes": 20,
            "cook_time_minutes": 15,
            "total_time_minutes": 35,
            "servings": 4,
            # Dried guajillo chiles and white vinegar are left without a
            # nutrition_per_unit -- dried chiles don't have an easily
            # sourced standard per-whole-chile figure, and both contribute
            # well under 1% of the dish's total calories either way, the
            # same negligible treatment as salt. Achiote paste's value below
            # is a rough estimate (it's mostly ground annatto seed and
            # spices, not a standard packaged food with a nutrition label),
            # kept in because it's the dish's defining ingredient rather
            # than a minor seasoning.
            "ingredients": [
                {"name": "boneless, skinless chicken thighs", "base_qty": 2, "unit_us": "lb", "base_qty_metric": 900, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 540, "protein_g": 92.0, "carbs_g": 0, "fat_g": 21.0}},
                {"name": "dried guajillo chiles, stemmed and seeded", "base_qty": 3, "unit_us": "whole", "base_qty_metric": 3, "unit_metric": "whole", "hub_slug": None},
                {"name": "achiote (annatto) paste", "base_qty": 2, "unit_us": "tbsp", "base_qty_metric": 30, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 35, "protein_g": 0.5, "carbs_g": 5.0, "fat_g": 1.0}},
                {"name": "pineapple juice", "base_qty": 0.5, "unit_us": "cup", "base_qty_metric": 120, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 132, "protein_g": 0.9, "carbs_g": 32.5, "fat_g": 0.3}},
                {"name": "white vinegar", "base_qty": 2, "unit_us": "tbsp", "base_qty_metric": 30, "unit_metric": "ml", "hub_slug": None},
                {"name": "garlic cloves", "base_qty": 3, "unit_us": "cloves", "base_qty_metric": 3, "unit_metric": "cloves", "hub_slug": None, "nutrition_per_unit": {"calories": 4, "protein_g": 0.2, "carbs_g": 1.0, "fat_g": 0}},
                {"name": "fresh pineapple, diced, for serving", "base_qty": 1, "unit_us": "cup", "base_qty_metric": 165, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 83, "protein_g": 0.9, "carbs_g": 21.6, "fat_g": 0.2}},
            ],
            "instructions": [
                "Rehydrate the guajillo chiles in hot water for 10 minutes, then drain.",
                "Blend the chiles, achiote paste, pineapple juice, vinegar, and garlic into a smooth marinade.",
                "Coat the chicken thighs in the marinade and refrigerate at least 1 hour, up to overnight.",
                "Heat a heavy skillet or grill pan over high heat.",
                "Sear the chicken 5-6 minutes per side until charred at the edges and cooked through (165°F / 74°C internal).",
                "Rest 5 minutes, then chop and serve with diced fresh pineapple, in tacos or over rice.",
            ],
            "step_notes": {
                0: "Dried chiles need rehydrating before blending or they stay tough and gritty in the finished marinade instead of pureeing smooth.",
                5: "Resting before chopping keeps the juices in the meat rather than letting them spill out onto the cutting board the moment it's cut into.",
            },
            "tips_and_variations": [
                "Achiote paste is sold in Latin grocery stores and many supermarkets' international aisle, don't substitute plain paprika, it lacks achiote's distinct earthy flavor.",
                "For tacos, warm corn tortillas and top with the chopped chicken, pineapple, chopped onion, and cilantro.",
            ],
            "reader_tips": [
                "Marinate the full time if you can, achiote's flavor is fairly mild until it's actually had time to penetrate the meat, not just coat it.",
                "A hot, barely-oiled pan matters more than a long cook time here, the char comes from contact with high heat, not from cooking the thin-cut thighs longer.",
            ],
            "storage_and_reheating": (
                "Refrigerate up to 3 days. Reheat in a hot skillet to re-crisp the "
                "edges, microwaving works but loses the char."
            ),
            # nutrition_note intentionally omitted -- superseded by the live
            # nutrition block computed from nutrition_per_unit above.
            "faqs": [
                {
                    "question": "Is chicken al pastor traditional, or is pork the only real version?",
                    "answer": (
                        "Pork is the traditional, original version, cooked on a "
                        "vertical trompo spit. Chicken al pastor is a common, "
                        "widely served home and restaurant adaptation of the same "
                        "marinade and flavor profile, not a fabricated substitute."
                    ),
                },
                {
                    "question": "Can I cook this on a vertical spit at home?",
                    "answer": (
                        "Most home kitchens don't have a trompo, so a hot skillet, "
                        "grill, or broiler is the practical substitute, the goal "
                        "is a hard sear with charred edges, which any of those can "
                        "achieve."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": ["parmesan-crusted-chicken"],
            "category_link": {"title": "Taco Recipes", "slug": "taco-recipes"},
        },
    },
    {
        "slug": "mango-ice-cream",
        "template_type": "recipe_or_dish",
        "title": "Mango Ice Cream Recipe",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "No-churn mango ice cream made with sweetened condensed milk and "
                "ripe mango puree, no ice cream maker required."
            ),
            "hero_image_query": "mango ice cream",
            "why_it_works": (
                "Sweetened condensed milk's sugar content lowers the freezing "
                "point enough that the mixture stays scoopable without an ice "
                "cream maker constantly churning air into it, whipped cream "
                "folded in does that job instead."
            ),
            "prep_time_minutes": 15,
            "cook_time_minutes": 0,
            "total_time_minutes": 375,
            "servings": 8,
            "ingredients": [
                {"name": "ripe mangoes, peeled and pureed", "base_qty": 3, "unit_us": "cups", "base_qty_metric": 490, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 110, "protein_g": 1.5, "carbs_g": 28.0, "fat_g": 0.7}},
                {"name": "sweetened condensed milk", "base_qty": 1, "unit_us": "can (14 oz)", "base_qty_metric": 397, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 1274, "protein_g": 31.4, "carbs_g": 216.0, "fat_g": 34.5}},
                {"name": "heavy cream, cold", "base_qty": 2, "unit_us": "cups", "base_qty_metric": 480, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 821, "protein_g": 4.9, "carbs_g": 6.6, "fat_g": 88.0}},
                {"name": "lime juice", "base_qty": 1, "unit_us": "tbsp", "base_qty_metric": 15, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 4, "protein_g": 0.1, "carbs_g": 1.4, "fat_g": 0}},
            ],
            "instructions": [
                "Puree the mango with the lime juice until smooth.",
                "Stir the mango puree into the sweetened condensed milk.",
                "In a separate bowl, whip the cold heavy cream to stiff peaks.",
                "Gently fold the whipped cream into the mango mixture until no streaks remain.",
                "Pour into a loaf pan or freezer-safe container and smooth the top.",
                "Freeze at least 6 hours, ideally overnight, before scooping.",
            ],
            # Only one step_note here, not the usual 2-3 -- most of this
            # recipe's real technique insight is already in reader_tips
            # above (chilling the bowl, the plastic-wrap trick), and
            # inventing a second, weaker note on top of that just to hit a
            # round number isn't worth it.
            "step_notes": {
                3: "Folding rather than stirring keeps the whipped air in the cream intact, which is what makes this scoopable without a machine constantly churning it, stirring would deflate it back to dense and icy.",
            },
            "tips_and_variations": [
                "Frozen mango chunks, thawed, work fine when ripe fresh mango isn't in season.",
                "A splash of coconut cream folded in alongside the whipped cream adds a tropical note.",
            ],
            "reader_tips": [
                "Chill the mixing bowl and beaters in the freezer for 10 minutes before whipping the cream, cold equipment whips air in faster and holds stiffer peaks.",
                "Press a piece of plastic wrap directly onto the surface before the lid goes on, it keeps ice crystals from forming on top during the long freeze.",
            ],
            "storage_and_reheating": (
                "Keeps well frozen, tightly covered, for up to 2 months. Let sit "
                "at room temperature 5-10 minutes before scooping if it's been "
                "frozen solid."
            ),
            # nutrition_note intentionally omitted -- superseded by the live
            # nutrition block computed from nutrition_per_unit above.
            "faqs": [
                {
                    "question": "Do I need an ice cream maker for this?",
                    "answer": (
                        "No, this is a no-churn method. The whipped cream folded "
                        "in provides the airiness a machine would normally churn "
                        "in, so a freezer is the only equipment needed."
                    ),
                },
                {
                    "question": "Why is my no-churn ice cream icy instead of creamy?",
                    "answer": (
                        "Usually under-whipped cream (it needs to reach stiff "
                        "peaks) or a mango puree with too much water content. "
                        "Strain very juicy mango puree slightly before mixing it in."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": [],
            "category_link": None,
        },
    },
    {
        "slug": "amaretto-sour",
        "template_type": "recipe_or_dish",
        "title": "Amaretto Sour Recipe",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "A properly balanced amaretto sour with fresh lemon juice and an "
                "egg white for a silky foam top, not the cloying bar-mix "
                "version."
            ),
            "hero_image_query": "amaretto sour cocktail",
            "why_it_works": (
                "Fresh lemon juice cuts amaretto's sweetness, and a dry shake "
                "(no ice) whips the egg white into a stable foam before the wet "
                "shake chills the drink, skipping either step is why bar-mix "
                "versions turn out flat and one-note sweet."
            ),
            "prep_time_minutes": 5,
            "cook_time_minutes": 0,
            "total_time_minutes": 5,
            "servings": 1,
            "ingredients": [
                {"name": "amaretto", "base_qty": 2, "unit_us": "oz", "base_qty_metric": 60, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 110, "protein_g": 0, "carbs_g": 12.0, "fat_g": 0}},
                {"name": "fresh lemon juice", "base_qty": 0.75, "unit_us": "oz", "base_qty_metric": 22, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 7, "protein_g": 0.1, "carbs_g": 2.6, "fat_g": 0}},
                {"name": "simple syrup", "base_qty": 0.5, "unit_us": "oz", "base_qty_metric": 15, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 48, "protein_g": 0, "carbs_g": 12.5, "fat_g": 0}},
                {"name": "egg white", "base_qty": 1, "unit_us": "whole", "base_qty_metric": 1, "unit_metric": "whole", "hub_slug": None, "nutrition_per_unit": {"calories": 17, "protein_g": 3.6, "carbs_g": 0.2, "fat_g": 0}},
                {"name": "angostura bitters, for garnish", "base_qty": 2, "unit_us": "dashes", "base_qty_metric": 2, "unit_metric": "dashes", "hub_slug": None},
            ],
            "instructions": [
                "Add the amaretto, lemon juice, simple syrup, and egg white to a shaker.",
                "Dry shake (no ice) vigorously for 15-20 seconds to whip the egg white.",
                "Add ice and shake again for 15 seconds until well chilled.",
                "Strain into a rocks glass over fresh ice, or up into a coupe.",
                "Dot the foam with angostura bitters for garnish.",
            ],
            # Only one step_note -- reader_tips above already covers the dry
            # shake's foam-building role and letting the shaker rest before
            # straining, so this covers the remaining distinct point: why
            # there's a second shake at all.
            "step_notes": {
                2: "The second, wet shake is what chills and dilutes the drink to a drinkable strength; the foam is already built from the dry shake, but skipping this step leaves the cocktail warm and overly boozy-tasting.",
            },
            "tips_and_variations": [
                "Pasteurized egg whites (or the liquid egg white product sold in cartons) work fine and remove any raw-egg concern.",
                "No egg white on hand? The drink is still good without it, just less foamy on top.",
            ],
            "reader_tips": [
                "The dry shake (no ice) is what actually builds the foam, skipping straight to the wet shake with ice will still taste fine but won't foam properly no matter how hard you shake it.",
                "Let the shaker sit for a few seconds after the wet shake before straining, it gives the foam a moment to stabilize instead of collapsing as soon as it hits the glass.",
            ],
            "storage_and_reheating": (
                "Best made fresh and drunk right away, the whipped egg-white "
                "foam collapses within a few minutes and won't come back with "
                "re-shaking. If you need to prep ahead for a crowd, batch the "
                "amaretto, lemon juice, and simple syrup together and "
                "refrigerate up to a day, then add egg white and shake to "
                "order per drink."
            ),
            # nutrition_note intentionally omitted -- superseded by the live
            # nutrition block computed from nutrition_per_unit above.
            "faqs": [
                {
                    "question": "Is it safe to drink raw egg white in a cocktail?",
                    "answer": (
                        "The risk is low but not zero. Using pasteurized egg "
                        "whites (fresh-pasteurized eggs, or a carton of "
                        "pasteurized egg whites) removes the concern entirely if "
                        "you'd rather not use a raw egg."
                    ),
                },
                {
                    "question": "What can I use instead of egg white?",
                    "answer": (
                        "Aquafaba (the liquid from a can of chickpeas), about the "
                        "same amount as the egg white, is the standard vegan "
                        "substitute and whips into a similar foam."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": [],
            "category_link": None,
        },
    },
    {
        "slug": "chilean-sea-bass",
        "template_type": "recipe_or_dish",
        "title": "Chilean Sea Bass Recipe",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Pan-seared Chilean sea bass with a crisp skin and buttery, "
                "flaky center, a restaurant-style preparation that's simple "
                "enough for a weeknight."
            ),
            "hero_image_query": "pan seared chilean sea bass",
            "why_it_works": (
                "Chilean sea bass's high fat content makes it nearly impossible "
                "to overcook into dryness the way leaner white fish can, a hot "
                "pan and a hands-off sear are all it needs for crisp skin and a "
                "silky center."
            ),
            "prep_time_minutes": 10,
            "cook_time_minutes": 10,
            "total_time_minutes": 20,
            "servings": 2,
            # The lemon is squeezed over as a finishing garnish, not eaten
            # whole, so it's left without a nutrition_per_unit -- the actual
            # calories transferred are negligible either way.
            "ingredients": [
                {"name": "Chilean sea bass fillets, skin on", "base_qty": 2, "unit_us": "fillets (6 oz each)", "base_qty_metric": 340, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 357, "protein_g": 30.6, "carbs_g": 0, "fat_g": 25.5}},
                {"name": "salt", "base_qty": 0.5, "unit_us": "tsp", "base_qty_metric": 3, "unit_metric": "g", "hub_slug": None},
                {"name": "black pepper", "base_qty": 0.25, "unit_us": "tsp", "base_qty_metric": 0.5, "unit_metric": "g", "hub_slug": None},
                {"name": "neutral oil (avocado or grapeseed)", "base_qty": 1, "unit_us": "tbsp", "base_qty_metric": 15, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 120, "protein_g": 0, "carbs_g": 0, "fat_g": 14.0}},
                {"name": "unsalted butter", "base_qty": 2, "unit_us": "tbsp", "base_qty_metric": 28, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 102, "protein_g": 0.1, "carbs_g": 0, "fat_g": 11.5}},
                {"name": "lemon, halved", "base_qty": 1, "unit_us": "whole", "base_qty_metric": 1, "unit_metric": "whole", "hub_slug": None},
            ],
            "instructions": [
                "Pat the fillets very dry and season both sides with salt and pepper.",
                "Heat the oil in a skillet over medium-high heat until shimmering.",
                "Lay the fillets skin-side down and press gently for the first 30 seconds so the skin doesn't curl.",
                "Sear undisturbed for 4-5 minutes, until the skin is deeply golden and crisp.",
                "Flip, add the butter to the pan, and baste the fillets for 2-3 minutes until the fish flakes easily and reaches 130-135°F (54-57°C) internally.",
                "Squeeze fresh lemon over the top and serve immediately.",
            ],
            "step_notes": {
                0: "Drying the fillets thoroughly means the skin contacts hot oil right away instead of first steaming off surface moisture before it can start crisping.",
                2: "Pressing the fillet flat for the first moments keeps the whole skin surface in contact with the pan while it firms up; skip this and the edges curl away from the heat before the skin has set.",
                4: "Basting with butter cooks the delicate flesh through gently rather than continuing a hard sear, without drying out the side that's no longer directly on the hot pan.",
            },
            "tips_and_variations": [
                "Don't move the fish while the skin-side sear is happening, it releases from the pan on its own once properly crisped.",
                "Chilean sea bass is also sold as Patagonian toothfish, same fish, different market name.",
            ],
            "reader_tips": [
                "Score the skin in a few shallow slashes before cooking, it helps the fillet lie flat instead of curling as the skin contracts in the hot pan.",
                "Spoon a little of the pan's butter-lemon sauce over the fish just before serving, it does more for flavor than adding extra butter to the pan itself.",
            ],
            "storage_and_reheating": (
                "Best eaten immediately. Leftovers keep a day refrigerated; reheat "
                "gently to avoid drying out the delicate flesh."
            ),
            # nutrition_note intentionally omitted -- superseded by the live
            # nutrition block computed from nutrition_per_unit above.
            "faqs": [
                {
                    "question": "Why is Chilean sea bass so expensive?",
                    "answer": (
                        "It's a slow-growing, deep-water fish with tightly "
                        "regulated catch limits, which keeps supply low relative "
                        "to demand, not a marketing markup on an otherwise "
                        "common fish."
                    ),
                },
                {
                    "question": "How do I know when it's done without a thermometer?",
                    "answer": (
                        "The flesh turns from translucent to opaque and flakes "
                        "easily with a fork when done. Because of its high fat "
                        "content, it stays moist even slightly past done, so err "
                        "toward pulling it a bit early."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": [],
            "category_link": None,
        },
    },
    {
        "slug": "arroz-con-leche",
        "template_type": "recipe_or_dish",
        "title": "Arroz con Leche Recipe",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Classic arroz con leche (Mexican rice pudding) simmered slowly "
                "with cinnamon and milk until creamy, a traditional recipe, "
                "not a shortcut version."
            ),
            "hero_image_query": "arroz con leche rice pudding",
            "why_it_works": (
                "Simmering the rice low and slow in milk, rather than boiling it "
                "hard, lets the starch release gradually so the pudding thickens "
                "naturally without the rice turning gluey."
            ),
            "prep_time_minutes": 5,
            "cook_time_minutes": 40,
            "total_time_minutes": 45,
            "servings": 6,
            "ingredients": [
                {"name": "white rice", "base_qty": 1, "unit_us": "cup", "base_qty_metric": 185, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 675, "protein_g": 12.5, "carbs_g": 148.0, "fat_g": 1.0}},
                {"name": "water", "base_qty": 2, "unit_us": "cups", "base_qty_metric": 480, "unit_metric": "ml", "hub_slug": None},
                {"name": "cinnamon stick", "base_qty": 1, "unit_us": "whole", "base_qty_metric": 1, "unit_metric": "whole", "hub_slug": None},
                {"name": "whole milk", "base_qty": 4, "unit_us": "cups", "base_qty_metric": 960, "unit_metric": "ml", "hub_slug": None, "nutrition_per_unit": {"calories": 149, "protein_g": 7.7, "carbs_g": 11.7, "fat_g": 8.0}},
                {"name": "sweetened condensed milk", "base_qty": 0.5, "unit_us": "cup", "base_qty_metric": 150, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 982, "protein_g": 24.2, "carbs_g": 166.5, "fat_g": 26.6}},
                {"name": "granulated sugar", "base_qty": 0.25, "unit_us": "cup", "base_qty_metric": 50, "unit_metric": "g", "hub_slug": None, "nutrition_per_unit": {"calories": 774, "protein_g": 0, "carbs_g": 200.0, "fat_g": 0}},
                {"name": "ground cinnamon, for serving", "base_qty": 1, "unit_us": "to taste", "base_qty_metric": 1, "unit_metric": "to taste", "hub_slug": None},
            ],
            "instructions": [
                "Combine the rice, water, and cinnamon stick in a saucepan and bring to a boil.",
                "Reduce heat to low, cover, and simmer for 15 minutes, until the water is absorbed.",
                "Stir in the whole milk, sweetened condensed milk, and sugar.",
                "Simmer uncovered over low heat, stirring often, for 20-25 minutes, until thickened and creamy.",
                "Remove the cinnamon stick and let cool slightly, it continues thickening as it cools.",
                "Serve warm or chilled, dusted with ground cinnamon.",
            ],
            # Steps 4/5's own insight (it keeps thickening off the heat) is
            # already reader_tips above, so these two cover different ground:
            # the choice of liquid at each stage.
            "step_notes": {
                1: "Cooking the rice in water first, not milk, lets it fully hydrate and soften without milk's proteins and sugars slowing that down or scorching before the rice is tender.",
                3: "Simmering uncovered once the milk goes in lets excess liquid evaporate off, which is what actually thickens the pudding, covering it here would trap the steam and keep it thin.",
            },
            "tips_and_variations": [
                "Stir often once the milk goes in, rice pudding scorches on the bottom of the pot easily if left unstirred.",
                "A strip of orange or lime zest simmered along with the cinnamon stick adds a traditional citrus note.",
            ],
            "reader_tips": [
                "Use a heavy-bottomed pot, a thin one heats unevenly and makes scorching on the bottom much more likely during the long simmer.",
                "It thickens quite a bit as it cools, so pull it off the heat while it still looks slightly thinner than you want the final texture to be.",
            ],
            "storage_and_reheating": (
                "Refrigerate up to 5 days. It thickens further when cold, stir "
                "in a splash of milk when reheating or serving cold to loosen it "
                "back up."
            ),
            # nutrition_note intentionally omitted -- superseded by the live
            # nutrition block computed from nutrition_per_unit above.
            "faqs": [
                {
                    "question": "Can I make arroz con leche ahead of time?",
                    "answer": (
                        "Yes, it keeps well refrigerated for several days and is "
                        "traditionally served both warm and cold, so making it a "
                        "day ahead is common, not a compromise."
                    ),
                },
                {
                    "question": "Why did my rice pudding turn out too thick or too thin?",
                    "answer": (
                        "It thickens significantly as it cools, so it should look "
                        "slightly looser than you want it in the final result "
                        "while it's still on the stove. If it's too thick after "
                        "cooling, stir in warm milk a splash at a time."
                    ),
                },
            ],
            "technique_link": None,
            "related_recipe_slugs": [],
            "category_link": {"title": "Mexican Recipes", "slug": "mexican-recipes"},
        },
    },
    {
        "slug": "oysters",
        "template_type": "ingredient_hub",
        "title": "Oysters",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "What to look for when buying oysters, how to store and shuck "
                "them safely, and how they're typically served."
            ),
            "hero_image_query": "fresh oysters on ice",
            "description": (
                "Oysters are bivalve mollusks harvested from coastal and "
                "estuarine waters, eaten raw on the half shell, grilled, fried, "
                "or baked. Flavor and texture vary significantly by region and "
                "species, briny and firm from cold Atlantic waters, milder and "
                "creamier from warmer Gulf waters."
            ),
            "substitutes": [
                {"name": "Clams", "ratio": "1:1 by count", "note": "Similar brine and texture raw or cooked, though generally less plump.", "ratio_multiplier": 1.0},
                {"name": "Mussels", "ratio": "1:1 by count", "note": "Works for cooked preparations (grilled, baked) but is a poor stand-in raw, different texture and flavor.", "ratio_multiplier": 1.0},
            ],
            "substitute_page_slug": None,
            "storage": (
                "Store live oysters in the refrigerator, cup-side down, covered "
                "with a damp cloth (never sealed in an airtight bag or submerged "
                "in fresh water, both of which suffocate them). Use within 5-7 "
                "days of purchase, and discard any that are open and don't close "
                "when tapped."
            ),
            "uses": (
                "Served raw on the half shell with mignonette or lemon, grilled "
                "with garlic butter, fried for po'boys, or baked (Oysters "
                "Rockefeller). Always cook thoroughly if not eating raw, raw "
                "oysters carry a real risk for people who are immunocompromised, "
                "pregnant, or have liver conditions."
            ),
            "nutrition_note": (
                "A significant source of zinc, vitamin B12, and iron, and "
                "relatively low in calories, roughly 50-70 calories per "
                "half-dozen raw oysters, depending on size."
            ),
            "buying_tips": (
                "Live oysters should be tightly closed, or close when "
                "tapped, discard any that stay open. Buy from a source "
                "with high turnover and keep them on ice, cup-side down, "
                "until shucking."
            ),
            "pairing_suggestions": (
                "Classic raw-bar pairings are a simple mignonette "
                "(shallot, vinegar, cracked pepper), a squeeze of lemon, "
                "or hot sauce, all meant to accent, not mask, the "
                "oyster's own brine."
            ),
            "variety_notes": (
                "Flavor and size vary significantly by growing region, "
                "East Coast oysters (like Blue Points) tend to be brinier "
                "and firmer, while Pacific varieties (like Kumamotos) run "
                "sweeter and smaller. Neither is a straight substitute for "
                "a recipe built around the other's size."
            ),
            "faqs": [
                {
                    "question": "How can I tell if an oyster is bad before opening it?",
                    "answer": (
                        "A live oyster's shell should be tightly closed, or close "
                        "when tapped. Discard any that are open and stay open, "
                        "cracked, or smell strongly of anything other than clean "
                        "brine."
                    ),
                },
                {
                    "question": "Is it safe to eat oysters raw?",
                    "answer": (
                        "For most healthy adults, yes, from a reputable source "
                        "with proper cold-chain handling. People who are pregnant, "
                        "immunocompromised, or have liver disease are advised to "
                        "eat oysters only fully cooked."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_ingredient_slugs": [],
        },
    },
    {
        "slug": "kielbasa",
        "template_type": "ingredient_hub",
        "title": "Kielbasa",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "What kielbasa is, how it differs from other sausages, storage "
                "tips, and the best ways to cook it."
            ),
            "hero_image_query": "sliced kielbasa sausage",
            "description": (
                "Kielbasa is a Polish smoked sausage, most commonly made from "
                "pork (sometimes blended with beef), seasoned with garlic and "
                "marjoram. In the US it's most often sold fully cooked and "
                "smoked, ready to slice and pan-fry, grill, or add to soups and "
                "casseroles."
            ),
            "substitutes": [
                {"name": "Smoked andouille sausage", "ratio": "1:1", "note": "Spicier and more heavily smoked, but a close textural match.", "ratio_multiplier": 1.0},
                {"name": "Smoked bratwurst", "ratio": "1:1", "note": "Milder flavor than kielbasa; works well in soups and skillet dishes.", "ratio_multiplier": 1.0},
            ],
            "substitute_page_slug": None,
            "storage": (
                "Unopened, vacuum-sealed kielbasa keeps in the refrigerator until "
                "its printed date. Once opened, use within a week, or freeze "
                "whole or sliced for up to 3 months."
            ),
            "uses": (
                "Since it's already fully cooked, kielbasa mainly needs "
                "reheating and browning: slice and pan-sear, grill whole links, "
                "or simmer sliced into soups, beans, and skillet hashes."
            ),
            "nutrition_note": (
                "High in protein and sodium; a 2-oz serving typically runs "
                "150-190 calories and 500-600mg sodium, so it's often used as a "
                "flavor component rather than the sole protein in a dish."
            ),
            "buying_tips": (
                "Check the label for 'fully cooked' vs 'fresh', most US "
                "grocery kielbasa is the former and only needs reheating, "
                "while fresh kielbasa needs to be cooked through like any "
                "raw sausage."
            ),
            "pairing_suggestions": (
                "Pairs well with sauerkraut, mustard, cabbage, and "
                "potatoes, the classic Eastern European combinations, and "
                "holds up well simmered into bean or lentil soups."
            ),
            "variety_notes": (
                "Fully cooked, smoked kielbasa (the common US supermarket "
                "version) is ready to slice and pan-sear. Fresh (raw) "
                "kielbasa, more common at Polish delis, needs to be cooked "
                "through first like any raw sausage, check the package "
                "before assuming either."
            ),
            "faqs": [
                {
                    "question": "Is kielbasa already cooked, or does it need to be cooked through?",
                    "answer": (
                        "Most kielbasa sold in US supermarkets is fully cooked and "
                        "smoked, it just needs reheating and browning, not "
                        "cooking to a safe internal temperature the way raw "
                        "sausage does. Check the package, since fresh, uncooked "
                        "kielbasa does exist and needs to reach 160°F (71°C)."
                    ),
                },
                {
                    "question": "What's the difference between kielbasa and Polish sausage?",
                    "answer": (
                        "None, \"kielbasa\" is simply the Polish word for "
                        "sausage, and in English it's come to specifically mean "
                        "the smoked Polish sausage most commonly found in stores, "
                        "so the two names refer to the same product."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_ingredient_slugs": [],
        },
    },
    {
        "slug": "creme-fraiche",
        "template_type": "ingredient_hub",
        "title": "Crème Fraîche",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "What crème fraîche is, how it differs from sour cream, storage "
                "tips, and how to use it in both cooking and baking."
            ),
            "hero_image_query": "creme fraiche in a bowl",
            "description": (
                "Crème fraîche is a thick, cultured cream, similar to sour cream "
                "but higher in fat and milder, less tangy in flavor. Its higher "
                "fat content also means it doesn't curdle when boiled or "
                "simmered, unlike sour cream, which makes it useful in hot sauces."
            ),
            "substitutes": [
                {"name": "Sour cream", "ratio": "1:1", "note": "Tangier and lower-fat; fine cold or as a finishing swirl, but can split if boiled.", "ratio_multiplier": 1.0},
                {"name": "Mascarpone thinned with a little cream", "ratio": "1:1", "note": "Milder and richer, closer to crème fraîche's fat content.", "ratio_multiplier": 1.0},
            ],
            "substitute_page_slug": "creme-fraiche-substitute",
            "storage": (
                "Refrigerate and use within the printed date, generally 1-2 "
                "weeks once opened. It doesn't freeze well, the texture "
                "separates and turns grainy once thawed."
            ),
            "uses": (
                "Stirred into pan sauces and soups (it won't curdle from heat "
                "the way sour cream can), dolloped over desserts or savory "
                "crepes, or whipped lightly to top fruit, it whips to soft "
                "peaks with less added sugar needed than heavy cream."
            ),
            "nutrition_note": (
                "Higher in fat than sour cream, typically 28-45% fat depending "
                "on the brand, so it's more calorie-dense, roughly 50-55 "
                "calories per tablespoon."
            ),
            "buying_tips": (
                "Check the expiration date and look for a thick, "
                "spoonable texture through the container lid, it "
                "shouldn't look separated or watery."
            ),
            "pairing_suggestions": (
                "Good with both sweet and savory: dolloped over fruit or "
                "a warm dessert, or stirred into pan sauces and soups "
                "where sour cream would curdle."
            ),
            "faqs": [
                {
                    "question": "Can I make crème fraîche at home?",
                    "answer": (
                        "Yes, stir 1 tablespoon of buttermilk into 1 cup of "
                        "heavy cream, cover loosely, and let sit at room "
                        "temperature for 12-24 hours until thickened, then "
                        "refrigerate."
                    ),
                },
                {
                    "question": "Why doesn't crème fraîche curdle when heated, unlike sour cream?",
                    "answer": (
                        "Its higher fat content stabilizes the proteins against "
                        "the heat that would otherwise cause them to seize and "
                        "curdle, which is exactly why it's preferred for finishing "
                        "hot sauces and soups."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_ingredient_slugs": ["gruyere-cheese", "chives"],
        },
    },
    {
        "slug": "gruyere-cheese",
        "template_type": "ingredient_hub",
        "title": "Gruyère Cheese",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "What gruyère cheese is, how it melts and tastes, storage tips, "
                "and the best substitutes when it's not available."
            ),
            "hero_image_query": "gruyere cheese wedge",
            "description": (
                "Gruyère is a hard, Swiss cow's-milk cheese, aged anywhere from "
                "5 months to over a year. Younger gruyère is mild and nutty; "
                "longer-aged gruyère turns more intense, slightly grainy, and "
                "savory. It melts exceptionally smoothly, which is why it's the "
                "classic choice for fondue and French onion soup."
            ),
            # nutrition_per_unit here uses the same "per 1 cup, USDA-comparable
            # estimate" convention as the gruyère ingredient it substitutes for
            # (see chicken-broccoli-rice-casserole) -- swapping to one of these
            # on that recipe's page should visibly shift the live nutrition
            # block, not just the ingredient name and quantity.
            "substitutes": [
                {"name": "Comté", "ratio": "1:1", "note": "Very close in flavor and melting behavior; the classic French cousin to Swiss gruyère.", "ratio_multiplier": 1.0, "nutrition_per_unit": {"calories": 440, "protein_g": 30.0, "carbs_g": 1.0, "fat_g": 34.0}},
                {"name": "Swiss Emmental", "ratio": "1:1", "note": "Milder and sweeter, with the characteristic large holes; melts similarly well.", "ratio_multiplier": 1.0, "nutrition_per_unit": {"calories": 397, "protein_g": 28.0, "carbs_g": 3.4, "fat_g": 30.0}},
                {"name": "Fontina", "ratio": "1:1", "note": "Softer and buttery rather than nutty, but melts just as smoothly.", "ratio_multiplier": 1.0, "nutrition_per_unit": {"calories": 397, "protein_g": 26.0, "carbs_g": 1.5, "fat_g": 31.0}},
            ],
            "substitute_page_slug": "gruyere-cheese-substitute",
            "storage": (
                "Wrap tightly in wax or parchment paper (not plastic, which "
                "traps moisture and speeds mold growth), then loosely in "
                "plastic. Refrigerate and use within 3-4 weeks of opening; it "
                "also freezes reasonably well for cooking use, though the "
                "texture suffers slightly."
            ),
            "uses": (
                "Melts into fondue, French onion soup, croque monsieur, and "
                "gratins; grated over casseroles for a golden, bubbling crust; "
                "or sliced for a cheese board alongside fruit and nuts."
            ),
            "nutrition_note": (
                "A rich source of calcium and protein; approximately 110-120 "
                "calories and 9g fat per 1-oz serving, similar to most hard "
                "cheeses."
            ),
            "buying_tips": (
                "Buy a wedge cut from a wheel rather than pre-shredded "
                "when possible, pre-shredded cheese is coated in "
                "anti-caking starch that keeps it from melting as "
                "smoothly."
            ),
            "pairing_suggestions": (
                "A natural match for white wine, crusty bread, and cured "
                "meats on a cheese board, and for onions and nutmeg in "
                "cooked dishes like French onion soup and gratins."
            ),
            "faqs": [
                {
                    "question": "Why is my gruyère grainy instead of smooth?",
                    "answer": (
                        "That's usually a sign of longer aging, not a flaw, "
                        "aged gruyère develops small, crunchy tyrosine crystals "
                        "similar to aged cheddar or parmesan, which many people "
                        "specifically seek out."
                    ),
                },
                {
                    "question": "Is gruyère the same as Swiss cheese?",
                    "answer": (
                        "Gruyère is one specific type of Swiss cheese, made in a "
                        "particular region of Switzerland (and nearby France) "
                        "under specific rules. \"Swiss cheese\" in US supermarkets "
                        "usually refers to a milder, generic Emmental-style "
                        "cheese, not gruyère specifically."
                    ),
                },
            ],
            "recipe_slugs": ["chicken-broccoli-rice-casserole"],
            "related_ingredient_slugs": ["creme-fraiche", "pecorino"],
        },
    },
    {
        "slug": "balsamic-vinegar",
        "template_type": "ingredient_hub",
        "title": "Balsamic Vinegar",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "What balsamic vinegar is, how to tell real aged balsamic from "
                "supermarket versions, storage tips, and how to use it."
            ),
            "hero_image_query": "balsamic vinegar bottle",
            "description": (
                "Balsamic vinegar is made from reduced, fermented grape must "
                "(unfermented grape juice), giving it a dark color and a "
                "sweet-tart flavor unlike wine-based vinegars. Traditional "
                "balsamic from Modena or Reggio Emilia, Italy, is aged for "
                "years in wooden barrels and is thick, complex, and expensive; "
                "most supermarket balsamic is a younger, thinner commercial "
                "version, often with added caramel color and thickeners."
            ),
            "substitutes": [
                {"name": "Red wine vinegar + a little sugar or honey", "ratio": "1:1, plus sweetener to taste", "note": "Approximates the sweet-tart balance without balsamic's specific depth.", "ratio_multiplier": 1.0},
                {"name": "Sherry vinegar", "ratio": "1:1", "note": "Different flavor profile (nuttier, less sweet) but works in most savory applications.", "ratio_multiplier": 1.0},
            ],
            "substitute_page_slug": None,
            "storage": (
                "Store tightly capped in a cool, dark pantry, it doesn't need "
                "refrigeration. Quality balsamic keeps well for years due to "
                "its acidity and sugar content."
            ),
            "uses": (
                "Whisked into vinaigrettes, reduced into a syrupy glaze for "
                "drizzling over caprese salad or grilled meats, or splashed into "
                "pan sauces at the end of cooking (added early, its flavor "
                "cooks off)."
            ),
            "nutrition_note": (
                "Low in calories at typical serving sizes, about 14 calories "
                "per tablespoon, mostly from natural grape sugars."
            ),
            "buying_tips": (
                "For everyday cooking, a mid-priced bottle labeled "
                "'balsamic vinegar of Modena' (IGP) is the right call, "
                "save the true aged Tradizionale for finishing, not "
                "cooking, since heat destroys what makes it special."
            ),
            "pairing_suggestions": (
                "Classic with fresh mozzarella and tomatoes (caprese), "
                "strawberries, and grilled or roasted vegetables, its "
                "sweetness balances rich or bitter flavors like blue "
                "cheese and dark leafy greens."
            ),
            "variety_notes": (
                "Most bottles labeled 'balsamic vinegar of Modena' are a "
                "commercial blend of wine vinegar and grape must, fine for "
                "everyday cooking. True Aceto Balsamico Tradizionale "
                "(aged 12+ years, sold in a small, expensive bottle with a "
                "DOP seal) is a completely different, syrupy product "
                "meant for finishing dishes, not cooking with."
            ),
            "faqs": [
                {
                    "question": "How do I know if I'm buying real balsamic vinegar?",
                    "answer": (
                        "True traditional balsamic (Aceto Balsamico Tradizionale) "
                        "carries a DOP certification and is sold in small, "
                        "expensive bottles. Most supermarket balsamic is a "
                        "commercial-grade product, still genuinely useful for "
                        "everyday cooking, just not the aged traditional version."
                    ),
                },
                {
                    "question": "How do I make a balsamic glaze?",
                    "answer": (
                        "Simmer balsamic vinegar in a small saucepan over "
                        "medium-low heat until it reduces by about half and "
                        "coats the back of a spoon, roughly 10-15 minutes. It "
                        "thickens further as it cools."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_ingredient_slugs": ["feta-cheese"],
        },
    },
    {
        "slug": "feta-cheese",
        "template_type": "ingredient_hub",
        "title": "Feta Cheese",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "What feta cheese is, how to store it properly in brine, and "
                "the best substitutes for its salty, tangy flavor."
            ),
            "hero_image_query": "feta cheese block",
            "description": (
                "Feta is a brined, crumbly white cheese, traditionally made in "
                "Greece from sheep's milk (or a sheep-and-goat blend). It's "
                "tangy, salty, and firm enough to crumble or cube rather than "
                "melt smoothly."
            ),
            "substitutes": [
                {"name": "Cotija cheese", "ratio": "1:1", "note": "Saltier and drier, doesn't crumble quite as creamily, but a close flavor match.", "ratio_multiplier": 1.0},
                {"name": "Goat cheese", "ratio": "1:1", "note": "Softer and tangier in a different way; works well in salads.", "ratio_multiplier": 1.0},
            ],
            "substitute_page_slug": None,
            "storage": (
                "Keep feta submerged in its brine (or a fresh saltwater brine, "
                "if the original was drained) in the refrigerator, it dries "
                "out and turns crumbly-hard quickly once exposed to air. Stored "
                "in brine, it keeps for several weeks."
            ),
            "uses": (
                "Crumbled over salads, watermelon, and roasted vegetables; "
                "baked whole in a block with tomatoes and olive oil for a "
                "quick pasta sauce; or layered into spanakopita and other "
                "phyllo pastries."
            ),
            "nutrition_note": (
                "Lower in fat than many hard cheeses but notably high in "
                "sodium due to the brine; approximately 75 calories and 320mg "
                "sodium per 1-oz serving."
            ),
            "buying_tips": (
                "Buy feta stored in brine (a block in liquid) rather than "
                "pre-crumbled and dry-packed, it stays fresher longer and "
                "has better texture. Taste before buying if possible, "
                "saltiness and tang vary a lot by brand."
            ),
            "pairing_suggestions": (
                "Pairs well with watermelon, olives, cucumber, and olive "
                "oil in salads, and with honey and nuts as a simple "
                "appetizer, its saltiness balances sweet and bright "
                "flavors especially well."
            ),
            "variety_notes": (
                "Traditional Greek feta (look for a PDO label) is made "
                "from sheep's milk or a sheep-and-goat blend and has a "
                "tangier, more complex flavor. Feta made purely from "
                "cow's milk, common in US supermarkets, is milder and "
                "less crumbly."
            ),
            "faqs": [
                {
                    "question": "Why is my feta so salty?",
                    "answer": (
                        "It's cured and stored in a salt brine, which is "
                        "essential to its texture and shelf life. Rinsing it "
                        "briefly under cold water before using mellows the "
                        "saltiness if it's too much for a dish."
                    ),
                },
                {
                    "question": "Can feta cheese be frozen?",
                    "answer": (
                        "It can, but the texture turns noticeably more crumbly "
                        "and watery after thawing, fine for cooking into baked "
                        "dishes, but not ideal for serving raw or in a salad."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_ingredient_slugs": ["balsamic-vinegar"],
        },
    },
    {
        "slug": "corn-starch",
        "template_type": "ingredient_hub",
        "title": "Cornstarch",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "What cornstarch is used for, how to make a proper slurry, "
                "storage tips, and the best substitutes for thickening."
            ),
            "hero_image_query": "cornstarch in a bowl",
            "description": (
                "Cornstarch is a fine, flavorless powder milled from the "
                "endosperm of corn kernels, used almost entirely as a "
                "thickening agent. It thickens with about twice the power of "
                "flour and sets into a clear, glossy gel rather than flour's "
                "cloudier, more opaque thickening."
            ),
            "substitutes": [
                {"name": "All-purpose flour", "ratio": "Use 2x the amount of cornstarch called for", "note": "Thickens cloudier and needs longer cooking to lose a raw-flour taste.", "ratio_multiplier": 2.0},
                {"name": "Arrowroot powder", "ratio": "1:1", "note": "Similar clear, glossy thickening; holds up better than cornstarch in acidic or frozen dishes.", "ratio_multiplier": 1.0},
                {"name": "Potato starch", "ratio": "1:1", "note": "Similar thickening power; add near the end of cooking since it breaks down if boiled too long.", "ratio_multiplier": 1.0},
            ],
            "substitute_page_slug": None,
            "storage": (
                "Keep in a sealed container in a cool, dry pantry, it has an "
                "essentially indefinite shelf life as long as it stays dry, "
                "since moisture (not time) is what degrades it."
            ),
            "uses": (
                "Mixed with cold liquid into a slurry before adding to a hot "
                "sauce or soup (adding it dry causes clumping), used to coat "
                "meat before frying for extra crispness, or blended into baked "
                "goods in small amounts for a more tender crumb."
            ),
            "nutrition_note": (
                "Essentially pure starch, about 30 calories per tablespoon, "
                "with negligible protein, fat, or fiber."
            ),
            "buying_tips": (
                "Any plain cornstarch works the same for thickening, "
                "there is no meaningful quality tier to shop for, just "
                "check that it is plain starch with no added seasoning."
            ),
            "faqs": [
                {
                    "question": "Why did my cornstarch-thickened sauce turn out lumpy?",
                    "answer": (
                        "Cornstarch added directly to a hot liquid clumps almost "
                        "instantly. Always mix it with a small amount of cold "
                        "liquid into a smooth slurry first, then whisk that into "
                        "the hot liquid."
                    ),
                },
                {
                    "question": "Can I substitute cornstarch for flour in baking?",
                    "answer": (
                        "Only in small amounts, mixed with flour, not as a full "
                        "1:1 replacement, a spoonful swapped in for flour in "
                        "cookies or cakes can make the crumb more tender, but "
                        "cornstarch has none of flour's gluten structure."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_ingredient_slugs": ["bread-flour"],
        },
    },
    {
        "slug": "bread-flour",
        "template_type": "ingredient_hub",
        "title": "Bread Flour",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "What makes bread flour different from all-purpose flour, when "
                "to use it, storage tips, and how to substitute in a pinch."
            ),
            "hero_image_query": "bread flour bag",
            "description": (
                "Bread flour is milled from hard wheat with a higher protein "
                "content (typically 12-14%) than all-purpose flour (10-12%). "
                "That extra protein develops more gluten, giving yeasted bread "
                "a chewier crumb and better structure to trap the gas produced "
                "during rising."
            ),
            "substitutes": [
                {"name": "All-purpose flour + vital wheat gluten", "ratio": "1 cup flour + 1 tsp vital wheat gluten per cup of bread flour called for", "note": "Approximates bread flour's protein content reasonably closely.", "ratio_multiplier": None},
                {"name": "Plain all-purpose flour", "ratio": "1:1", "note": "Works fine for most home baking; the loaf will be slightly softer and less chewy.", "ratio_multiplier": 1.0},
            ],
            "substitute_page_slug": None,
            "storage": (
                "Store in an airtight container in a cool, dry pantry for up to "
                "a year, or refrigerate/freeze for longer storage, flour's "
                "natural oils can turn rancid over time, especially in warm, "
                "humid conditions."
            ),
            "uses": (
                "Best for yeasted breads, pizza dough, and bagels, where a "
                "strong gluten network is wanted. Less ideal for tender baked "
                "goods like cakes and pastries, where too much gluten "
                "development makes for a tough result."
            ),
            "nutrition_note": (
                "Similar calorie content to all-purpose flour, about 100-110 "
                "calories per ¼ cup, with slightly more protein per serving "
                "due to the higher-protein wheat it's milled from."
            ),
            "buying_tips": (
                "Check the protein content on the nutrition label if "
                "it is listed, bread flour should run 12-14%, noticeably "
                "higher than all-purpose (10-12%)."
            ),
            "faqs": [
                {
                    "question": "Can I use bread flour for cookies or cakes?",
                    "answer": (
                        "You can, but the higher gluten content tends to make "
                        "cookies and cakes chewier and denser rather than tender, "
                        "fine for a chewier cookie on purpose, less ideal for "
                        "a light cake."
                    ),
                },
                {
                    "question": "Does bread flour make that much of a difference in homemade bread?",
                    "answer": (
                        "Yes, noticeably, the extra gluten gives the dough more "
                        "strength to rise tall and hold an open, chewy crumb, "
                        "which is why most dedicated bread recipes call for it "
                        "specifically rather than all-purpose flour."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_ingredient_slugs": ["corn-starch"],
        },
    },
    {
        "slug": "pecorino",
        "template_type": "ingredient_hub",
        "title": "Pecorino Romano",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "What pecorino romano is, how it differs from parmesan, storage "
                "tips, and how to use its sharp, salty flavor."
            ),
            "hero_image_query": "pecorino romano wedge",
            "description": (
                "Pecorino Romano is a hard, salty Italian cheese made from "
                "sheep's milk (\"pecorino\" comes from pecora, Italian for "
                "sheep). It's sharper and saltier than parmesan, which is made "
                "from cow's milk, and is the traditional cheese in Roman pasta "
                "dishes like cacio e pepe and carbonara."
            ),
            "substitutes": [
                {"name": "Parmigiano-Reggiano", "ratio": "1:1", "note": "Milder and less salty, may want to add a bit more salt to the dish to compensate.", "ratio_multiplier": 1.0},
                {"name": "Grana Padano", "ratio": "1:1", "note": "Similar to parmesan in flavor; a milder substitute than pecorino.", "ratio_multiplier": 1.0},
            ],
            "substitute_page_slug": None,
            "storage": (
                "Wrap tightly in wax or parchment paper, then loosely in "
                "plastic, and refrigerate. A whole or large wedge keeps for "
                "several months this way; grated pecorino should be used "
                "within a couple of weeks for best flavor."
            ),
            "uses": (
                "Grated into cacio e pepe, carbonara, and amatriciana, the "
                "traditional Roman pastas, or shaved over salads and roasted "
                "vegetables for a sharp, salty finish."
            ),
            "nutrition_note": (
                "Higher in sodium than most cow's-milk hard cheeses due to its "
                "curing process; approximately 110 calories and 340mg sodium "
                "per 1-oz serving."
            ),
            "buying_tips": (
                "Buy it in a wedge and grate it yourself right before "
                "using, pre-grated pecorino loses its sharp aroma fast "
                "and often contains anti-caking additives."
            ),
            "pairing_suggestions": (
                "The traditional partner for black pepper and guanciale "
                "in Roman pastas, and a sharp, salty finish shaved over "
                "roasted vegetables or a simple green salad."
            ),
            "variety_notes": (
                "Pecorino Romano is the sharpest and saltiest of the "
                "pecorino family. Pecorino Toscano and other regional "
                "pecorinos are aged less and taste milder, closer to a "
                "firm, nutty table cheese than a grating cheese."
            ),
            "faqs": [
                {
                    "question": "Can I use parmesan instead of pecorino in carbonara?",
                    "answer": (
                        "Yes, and many recipes outside Italy do, it's milder "
                        "and less salty than pecorino, so the dish will taste "
                        "noticeably gentler. Purists consider pecorino essential "
                        "to a traditional Roman carbonara, but parmesan makes a "
                        "perfectly good dish."
                    ),
                },
                {
                    "question": "Why is pecorino so much saltier than parmesan?",
                    "answer": (
                        "Sheep's milk itself is naturally different from cow's "
                        "milk, and pecorino's traditional production and aging "
                        "process further concentrates its salt and sharpness "
                        "compared to parmesan's milder cow's-milk profile."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_ingredient_slugs": ["gruyere-cheese"],
        },
    },
    {
        "slug": "celtic-salt",
        "template_type": "ingredient_hub",
        "title": "Celtic Salt",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "What Celtic salt is, how it differs from table and kosher "
                "salt, and how to use its coarser, moister crystals."
            ),
            "hero_image_query": "celtic sea salt",
            "description": (
                "Celtic salt (sel gris) is an unrefined, grayish sea salt "
                "harvested from coastal salt marshes in Brittany, France, "
                "traditionally raked by hand. Its natural moisture content and "
                "trace minerals give it a slightly damp texture and a milder, "
                "more rounded flavor than refined table salt."
            ),
            "substitutes": [
                {"name": "Kosher salt", "ratio": "Use slightly more by volume", "note": "Kosher salt's larger, drier flakes are less dense, so measure by weight if precision matters.", "ratio_multiplier": None},
                {"name": "Other coarse sea salt", "ratio": "1:1 by volume", "note": "A reasonable stand-in, though it won't carry Celtic salt's specific mineral content.", "ratio_multiplier": 1.0},
            ],
            "substitute_page_slug": None,
            "storage": (
                "Store in a non-metal container (its moisture content can "
                "corrode metal lids over time) in a cool, dry place. Its "
                "natural moisture means it can clump, this is normal, not "
                "spoilage."
            ),
            "uses": (
                "Best as a finishing salt, sprinkled over roasted vegetables, "
                "grilled meats, or caramel, where its texture and mineral "
                "flavor are noticeable, rather than dissolved into a large pot "
                "of cooking water where the distinction is lost."
            ),
            "nutrition_note": (
                "Nutritionally similar to other salts, sodium is sodium, "
                "though it contains trace minerals like magnesium and potassium "
                "in amounts too small to be nutritionally significant."
            ),
            "buying_tips": (
                "Look for a grayish color and slightly damp texture, "
                "very white, bone-dry salt sold as 'Celtic salt' may be "
                "a lower-quality imitation rather than the real "
                "hand-harvested product."
            ),
            "faqs": [
                {
                    "question": "Is Celtic salt healthier than regular table salt?",
                    "answer": (
                        "Not meaningfully, the trace minerals it contains are "
                        "in amounts far too small to provide real nutritional "
                        "benefit. Any health difference from reducing refined "
                        "table salt intake would come from moderation, not from "
                        "switching salt types."
                    ),
                },
                {
                    "question": "Can I substitute Celtic salt 1:1 for table salt in a recipe?",
                    "answer": (
                        "Not by volume, its coarser, moister crystals are less "
                        "dense than fine table salt, so a recipe calling for "
                        "table salt will need more Celtic salt by volume (or the "
                        "same amount by weight) to taste equally salty."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_ingredient_slugs": [],
        },
    },
    {
        "slug": "how-to-cut-a-watermelon",
        "template_type": "howto_technique",
        "title": "How to Cut a Watermelon",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "The fastest, cleanest way to cut a watermelon into cubes, "
                "wedges, or sticks without a mess."
            ),
            "hero_image_query": "cutting a watermelon into cubes",
            "intro": (
                "A whole watermelon is awkward, and genuinely risky, to "
                "cut without a plan, its round shape rolls under the "
                "knife the moment you apply pressure. Squaring it off "
                "first turns a wobbly job into a fast, controlled one, "
                "however you want the pieces cut."
            ),
            "steps": [
                "Wash the outside of the watermelon and pat dry.",
                "Slice off both ends so the melon sits flat and stable on the cutting board.",
                "Stand the melon on one flat end and slice downward, following the curve, to remove the rind in strips.",
                "Once the rind is fully removed, slice the melon into 1-inch-thick rounds.",
                "Stack the rounds and cut into strips, then rotate and cut again to form cubes.",
                "Alternatively, for wedges: halve the melon lengthwise, then cut each half into wedges without removing the rind first.",
            ],
            "common_mistakes": [
                "Skipping the flat-end cut: a rounded, unstable melon is the main cause of a knife slipping during cutting.",
                "Using a dull knife: watermelon rind is tougher than it looks, and a dull blade is more likely to slip than cut cleanly through.",
            ],
            "equipment": ["Large chef's knife", "Cutting board", "Large bowl for cubes"],
            "faqs": [
                {
                    "question": "How do I pick a ripe watermelon before cutting it?",
                    "answer": (
                        "Look for a uniform, dull (not shiny) rind, a creamy "
                        "yellow \"field spot\" where it sat on the ground, and a "
                        "heavy weight for its size. A hollow sound when tapped is "
                        "a traditional but less reliable indicator."
                    ),
                },
                {
                    "question": "How long do cut watermelon cubes last in the fridge?",
                    "answer": (
                        "About 3-5 days in an airtight container. Watermelon "
                        "releases a lot of liquid once cut, so drain any pooled "
                        "juice before storing to keep the pieces from getting "
                        "mushy."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_technique_slugs": [],
        },
    },
    {
        "slug": "how-to-brine-a-turkey",
        "template_type": "howto_technique",
        "title": "How to Brine a Turkey",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "How to wet-brine a turkey for a juicier, more evenly seasoned "
                "roast - ratios, timing, and food-safety notes."
            ),
            "hero_image_query": "turkey brining in a bucket",
            "intro": (
                "A wet brine seasons a turkey all the way through and "
                "helps it hold onto moisture during the long roast, but "
                "only if the ratio, timing, and turkey type are right. "
                "Get any of those wrong, especially brining an "
                "already-injected bird, and the result is worse than "
                "skipping it entirely."
            ),
            "steps": [
                "Dissolve 1 cup of kosher salt per gallon of water, along with any aromatics (bay leaves, peppercorns, citrus, herbs), in a large pot over heat, then cool completely.",
                "Place the fully thawed turkey in a food-safe brining bag or a very large stockpot.",
                "Pour the cooled brine over the turkey until fully submerged, adding plain cold water if needed to cover.",
                "Refrigerate (or keep below 40°F/4°C in a cooler with ice) for 12-24 hours, depending on size.",
                "Remove the turkey, rinse off the excess surface salt, and pat completely dry.",
                "Let the turkey air-dry uncovered in the refrigerator for a few hours, or roast right away.",
            ],
            "common_mistakes": [
                "Brining pre-basted or kosher turkeys: these are already injected with a salt solution, and brining them again results in an inedibly salty bird.",
                "Brining too long: beyond about 24 hours, the texture can turn spongy rather than juicy.",
                "Adding hot brine to the turkey: the brine must be fully cooled first, or it starts cooking the surface of the bird and creates a food-safety risk in the temperature danger zone.",
            ],
            "equipment": ["Large stockpot or food-safe brining bag", "Cooler (if refrigerator space is tight)", "Kitchen scale (optional, for measuring salt precisely)"],
            "faqs": [
                {
                    "question": "Do I need to rinse the turkey after brining?",
                    "answer": (
                        "Yes, rinse off the surface brine and pat the skin very "
                        "dry. Leftover surface salt makes the skin taste overly "
                        "salty, and a wet surface won't crisp well in the oven."
                    ),
                },
                {
                    "question": "Can I brine a frozen turkey?",
                    "answer": (
                        "No, it needs to be fully thawed first so the brine can "
                        "penetrate evenly. Brining a partially frozen turkey "
                        "results in uneven seasoning and an unsafe, extended time "
                        "in the temperature danger zone for the still-frozen parts."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_technique_slugs": ["how-to-use-a-meat-thermometer"],
        },
    },
    {
        "slug": "how-to-frost-a-cake",
        "template_type": "howto_technique",
        "title": "How to Frost a Cake",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "How to frost a layer cake with smooth, even sides using a "
                "crumb coat, the technique bakeries actually use."
            ),
            "hero_image_query": "frosting a layer cake",
            "intro": (
                "The smooth, bakery-style finish on a frosted layer cake "
                "comes down to one step home bakers skip: the crumb "
                "coat. This is the technique bakeries actually use to "
                "keep loose crumbs out of the final layer of frosting."
            ),
            "steps": [
                "Make sure cake layers are completely cool, frosting a warm cake melts the frosting and tears the crumb.",
                "Level the tops of the layers with a serrated knife if they domed while baking.",
                "Place the first layer on a cake board or plate and spread an even layer of frosting on top.",
                "Stack the second layer on top, pressing gently to level it.",
                "Apply a thin \"crumb coat\", a very thin layer of frosting over the entire cake, to seal in loose crumbs.",
                "Refrigerate for 15-20 minutes until the crumb coat firms up.",
                "Apply the final, thicker layer of frosting, smoothing with an offset spatula or bench scraper.",
            ],
            "common_mistakes": [
                "Skipping the crumb coat: this is the single biggest cause of visible crumbs mixed into the final frosting layer.",
                "Frosting a warm or cooling cake: this melts the frosting and drags loose crumbs through it.",
                "Overfilling the piping bag or using frosting that's too soft: warm, soft frosting slides off the sides instead of holding a clean edge.",
            ],
            "equipment": ["Offset spatula", "Bench scraper (optional)", "Cake turntable (optional, but makes smoothing much easier)", "Serrated knife"],
            "faqs": [
                {
                    "question": "What is a crumb coat and is it really necessary?",
                    "answer": (
                        "A crumb coat is a thin layer of frosting applied first "
                        "and chilled before the final coat, it traps loose cake "
                        "crumbs so they don't end up smeared through the visible "
                        "final layer. It's optional for a rustic look, but "
                        "essential for smooth, bakery-style sides."
                    ),
                },
                {
                    "question": "How do I get perfectly smooth sides on a frosted cake?",
                    "answer": (
                        "After the crumb coat sets, apply a generous final layer "
                        "and hold a bench scraper at a slight angle against the "
                        "side while rotating the cake on a turntable, wiping the "
                        "scraper clean between passes."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_technique_slugs": [],
        },
    },
    {
        "slug": "how-to-steam-dumplings",
        "template_type": "howto_technique",
        "title": "How to Steam Dumplings",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "How to steam dumplings so the wrappers stay tender without "
                "sticking or turning gummy, bamboo steamer or metal steamer "
                "basket, either works."
            ),
            "hero_image_query": "steaming dumplings in a bamboo steamer",
            "intro": (
                "Steaming is the gentlest way to cook a dumpling without "
                "blowing out or drying the wrapper, but it goes wrong "
                "fast if the basket is overcrowded or the wrappers "
                "stick. This works the same whether you are using a "
                "bamboo steamer or a metal steamer basket."
            ),
            "steps": [
                "Line the steamer basket with parchment paper, cabbage leaves, or a light coat of oil to prevent sticking.",
                "Arrange dumplings with at least ½ inch of space between them, they expand slightly and will stick together if too close.",
                "Bring water in the pot below to a rolling boil.",
                "Set the steamer basket over the water, making sure the water doesn't touch the bottom of the basket.",
                "Cover and steam for 8-10 minutes for fresh dumplings, or 12-15 minutes from frozen, without lifting the lid early.",
                "Check that the wrapper is translucent and the filling is fully cooked through before removing.",
            ],
            "common_mistakes": [
                "Overcrowding the basket: dumplings that touch will fuse together and tear apart when separated.",
                "Letting the water run dry: check the water level for longer steaming batches and top up with more boiling water if needed.",
                "Lifting the lid repeatedly: this lets heat and steam escape and extends the actual cooking time.",
            ],
            "equipment": ["Bamboo or metal steamer basket", "Wok or pot the steamer fits over", "Parchment paper or cabbage leaves"],
            "faqs": [
                {
                    "question": "Do I need to thaw frozen dumplings before steaming?",
                    "answer": (
                        "No, steam them directly from frozen, just extend the "
                        "steaming time by a few minutes to make sure the filling "
                        "cooks through completely."
                    ),
                },
                {
                    "question": "Why do my dumplings stick to the steamer?",
                    "answer": (
                        "The steamer surface (or the parchment/cabbage liner) "
                        "needs a barrier between it and the dumpling wrapper, "
                        "an unlined metal or bamboo surface will cause sticking "
                        "almost every time."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_technique_slugs": [],
        },
    },
    {
        "slug": "how-to-use-a-meat-thermometer",
        "template_type": "howto_technique",
        "title": "How to Use a Meat Thermometer",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "How to correctly place a meat thermometer for an accurate "
                "reading, plus the USDA safe minimum temperatures by protein."
            ),
            "hero_image_query": "meat thermometer in chicken",
            "intro": (
                "A thermometer is only as accurate as where you put it, "
                "a probe touching bone or sitting in the wrong spot in "
                "the cut can read many degrees off from the actual "
                "internal temperature. Here is the correct placement, "
                "plus the USDA's safe minimum temperatures by protein."
            ),
            "steps": [
                "Insert the probe into the thickest part of the meat, avoiding bone, fat pockets, and gristle, all of which give a false reading.",
                "For poultry, check the innermost part of the thigh and wing, and the thickest part of the breast.",
                "For a whole roast or turkey, insert horizontally from the side rather than straight down, to reach the true center.",
                "Wait for the reading to stabilize (a few seconds for instant-read, longer for leave-in probe thermometers).",
                "Check in more than one spot for large or irregularly shaped cuts to confirm the coldest point has also reached a safe temperature.",
                "Clean the probe with hot soapy water between uses, especially between raw and cooked foods.",
            ],
            "common_mistakes": [
                "Touching bone with the probe tip: bone conducts and holds heat differently than meat and will give a misleadingly high reading.",
                "Checking only one spot: irregularly shaped cuts can have a thick section that's still underdone even if a thinner part reads safe.",
                "Reading immediately on insertion: instant-read thermometers still need a few seconds to stabilize; pulling the reading too fast risks an inaccurate low number.",
            ],
            "equipment": ["Instant-read or leave-in probe thermometer"],
            "faqs": [
                {
                    "question": "What internal temperature is chicken safe to eat at?",
                    "answer": (
                        "165°F (74°C) at the thickest part, per USDA guidelines. "
                        "Dark meat (thighs, drumsticks) is also safe at that "
                        "temperature and is often more tender there than at "
                        "lower temperatures some cooks target."
                    ),
                },
                {
                    "question": "Do I need a different thermometer for grilling versus roasting?",
                    "answer": (
                        "No, the same instant-read or probe thermometer works for "
                        "both, what matters is insertion technique (thickest "
                        "part, avoiding bone) more than the cooking method being "
                        "used."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_technique_slugs": ["how-to-brine-a-turkey"],
        },
    },
    {
        "slug": "how-to-season-a-wok",
        "template_type": "howto_technique",
        "title": "How to Season a Wok",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "How to season a new carbon steel wok so food releases cleanly "
                "and it resists rust, the stovetop method, step by step."
            ),
            "hero_image_query": "seasoning a carbon steel wok",
            "intro": (
                "A new carbon steel wok is bare metal that rusts and "
                "sticks until it builds up a seasoned patina, and that "
                "only happens with the right stovetop process. Skip a "
                "step, or reach for soap too early, and the seasoning "
                "you are building gets stripped right back off."
            ),
            "steps": [
                "Scrub a new wok thoroughly with soap and hot water to remove the factory coating, this is the one time it's fine to use soap on it.",
                "Dry completely, then heat the empty wok over high heat until it starts to change color slightly.",
                "Add a small amount of high-smoke-point oil (vegetable or peanut oil) and swirl to coat the entire interior surface.",
                "Continue heating and swirling until the oil starts to smoke, then carefully wipe out the excess with tongs and a paper towel.",
                "Repeat the oiling and heating process 3-4 times, building up a thin, dark patina with each round.",
                "Stir-fry an inexpensive aromatic batch (ginger and scallion scraps work well) as a final seasoning pass, then wipe clean.",
            ],
            "common_mistakes": [
                "Using soap after seasoning has started: soap strips the oil patina being built up, only the very first factory-coating cleaning should use soap.",
                "Using too much oil: a thick pooled layer turns sticky and gummy rather than forming a smooth patina; wipe out excess after each round.",
                "Storing it wet: dry the wok completely and rub a very thin layer of oil on it before storing to prevent rust.",
            ],
            "equipment": ["Carbon steel wok", "High smoke-point oil", "Tongs", "Paper towels"],
            "faqs": [
                {
                    "question": "Why does food stick to my new wok even after seasoning?",
                    "answer": (
                        "A single seasoning round isn't enough, the nonstick "
                        "patina builds up gradually over repeated cooking "
                        "sessions. Continue cooking with oil regularly and it "
                        "will keep improving over the first several uses."
                    ),
                },
                {
                    "question": "How do I stop my wok from rusting?",
                    "answer": (
                        "Never let it air-dry wet or soak in water, dry it "
                        "immediately over low heat after washing, then rub a "
                        "very thin layer of oil over the surface before storing."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_technique_slugs": [],
        },
    },
    {
        "slug": "how-to-make-cold-brew-concentrate",
        "template_type": "howto_technique",
        "title": "How to Make Cold Brew Concentrate",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "How to make cold brew coffee concentrate at home - ratio, "
                "steep time, and how to dilute it for drinking."
            ),
            "hero_image_query": "cold brew coffee concentrate in a jar",
            "intro": (
                "Cold brew concentrate is just coffee grounds steeped in "
                "cold water for a long time, but the grind size, ratio, "
                "and steep time all matter more than they do for hot "
                "coffee. Get them right and you get a smooth, low-acid "
                "concentrate that is easy to dilute to taste."
            ),
            "steps": [
                "Coarsely grind coffee beans, a texture like coarse sea salt, similar to French press grind.",
                "Combine 1 cup of coarsely ground coffee with 4 cups of cold or room-temperature water in a large jar or pitcher.",
                "Stir gently to make sure all the grounds are saturated.",
                "Cover and steep at room temperature or in the refrigerator for 12-18 hours.",
                "Strain through a fine-mesh sieve lined with a coffee filter or cheesecloth, pressing gently on the grounds.",
                "Store the concentrate in the refrigerator and dilute with water or milk (roughly 1:1) to taste before drinking.",
            ],
            "common_mistakes": [
                "Using a fine grind: it passes through most strainers and leaves the concentrate gritty; a coarse grind is essential.",
                "Steeping too briefly: cold extraction is slow, under 12 hours typically under-extracts and tastes weak and sour once diluted.",
                "Drinking it undiluted: cold brew concentrate is meant to be cut with water, milk, or ice, straight concentrate is much stronger than a normal cup of coffee.",
            ],
            "equipment": ["Large jar or pitcher", "Fine-mesh sieve", "Coffee filter or cheesecloth", "Coffee grinder"],
            "faqs": [
                {
                    "question": "How long does cold brew concentrate last in the fridge?",
                    "answer": (
                        "About 1-2 weeks refrigerated in a sealed container, "
                        "notably longer than brewed hot coffee, since cold brew's "
                        "extraction process produces less of the compounds that "
                        "go stale or sour quickly."
                    ),
                },
                {
                    "question": "What's the difference between cold brew and iced coffee?",
                    "answer": (
                        "Cold brew is steeped with cold water over many hours; "
                        "iced coffee is regular hot-brewed coffee cooled and "
                        "poured over ice. Cold brew is typically smoother and "
                        "less acidic since hot extraction pulls out more acidic "
                        "compounds."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_technique_slugs": [],
        },
    },
    {
        "slug": "how-to-boil-chicken-breast",
        "template_type": "howto_technique",
        "title": "How Long to Boil Chicken Breast",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "How long to boil chicken breast until safely cooked but still "
                "juicy, timing by size, plus how to shred it afterward."
            ),
            "hero_image_query": "boiled chicken breast sliced",
            "intro": (
                "Chicken breast turns tough and stringy shockingly fast "
                "in boiling water. The fix is not a magic timing number "
                "so much as keeping the water at a bare simmer rather "
                "than a rolling boil, and timing here also depends "
                "heavily on the size of the breast, not just the clock."
            ),
            "steps": [
                "Place boneless, skinless chicken breasts in a single layer in a pot and cover with cold water or broth by about an inch.",
                "Add aromatics if desired, a bay leaf, a few peppercorns, a smashed garlic clove.",
                "Bring to a boil, then immediately reduce to a gentle simmer, a hard boil toughens the meat.",
                "Simmer for 12-15 minutes for average-size breasts (about 6-8 oz each), or until the internal temperature reaches 165°F (74°C).",
                "Remove from the liquid and let rest for 5 minutes before slicing or shredding.",
            ],
            "common_mistakes": [
                "Boiling hard instead of simmering gently: a rolling boil makes chicken breast noticeably tougher and stringier.",
                "Not checking temperature: cook times vary with breast size and starting temperature, so a thermometer is more reliable than the clock alone.",
                "Cutting into it immediately: resting for a few minutes keeps the juices in the meat instead of spilling out onto the cutting board.",
            ],
            "equipment": ["Large pot", "Instant-read thermometer", "Tongs"],
            "faqs": [
                {
                    "question": "Why does my boiled chicken turn out rubbery?",
                    "answer": (
                        "Almost always from boiling too hard or too long. Keep "
                        "the liquid at a gentle simmer, not a rolling boil, and "
                        "pull the chicken as soon as it hits 165°F (74°C) rather "
                        "than cooking it further \"to be safe.\""
                    ),
                },
                {
                    "question": "Can I use the cooking liquid afterward?",
                    "answer": (
                        "Yes, if you added aromatics, the poaching liquid "
                        "becomes a light, usable chicken broth. Strain out the "
                        "solids and use it as a base for soup or to cook rice."
                    ),
                },
            ],
            "recipe_slugs": ["chicken-broccoli-rice-casserole"],
            "related_technique_slugs": ["how-to-use-a-meat-thermometer"],
        },
    },
    {
        "slug": "how-to-bake-bacon-in-the-oven",
        "template_type": "howto_technique",
        "title": "How to Bake Bacon in the Oven",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "How to bake bacon in the oven for evenly crisp strips with no "
                "stovetop splatter - temperature, timing, and cleanup tips."
            ),
            "hero_image_query": "baking bacon on a sheet pan",
            "intro": (
                "Baking bacon in the oven gets every strip evenly crisp "
                "at the same time, with none of the stovetop splatter "
                "or standing-over-the-pan babysitting that comes with "
                "frying it. The main choice to make upfront is oven "
                "temperature and whether to start from cold or "
                "preheated, pick one and watch closely the first time."
            ),
            "steps": [
                "Preheat the oven to 400°F (200°C).",
                "Line a rimmed baking sheet with foil or parchment for easy cleanup.",
                "Arrange bacon strips in a single layer without overlapping.",
                "Bake for 15-20 minutes, depending on thickness and desired crispness, without flipping.",
                "Check at the 15-minute mark, bacon can go from perfectly crisp to burnt quickly in the last few minutes.",
                "Transfer to a paper-towel-lined plate to drain excess grease before serving.",
            ],
            "common_mistakes": [
                "Starting with a hot oven and cold pan mismatch: a cold oven start (adding bacon before preheating) can also work but changes timing, pick one method and watch closely the first time.",
                "Overlapping strips: this causes uneven cooking, with the overlapped sections staying pale and undercooked.",
                "Not saving the rendered fat: strained bacon grease keeps refrigerated for weeks and is excellent for cooking eggs or roasting vegetables.",
            ],
            "equipment": ["Rimmed baking sheet", "Foil or parchment paper", "Tongs"],
            "faqs": [
                {
                    "question": "Do I need to flip bacon when baking it?",
                    "answer": (
                        "No, unlike pan-frying, the oven's heat surrounds the "
                        "bacon evenly on a sheet pan, so flipping isn't necessary "
                        "for even cooking."
                    ),
                },
                {
                    "question": "Why is oven-baked bacon better than pan-frying for a crowd?",
                    "answer": (
                        "A full sheet pan cooks a dozen or more strips at once, "
                        "hands-off, versus babysitting a skillet in smaller "
                        "batches, and there's far less grease splatter to clean "
                        "up afterward."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_technique_slugs": [],
        },
    },
    {
        "slug": "how-to-make-powdered-sugar",
        "template_type": "howto_technique",
        "title": "How to Make Powdered Sugar",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "How to make powdered sugar at home from granulated sugar using "
                "a blender or food processor, ready in under a minute."
            ),
            "hero_image_query": "homemade powdered sugar",
            "intro": (
                "Powdered sugar is just granulated sugar ground fine "
                "enough to dissolve instantly, something a blender or "
                "food processor can do in under a minute at home. The "
                "one thing store-bought powdered sugar has that a DIY "
                "batch needs too is a bit of cornstarch, without it, it "
                "clumps back together fast."
            ),
            "steps": [
                "Add granulated sugar to a high-speed blender or food processor.",
                "For every cup of sugar, add 1 tablespoon of cornstarch (this prevents clumping, matching store-bought powdered sugar).",
                "Blend on high for 1-2 minutes, until completely fine and powdery.",
                "Let the dust settle for a minute before opening the lid.",
                "Sift if any coarser bits remain, and use immediately or store in an airtight container.",
            ],
            "common_mistakes": [
                "Skipping the cornstarch: without it, homemade powdered sugar clumps together much faster than the store-bought version.",
                "Opening the lid immediately: the fine sugar dust needs a moment to settle, or it puffs out in a cloud.",
                "Under-blending: stop too early and the sugar stays gritty rather than truly powdered, give it the full 1-2 minutes.",
            ],
            "equipment": ["High-speed blender or food processor", "Fine-mesh sifter (optional)"],
            "faqs": [
                {
                    "question": "Can I make powdered sugar without cornstarch?",
                    "answer": (
                        "Yes, it'll still work as powdered sugar, but it will "
                        "clump and harden faster during storage since cornstarch "
                        "is what keeps commercial powdered sugar free-flowing."
                    ),
                },
                {
                    "question": "How long does homemade powdered sugar keep?",
                    "answer": (
                        "Stored in an airtight container in a dry pantry, it "
                        "keeps indefinitely, similar to granulated sugar, just "
                        "expect it to clump somewhat over time and need a quick "
                        "whisk or re-sift before using."
                    ),
                },
            ],
            "recipe_slugs": [],
            "related_technique_slugs": [],
        },
    },
    {
        "slug": "what-is-burrata",
        "template_type": "definition",
        "title": "What Is Burrata?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Burrata is a fresh Italian cheese with a solid mozzarella "
                "shell and a soft, creamy center. What it is and how to serve it."
            ),
            "hero_image_query": "burrata cheese cut open",
            "direct_answer": (
                "Burrata is a fresh Italian cheese made of a solid mozzarella "
                "shell filled with a soft mixture of shredded mozzarella and "
                "cream, so cutting it open releases a creamy, oozing center."
            ),
            "expanded_explanation": (
                "The name comes from the Italian burro (butter), a nod to its "
                "rich, buttery center. It originated in Puglia, in southern "
                "Italy, as a way to use up mozzarella scraps by wrapping them "
                "with cream inside a fresh mozzarella pouch. Unlike aged "
                "cheeses, it's meant to be eaten very fresh, typically within "
                "a day or two of being made."
            ),
            "usage_origin": (
                "Most often served simply, at room temperature, drizzled "
                "with good olive oil, flaky salt, and black pepper, alongside "
                "crusty bread or ripe tomatoes. It's a finishing or centerpiece "
                "cheese rather than a melting or cooking cheese."
            ),
            "substitute_note": "Fresh mozzarella (bocconcini or a ball) is the closest substitute, though it lacks burrata's creamy center.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Is burrata the same as mozzarella?",
                    "answer": (
                        "No, though it's made from the same base. Burrata is a "
                        "mozzarella shell filled with soft cheese curds and "
                        "cream, giving it a creamy, oozing center that solid "
                        "mozzarella doesn't have."
                    ),
                },
                {
                    "question": "How long does burrata last in the fridge?",
                    "answer": (
                        "It's highly perishable and best eaten within 1-2 days "
                        "of purchase, kept refrigerated in its liquid. It doesn't "
                        "keep nearly as long as aged or even fresh mozzarella."
                    ),
                },
            ],
            "related_recipe_slugs": [],
        },
    },
    {
        "slug": "what-is-brisket",
        "template_type": "definition",
        "title": "What Is Brisket?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Brisket is a tough, well-worked cut of beef from the chest "
                "that turns tender with long, slow cooking. What it is and how "
                "it's typically prepared."
            ),
            "hero_image_query": "raw beef brisket",
            "direct_answer": (
                "Brisket is a cut of beef from the lower chest of the cow, "
                "made of two muscles (the \"flat\" and the \"point\") that "
                "support a large portion of the animal's body weight."
            ),
            "expanded_explanation": (
                "Because it's a heavily worked muscle, brisket is naturally "
                "tough and full of connective tissue, it needs long, slow "
                "cooking (smoking, braising) to break that collagen down into "
                "gelatin, which is what turns it tender rather than chewy. "
                "Cooked quickly with high heat, it stays tough no matter the "
                "seasoning."
            ),
            "usage_origin": (
                "Central to Texas-style barbecue (smoked low and slow for many "
                "hours) and to Jewish deli cooking (braised for corned beef and "
                "pastrami). Both traditions rely on the same principle: time "
                "and moisture, not high heat, are what make brisket good."
            ),
            "substitute_note": "Chuck roast is the closest substitute for braising, though it lacks brisket's specific fat cap and grain for slicing.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Why is my brisket tough even after cooking it a long time?",
                    "answer": (
                        "Usually it needs more time, not less heat, brisket "
                        "often has to pass through a temperature \"stall\" where "
                        "it seems stuck for hours before the collagen finally "
                        "breaks down. Rushing it, or pulling it before it's "
                        "probe-tender, is the most common cause of toughness."
                    ),
                },
                {
                    "question": "What's the difference between the flat and the point?",
                    "answer": (
                        "The flat is leaner and slices neatly, while the point "
                        "is fattier, more marbled, and more forgiving to cook, "
                        "it's the cut typically used for burnt ends."
                    ),
                },
            ],
            "related_recipe_slugs": [],
        },
    },
    {
        "slug": "what-is-mochi",
        "template_type": "definition",
        "title": "What Is Mochi?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Mochi is a chewy Japanese rice cake made from pounded glutinous "
                "rice. What it is, how it's made, and its common forms."
            ),
            "hero_image_query": "mochi rice cakes",
            "direct_answer": (
                "Mochi is a chewy Japanese rice cake made by pounding cooked "
                "glutinous (sticky) rice into a smooth, elastic paste, then "
                "shaping it while warm."
            ),
            "expanded_explanation": (
                "Traditional mochi is made through mochitsuki, a labor-intensive "
                "process of steaming glutinous rice and pounding it in a large "
                "mortar with a wooden mallet until it transforms into a smooth, "
                "stretchy dough. Modern mochi is often made faster with a stand "
                "mixer or microwave method using sweet rice flour (mochiko) "
                "instead of whole steamed rice."
            ),
            "usage_origin": (
                "Traditional in Japanese New Year celebrations (mochitsuki is "
                "often a communal event) and used in both savory dishes (grilled "
                "mochi, added to soups) and sweet ones, daifuku (mochi filled "
                "with sweet red bean paste) and mochi ice cream are the most "
                "internationally familiar forms."
            ),
            "substitute_note": "There isn't a good direct substitute, glutinous rice flour's specific starch structure is what gives mochi its stretchy chew.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Is mochi made from regular rice or a special kind?",
                    "answer": (
                        "It requires glutinous rice (also called sweet or sticky "
                        "rice), which is botanically different from the long- or "
                        "short-grain rice used for regular cooked rice, and has "
                        "no gluten despite the name."
                    ),
                },
                {
                    "question": "Why is mochi a choking hazard, and how can it be eaten more safely?",
                    "answer": (
                        "Its dense, sticky, chewy texture makes it hard to break "
                        "down and easy to swallow before it's fully chewed, which "
                        "is a particular risk for young children and older "
                        "adults. Cutting it into smaller pieces and chewing "
                        "thoroughly before swallowing reduces the risk."
                    ),
                },
            ],
            "related_recipe_slugs": [],
        },
    },
    {
        "slug": "what-is-hummus",
        "template_type": "definition",
        "title": "What Is Hummus?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Hummus is a creamy Middle Eastern dip made from blended "
                "chickpeas and tahini. What it is and its traditional "
                "preparation."
            ),
            "hero_image_query": "bowl of hummus",
            "direct_answer": (
                "Hummus is a smooth, creamy dip or spread made by blending "
                "cooked chickpeas with tahini, lemon juice, garlic, and olive "
                "oil."
            ),
            "expanded_explanation": (
                "\"Hummus\" is simply the Arabic word for chickpeas, and the "
                "full traditional name is hummus bi tahini (chickpeas with "
                "tahini). Texture and flavor vary widely by recipe and region, "
                "some versions are whipped very light and airy by blending "
                "for an extended time, while others stay coarser and more "
                "rustic."
            ),
            "usage_origin": (
                "A staple across the Middle East and Eastern Mediterranean for "
                "centuries, traditionally served as part of a mezze spread with "
                "warm pita, raw vegetables, and olive oil drizzled on top. "
                "Its exact origin is a point of ongoing regional debate rather "
                "than a settled fact."
            ),
            "substitute_note": "White bean dip (blended cannellini or great northern beans with tahini) is a reasonable stand-in if chickpeas aren't available.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Why is my homemade hummus grainy instead of smooth?",
                    "answer": (
                        "Usually the chickpea skins, removing them (rubbing "
                        "cooked chickpeas in a towel, or simmering them briefly "
                        "with a pinch of baking soda to loosen the skins) makes a "
                        "noticeably smoother final texture."
                    ),
                },
                {
                    "question": "Can I make hummus without tahini?",
                    "answer": (
                        "Yes, though it won't taste quite the same, tahini "
                        "provides a nutty depth that's part of hummus's "
                        "signature flavor. A tahini-free version made with just "
                        "chickpeas, lemon, garlic, and olive oil is still "
                        "genuinely good, just different."
                    ),
                },
            ],
            "related_recipe_slugs": [],
        },
    },
    {
        "slug": "what-is-gelato",
        "template_type": "definition",
        "title": "What Is Gelato?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Gelato is an Italian frozen dessert, denser and less airy than "
                "American ice cream. What makes it different."
            ),
            "hero_image_query": "gelato in a display case",
            "direct_answer": (
                "Gelato is an Italian-style frozen dessert made with a base "
                "similar to ice cream's, but churned much more slowly, which "
                "incorporates far less air and results in a denser, more "
                "intensely flavored texture."
            ),
            "expanded_explanation": (
                "Gelato typically uses more milk and less cream than American "
                "ice cream, and is churned at a slower speed, which traps "
                "roughly half the air (called \"overrun\" in the industry). "
                "It's also served notably warmer than ice cream, around "
                "10-15°F warmer, which keeps it soft and scoopable rather "
                "than rock-hard."
            ),
            "usage_origin": (
                "A centuries-old Italian tradition, sold from gelaterie across "
                "Italy and, increasingly, internationally, typically displayed "
                "in shallow, covered pans rather than scooped from deep tubs."
            ),
            "substitute_note": "Ice cream is the closest substitute, though it will taste noticeably lighter and airier by comparison.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Is gelato lower in fat than ice cream?",
                    "answer": (
                        "Often, yes, since it uses more milk and less cream, but "
                        "not always, some gelato recipes are quite rich. Its "
                        "denser texture (less air) can also make it feel more "
                        "indulgent per bite even at a similar fat percentage."
                    ),
                },
                {
                    "question": "Why does gelato melt faster than ice cream?",
                    "answer": (
                        "It's served at a warmer temperature and contains less "
                        "air, both of which mean less insulation and a head "
                        "start toward melting once it's out of the case, it's "
                        "meant to be eaten promptly, not carried around slowly."
                    ),
                },
            ],
            "related_recipe_slugs": ["mango-ice-cream"],
        },
    },
    {
        "slug": "what-is-caviar",
        "template_type": "definition",
        "title": "What Is Caviar?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Caviar is salt-cured sturgeon roe (fish eggs). What qualifies "
                "as true caviar and how it's traditionally served."
            ),
            "hero_image_query": "caviar tin with spoon",
            "direct_answer": (
                "Caviar is salt-cured fish roe (eggs), and by strict "
                "traditional definition, specifically the roe of wild sturgeon "
                "from the Caspian and Black Sea regions."
            ),
            "expanded_explanation": (
                "Roe from other fish - salmon, trout, whitefish - is often "
                "sold as \"caviar\" in a looser, more common usage, but purists "
                "reserve the term strictly for sturgeon roe. Grading depends on "
                "the species of sturgeon, egg size, color, and firmness - "
                "beluga, osetra, and sevruga are the most well-known varieties."
            ),
            "usage_origin": (
                "Long associated with Russian and Persian aristocracy, caviar "
                "became internationally prestigious in the 19th and 20th "
                "centuries. Wild sturgeon populations have declined sharply "
                "from overfishing, so most caviar sold today comes from "
                "regulated sturgeon farms rather than wild-caught fish."
            ),
            "substitute_note": "Salmon roe (ikura) or trout roe are common, far less expensive substitutes, though they differ noticeably in flavor, size, and texture from true sturgeon caviar.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Is all fish roe technically caviar?",
                    "answer": (
                        "Strictly speaking, no, true caviar is sturgeon roe "
                        "specifically. Roe from salmon, trout, and other fish is "
                        "commonly labeled \"caviar\" in retail, but is more "
                        "precisely just \"roe\" under the traditional definition."
                    ),
                },
                {
                    "question": "How should caviar be served?",
                    "answer": (
                        "Traditionally chilled, in small portions, with a "
                        "non-metal spoon (mother-of-pearl or bone), since metal "
                        "can react with the roe and affect its flavor. Simple "
                        "accompaniments, blini, crème fraîche, toast points, "
                        "are preferred over anything that masks its flavor."
                    ),
                },
            ],
            "related_recipe_slugs": [],
        },
    },
    {
        "slug": "what-is-lard",
        "template_type": "definition",
        "title": "What Is Lard?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Lard is rendered pork fat used for cooking and baking. What it "
                "is and why it's prized for flaky pastry."
            ),
            "hero_image_query": "lard in a jar",
            "direct_answer": (
                "Lard is rendered (melted down and purified) pork fat, used as "
                "a cooking fat and, especially, as a shortening in baking."
            ),
            "expanded_explanation": (
                "Different cuts of pork fat render into lard with different "
                "qualities, leaf lard, rendered from the fat around the "
                "kidneys, is the mildest-tasting and most prized for baking, "
                "while fat from other parts of the pig renders into a more "
                "flavorful, porkier lard better suited to savory cooking."
            ),
            "usage_origin": (
                "A dominant cooking fat across many cuisines for centuries "
                "before vegetable shortening and oils became widely available "
                "and marketed as healthier alternatives in the 20th century. "
                "It's seen a resurgence among bakers specifically for its "
                "effect on pastry texture."
            ),
            "substitute_note": "Vegetable shortening substitutes 1:1 by volume, though pastry made with it will be slightly less flaky and flavorful than one made with lard.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Why does lard make pie crust flakier than butter?",
                    "answer": (
                        "Lard has a larger fat crystal structure and a higher "
                        "melting point than butter, which creates larger, more "
                        "distinct layers in the dough as it bakes, many bakers "
                        "use a mix of both for lard's flakiness and butter's "
                        "flavor."
                    ),
                },
                {
                    "question": "Is lard the same thing as shortening?",
                    "answer": (
                        "No, lard is rendered animal (pork) fat, while "
                        "shortening is a manufactured, typically hydrogenated "
                        "vegetable fat. They behave similarly in baking but come "
                        "from entirely different sources."
                    ),
                },
            ],
            "related_recipe_slugs": [],
        },
    },
    {
        "slug": "what-is-yuzu",
        "template_type": "definition",
        "title": "What Is Yuzu?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Yuzu is an East Asian citrus fruit with an aromatic, tart "
                "flavor between a mandarin, grapefruit, and lemon. What it is "
                "and how it's used."
            ),
            "hero_image_query": "yuzu citrus fruit",
            "direct_answer": (
                "Yuzu is an East Asian citrus fruit, roughly the size of a "
                "small orange, with a highly aromatic, tart flavor often "
                "described as a cross between a mandarin, grapefruit, and lemon."
            ),
            "expanded_explanation": (
                "Yuzu is grown mainly for its zest and juice rather than eaten "
                "as fresh fruit, it's quite seedy and sour on its own. It's "
                "prized specifically for its intensely fragrant peel, which "
                "carries most of its distinctive floral, citrusy aroma."
            ),
            "usage_origin": (
                "Widely used in Japanese and Korean cooking, yuzu kosho "
                "(a fermented chile-yuzu paste), ponzu sauce, yuzu tea, and as "
                "a zested garnish over both savory dishes and desserts. It has "
                "become popular internationally in high-end cooking and "
                "cocktails over the past couple of decades."
            ),
            "substitute_note": "A mix of lemon, lime, and a little mandarin orange juice/zest approximates yuzu's flavor profile reasonably well when it isn't available.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Can I eat yuzu like a regular orange?",
                    "answer": (
                        "It's technically edible but very sour and seedy, so "
                        "it's almost never eaten out of hand, its juice and "
                        "zest are what's used in cooking, not the whole fruit "
                        "as a snack."
                    ),
                },
                {
                    "question": "Why is fresh yuzu hard to find outside Japan?",
                    "answer": (
                        "It has a short harvest season and doesn't ship or "
                        "store as easily as more common citrus, so most markets "
                        "outside East Asia carry bottled yuzu juice or yuzu "
                        "kosho rather than the fresh fruit."
                    ),
                },
            ],
            "related_recipe_slugs": [],
        },
    },
    {
        "slug": "what-is-vermouth",
        "template_type": "definition",
        "title": "What Is Vermouth?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Vermouth is a fortified, aromatized wine used in cocktails "
                "like the martini and Manhattan. What it is and how it's "
                "categorized."
            ),
            "hero_image_query": "vermouth bottle and glass",
            "direct_answer": (
                "Vermouth is a fortified wine flavored with botanicals, "
                "herbs, spices, roots, and bark, and typically categorized "
                "as either dry (white) or sweet (red)."
            ),
            "expanded_explanation": (
                "\"Fortified\" means a neutral spirit (usually brandy) is added "
                "to raise the alcohol content beyond what fermentation alone "
                "achieves, and \"aromatized\" means it's further flavored with a "
                "proprietary blend of botanicals, which varies by brand and is "
                "often a closely guarded recipe."
            ),
            "usage_origin": (
                "Developed in 18th-century Italy and France as a way to make "
                "cheaper wine more palatable and shelf-stable, it became "
                "essential to classic cocktails, dry vermouth in a martini, "
                "sweet vermouth in a Manhattan or Negroni, once cocktail "
                "culture took off in the 19th and 20th centuries."
            ),
            "substitute_note": "Dry sherry can stand in for dry vermouth, and a splash of port or Madeira with a dash of bitters approximates sweet vermouth in a pinch.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Does vermouth need to be refrigerated after opening?",
                    "answer": (
                        "Yes, unlike hard spirits, vermouth is wine-based and "
                        "starts to oxidize and lose flavor once opened. "
                        "Refrigerate it and use within about a month for best "
                        "flavor."
                    ),
                },
                {
                    "question": "What's the difference between dry and sweet vermouth?",
                    "answer": (
                        "Dry (white) vermouth is lighter and less sweet, used in "
                        "martinis; sweet (red) vermouth is darker, richer, and "
                        "sweeter, used in Manhattans and Negronis. They aren't "
                        "interchangeable in most classic cocktail recipes."
                    ),
                },
            ],
            "related_recipe_slugs": ["amaretto-sour"],
        },
    },
    {
        "slug": "what-is-whey",
        "template_type": "definition",
        "title": "What Is Whey?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Whey is the liquid left over from making cheese, and the "
                "source of whey protein powder. What it is and how it's used."
            ),
            "hero_image_query": "whey protein powder and liquid whey",
            "direct_answer": (
                "Whey is the watery liquid left behind after milk is curdled "
                "and strained during cheesemaking, it's the part that "
                "separates from the solid curds."
            ),
            "expanded_explanation": (
                "It contains proteins, lactose, vitamins, and minerals from "
                "the original milk. \"Sweet whey\" comes from rennet-based "
                "cheesemaking (most hard cheeses); \"acid whey\" comes from "
                "acid-set cheeses like ricotta and paneer, and has a more "
                "sour flavor and different mineral profile."
            ),
            "usage_origin": (
                "Historically often discarded or fed to livestock as a "
                "cheesemaking byproduct. Today it's commercially dried and "
                "concentrated into whey protein powder (a major fitness and "
                "supplement product), and used in some traditional dishes like "
                "Norwegian brunost (whey cheese) and ricotta, which is itself "
                "made by cooking whey further."
            ),
            "substitute_note": "There isn't a real substitute for whey's specific role, in recipes that call for leftover whey (like using it as a liquid in baking), buttermilk or milk work as a reasonable stand-in.",
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Is whey protein powder the same as the liquid whey from cheesemaking?",
                    "answer": (
                        "It starts from the same liquid, but whey protein "
                        "powder is filtered, concentrated, and dried into a "
                        "much more protein-dense product, not something you'd "
                        "get by just draining and drying leftover cheesemaking "
                        "whey at home."
                    ),
                },
                {
                    "question": "Can I use leftover whey from making ricotta or yogurt?",
                    "answer": (
                        "Yes, it works well as a liquid in bread dough, "
                        "pancake batter, or smoothies, adding a mild tang and "
                        "some extra protein rather than being wasted."
                    ),
                },
            ],
            "related_recipe_slugs": [],
        },
    },
    # Technique glossary: definitions for the recipe-instruction jargon a
    # novice reader wouldn't know (fold, sear, dredge, ...), so LinkifiedText
    # can link the first mention inside a recipe's own instructions straight
    # to a real explanation instead of assuming the reader already knows it.
    # related_recipe_slugs point back to the actual recipes that use each
    # technique in their instructions, not every recipe that plausibly could.
    {
        "slug": "what-is-folding",
        "template_type": "definition",
        "title": "What Is Folding?",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Folding is a gentle mixing technique that combines a light, "
                "whipped ingredient into a heavier one without knocking the "
                "air back out. How and when to use it."
            ),
            "hero_image_query": "folding whipped cream into batter",
            "link_terms": ["fold", "folds", "folded", "folding"],
            "direct_answer": (
                "Folding is a gentle mixing technique that combines a light, "
                "airy mixture, like whipped cream or beaten egg whites, into "
                "a heavier one without deflating the air already whipped "
                "into it."
            ),
            "expanded_explanation": (
                "Instead of stirring in circles, folding uses a rubber "
                "spatula to cut down through the center of the bowl, scrape "
                "along the bottom, and turn the mixture up and over itself, "
                "rotating the bowl a quarter turn between passes. The goal "
                "is combining the two mixtures in as few strokes as "
                "possible, since every extra stroke knocks more air back out."
            ),
            "usage_origin": (
                "Used any time a recipe needs to protect a whipped "
                "component's volume, folding whipped cream into a mousse or "
                "no-churn ice cream base, or folding whipped egg whites into "
                "a soufflé or cake batter."
            ),
            "substitute_note": (
                "No substitute for the technique itself, but if you don't "
                "have a rubber spatula, a large metal spoon works almost as "
                "well, just use the same gentle scoop-and-turn motion "
                "instead of a flat blade that cuts straight through."
            ),
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "What's the difference between folding and stirring?",
                    "answer": (
                        "Stirring uses a circular motion that's efficient at "
                        "combining ingredients but knocks air out of "
                        "anything whipped. Folding uses a scoop-and-turn "
                        "motion specifically to combine two mixtures while "
                        "keeping most of that air intact."
                    ),
                },
                {
                    "question": "How do I know when I've folded enough?",
                    "answer": (
                        "Stop as soon as no large streaks of the unmixed "
                        "ingredient remain. A few small streaks are better "
                        "than overmixing, once it looks fully uniform, "
                        "you've likely folded a few strokes too many and "
                        "lost some volume."
                    ),
                },
            ],
            "related_recipe_slugs": ["banana-nut-bread", "mango-ice-cream"],
        },
    },
    {
        "slug": "what-is-pureeing",
        "template_type": "definition",
        "title": "What Is Pureeing?",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Pureeing means blending a food until completely smooth, "
                "with no visible chunks. What it means and how it's done."
            ),
            "hero_image_query": "pureeing mango in a blender",
            "link_terms": ["puree", "purees", "pureed", "pureeing"],
            "direct_answer": (
                "Pureeing means blending a food until it's completely "
                "smooth, with no visible chunks, pieces, or fibers left, "
                "usually in a blender, food processor, or with an immersion "
                "blender."
            ),
            "expanded_explanation": (
                "The goal is a uniform consistency, pourable to thick "
                "depending on the ingredient's water content, a pureed "
                "mango is roughly the texture of a thick smoothie, while a "
                "pureed vegetable soup base can be closer to a paste before "
                "liquid is added back. Fibrous ingredients sometimes benefit "
                "from straining the puree afterward to remove any stringy "
                "bits a blender didn't fully break down."
            ),
            "usage_origin": (
                "Used for smoothie and ice cream bases (like mango puree), "
                "soups, sauces, and baby food, anywhere a recipe wants a "
                "uniform, chunk-free texture rather than distinct pieces."
            ),
            "substitute_note": (
                "A blender or food processor both work; for a small amount, "
                "a fine-mesh sieve and the back of a spoon can push a soft "
                "ingredient through by hand, though it takes longer."
            ),
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Do I need a special blender to puree food?",
                    "answer": (
                        "No, a standard countertop blender, food processor, "
                        "or handheld immersion blender all work. An "
                        "immersion blender is convenient for pureeing "
                        "directly in a pot of soup without transferring hot "
                        "liquid to a separate blender."
                    ),
                },
                {
                    "question": "Why is my puree still a little chunky?",
                    "answer": (
                        "Usually the pieces going in were too large or too "
                        "firm to begin with. Cutting ingredients smaller "
                        "first, or cooking them until fully tender before "
                        "blending, gives the blender less work to do."
                    ),
                },
            ],
            "related_recipe_slugs": ["mango-ice-cream"],
        },
    },
    {
        "slug": "what-is-dredging",
        "template_type": "definition",
        "title": "What Is Dredging?",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Dredging means coating food lightly in a dry ingredient, "
                "usually the first step in a multi-step breading. How it "
                "works and why it matters."
            ),
            "hero_image_query": "dredging tomato slices in flour",
            "link_terms": ["dredge", "dredges", "dredged", "dredging"],
            "direct_answer": (
                "Dredging means coating food lightly in a dry ingredient, "
                "usually flour, cornmeal, or breadcrumbs, before cooking, "
                "most often as the first layer in a multi-step breading "
                "process."
            ),
            "expanded_explanation": (
                "In a classic three-step breading (flour, then egg, then a "
                "coarser coating like cornmeal or breadcrumbs), dredging "
                "refers specifically to that first flour layer. The thin, "
                "dry coating gives the wet egg wash something to cling to, "
                "which in turn gives the final coarse layer something to "
                "bind to, each layer depends on the one before it."
            ),
            "usage_origin": (
                "Common for fried foods like fried green tomatoes, fried "
                "chicken, and schnitzel, and for lightly flouring meat or "
                "fish before pan-searing to help it brown evenly."
            ),
            "substitute_note": (
                "No real substitute if a recipe calls for it specifically, "
                "the coating is what gives the fried food its crust. In a "
                "pinch, a shaker bag (the dry ingredient and flour, shaken "
                "together in a bag) works instead of a shallow dish."
            ),
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Do I have to dredge in a separate dish?",
                    "answer": (
                        "It's easiest with a shallow dish or plate so you "
                        "can press each piece into an even, thin layer, a "
                        "deep bowl makes it harder to coat evenly and easier "
                        "to clump the flour."
                    ),
                },
                {
                    "question": "What happens if I skip the dredging step in a breading?",
                    "answer": (
                        "The egg wash won't have anything to grip, and the "
                        "final coarse coating tends to slide off or clump "
                        "unevenly instead of forming a solid, even crust."
                    ),
                },
            ],
            "related_recipe_slugs": ["fried-green-tomatoes"],
        },
    },
    {
        "slug": "what-is-basting",
        "template_type": "definition",
        "title": "What Is Basting?",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Basting means spooning or brushing liquid over food as it "
                "cooks, to add flavor and moisture to the surface. How and "
                "when to do it safely."
            ),
            "hero_image_query": "basting chicken with a spoon",
            "link_terms": ["baste", "bastes", "basted", "basting"],
            "direct_answer": (
                "Basting means spooning, brushing, or squeezing liquid, "
                "usually pan juices, melted butter, or a marinade, over "
                "food as it cooks, to add flavor and moisture to the "
                "surface."
            ),
            "expanded_explanation": (
                "Basting doesn't cook food from the inside out the way "
                "marinating does, it works on the exposed surface, building "
                "flavor and a glossy finish as the liquid partially reduces "
                "and caramelizes with each pass. It's typically done a few "
                "times near the end of cooking rather than continuously, "
                "since opening an oven or lifting food off a hot pan too "
                "often can slow cooking or dry out the surface between "
                "bastes."
            ),
            "usage_origin": (
                "Common for roasted or grilled meats (turkey, chicken, "
                "ribs) and pan-seared fish or steak finished with butter, "
                "where a spoon repeatedly pools melted butter over the food "
                "as it cooks."
            ),
            "substitute_note": (
                "A spoon works fine if you don't have a basting brush or "
                "bulb baster, just tilt the pan slightly to pool the liquid "
                "and spoon it over."
            ),
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Is it safe to baste with a marinade the raw meat sat in?",
                    "answer": (
                        "Only if it's brought to a full boil first, to kill "
                        "any bacteria transferred from the raw meat. Using a "
                        "separate, reserved portion of marinade set aside "
                        "before the raw meat went in avoids the issue "
                        "entirely."
                    ),
                },
                {
                    "question": "Do I need a basting brush?",
                    "answer": (
                        "No, a large spoon works fine, tilt the pan slightly "
                        "so the liquid pools on one side, then spoon it over "
                        "the food repeatedly."
                    ),
                },
            ],
            "related_recipe_slugs": ["peri-peri-chicken", "chilean-sea-bass"],
        },
    },
    {
        "slug": "what-is-searing",
        "template_type": "definition",
        "title": "What Is Searing?",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Searing means cooking a food's surface over high heat "
                "until it browns deeply, without necessarily cooking it "
                "through. Why it works and how to get it right."
            ),
            "hero_image_query": "searing a steak in a hot pan",
            "link_terms": ["sear", "sears", "seared", "searing"],
            "direct_answer": (
                "Searing means cooking food's surface, usually meat or "
                "fish, over high heat until it develops a deep brown, "
                "flavorful crust, without necessarily cooking it all the "
                "way through."
            ),
            "expanded_explanation": (
                "The browning comes from the Maillard reaction, a chemical "
                "reaction between proteins and sugars that only happens at "
                "high temperatures, which is why a hot, dry pan matters "
                "more than cook time. A wet surface, a crowded pan, or "
                "moving the food too soon all lower the pan's effective "
                "temperature and prevent a real sear from forming, food "
                "ends up steaming and graying instead of browning."
            ),
            "usage_origin": (
                "Used at the start of a braise (searing meat before it "
                "simmers for hours) or as the entire cooking method for a "
                "quick-cooking cut like a thin steak or fish fillet, where "
                "the sear itself is most of the cooking."
            ),
            "substitute_note": (
                "There isn't a real substitute for a hot, dry pan, a "
                "nonstick pan can be used but won't develop as deep a crust "
                "as stainless steel or cast iron."
            ),
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Why isn't my food browning even though the pan is hot?",
                    "answer": (
                        "Usually surface moisture, pat food very dry before "
                        "it goes in the pan, since any water on the surface "
                        "has to evaporate first before browning can start, "
                        "which wastes the pan's heat and buys time for the "
                        "food to steam instead."
                    ),
                },
                {
                    "question": "Do I need to sear food all the way through?",
                    "answer": (
                        "No, searing is about the surface. Thicker cuts "
                        "usually need to finish cooking through some other "
                        "way, in the oven, at a lower stovetop heat, or by "
                        "resting after a hard sear, depending on the cut."
                    ),
                },
            ],
            "related_recipe_slugs": ["chicken-al-pastor", "chilean-sea-bass"],
        },
    },
    {
        "slug": "what-is-whisking",
        "template_type": "definition",
        "title": "What Is Whisking?",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Whisking means rapidly beating ingredients to combine them "
                "smoothly and incorporate air. How it differs from stirring "
                "and whipping."
            ),
            "hero_image_query": "whisking eggs in a bowl",
            "link_terms": ["whisk", "whisks", "whisked", "whisking"],
            "direct_answer": (
                "Whisking means rapidly beating ingredients with a whisk "
                "(or fork) to combine them smoothly and incorporate air, "
                "more vigorous than stirring but lighter than whipping to "
                "full volume."
            ),
            "expanded_explanation": (
                "A whisk's thin wires move quickly through a mixture, "
                "breaking up lumps and blending ingredients, like eggs, or "
                "dry ingredients into wet, far more evenly than a spoon "
                "would. It also incorporates some air, useful for a lighter "
                "texture in things like beaten eggs or a smooth, lump-free "
                "sauce, without necessarily building the mixture to the "
                "full volume that whipping does."
            ),
            "usage_origin": (
                "Used for beating eggs, combining dry ingredients evenly "
                "before adding them to a batter, and smoothing out sauces, "
                "gravies, and dressings so no lumps remain."
            ),
            "substitute_note": (
                "A fork works for light mixing in a pinch, though it takes "
                "longer and won't incorporate air as effectively as a real "
                "whisk for tasks like beating eggs or whipping cream."
            ),
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "What's the difference between whisking and whipping?",
                    "answer": (
                        "Whisking generally means combining and lightening a "
                        "mixture; whipping specifically means beating a "
                        "mixture like cream or egg whites until it holds a "
                        "defined shape, like soft or stiff peaks. Both use "
                        "the same tool, but whipping goes further and takes "
                        "longer."
                    ),
                },
                {
                    "question": "Can I whisk by hand instead of using an electric mixer?",
                    "answer": (
                        "For light tasks like beating eggs or smoothing a "
                        "sauce, yes, easily. For building real volume, like "
                        "whipping cream to stiff peaks, it's possible by "
                        "hand but takes several minutes of steady, vigorous "
                        "effort."
                    ),
                },
            ],
            "related_recipe_slugs": [],
        },
    },
    {
        "slug": "what-is-whipping",
        "template_type": "definition",
        "title": "What Is Whipping?",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Whipping means beating cream or egg whites until they trap "
                "enough air to hold a shape, like soft or stiff peaks. How "
                "it works and common mistakes."
            ),
            "hero_image_query": "whipping cream to stiff peaks",
            "link_terms": ["whip", "whips", "whipped", "whipping"],
            "direct_answer": (
                "Whipping means beating an ingredient, most often cream or "
                "egg whites, vigorously and continuously until it traps "
                "enough air to hold a defined shape, like soft or stiff "
                "peaks."
            ),
            "expanded_explanation": (
                "As a whisk or mixer repeatedly moves through cream or egg "
                "whites, it traps tiny air bubbles that get stabilized by "
                "the fat (in cream) or proteins (in egg whites), gradually "
                "building volume and structure. Soft peaks droop over when "
                "the whisk is lifted; stiff peaks hold their shape upright. "
                "Whipping past stiff peaks turns cream grainy and eventually "
                "into butter, and turns egg whites dry and clumpy, so most "
                "recipes specify exactly how far to take it."
            ),
            "usage_origin": (
                "Used for whipped cream (as a topping or folded into a "
                "mousse or no-churn ice cream base) and beaten egg whites "
                "(for meringues, soufflés, and some cake batters)."
            ),
            "substitute_note": (
                "A hand mixer or stand mixer speeds this up considerably; "
                "by hand with a whisk it's possible but takes several "
                "minutes of steady effort to reach stiff peaks."
            ),
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Why won't my cream whip up?",
                    "answer": (
                        "It's almost always temperature, cream whips "
                        "fastest and holds its structure best when it's "
                        "cold, along with the bowl and beaters. Warm cream "
                        "takes much longer and can go straight to grainy or "
                        "buttery without ever holding a clean peak."
                    ),
                },
                {
                    "question": "What happens if I overwhip cream?",
                    "answer": (
                        "It turns grainy and separated, and if it goes "
                        "further, into butter and buttermilk. There's no way "
                        "to bring it back to smooth whipped cream once that "
                        "happens, only to stop and start over with fresh "
                        "cream."
                    ),
                },
            ],
            "related_recipe_slugs": ["mango-ice-cream"],
        },
    },
    {
        "slug": "what-is-zesting",
        "template_type": "definition",
        "title": "What Is Zesting?",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Zesting means removing just the thin, colorful outer peel "
                "of a citrus fruit, without the bitter white pith "
                "underneath. How and why to do it."
            ),
            "hero_image_query": "zesting a lemon with a microplane",
            "link_terms": ["zest", "zests", "zested", "zesting"],
            "direct_answer": (
                "Zesting means removing just the thin, colorful outer layer "
                "of a citrus fruit's peel, the part packed with aromatic "
                "oils, without digging into the bitter white pith "
                "underneath."
            ),
            "expanded_explanation": (
                "Citrus zest carries a concentrated version of the fruit's "
                "flavor and aroma, far more intense than the juice alone, "
                "because that's where the fruit's aromatic oils are stored. "
                "The white pith just beneath the zest is bitter and best "
                "avoided, which is why zesting tools (a fine grater or a "
                "citrus zester) are designed to shave off only that thin "
                "colored layer."
            ),
            "usage_origin": (
                "Used to add bright citrus flavor to baked goods, rice "
                "puddings, marinades, and cocktails, either grated directly "
                "into a mixture or as a garnish, and often alongside the "
                "fruit's juice for a fuller citrus flavor than juice "
                "provides alone."
            ),
            "substitute_note": (
                "A fine grater like a Microplane gives the finest, most "
                "even zest. A vegetable peeler works too, remove the peel "
                "in strips, then mince it finely, though the texture is "
                "coarser."
            ),
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Do I need a special tool to zest citrus?",
                    "answer": (
                        "A fine grater like a Microplane gives the finest, "
                        "most even zest. A vegetable peeler works too, "
                        "remove the peel in strips, then mince it finely, "
                        "though the texture is coarser."
                    ),
                },
                {
                    "question": "Can I zest a fruit and juice it too?",
                    "answer": (
                        "Yes, and it's the efficient order to do both, zest "
                        "the fruit first while it's whole and easier to "
                        "grip, then juice it."
                    ),
                },
            ],
            "related_recipe_slugs": ["arroz-con-leche"],
        },
    },
    {
        "slug": "what-is-a-dry-shake",
        "template_type": "definition",
        "title": "What Is a Dry Shake?",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "A dry shake is a cocktail technique that shakes egg white "
                "or aquafaba without ice first, to build a stable foam. "
                "Why it matters and how it works."
            ),
            "hero_image_query": "cocktail shaker with egg white foam",
            "link_terms": ["dry shake"],
            "direct_answer": (
                "A dry shake is a cocktail technique where ingredients, "
                "especially egg white or aquafaba, are shaken vigorously in "
                "a cocktail shaker without ice, to whip the egg white into "
                "a stable foam before the drink is chilled."
            ),
            "expanded_explanation": (
                "Shaking with ice at the same time as the egg white dilutes "
                "and chills the mixture before the egg white has a chance "
                "to whip up properly, so the foam never fully forms. A dry "
                "shake solves this by whipping the egg white first, "
                "undiluted, then a second wet shake with ice follows to "
                "chill and dilute the drink to a proper strength once the "
                "foam is already built."
            ),
            "usage_origin": (
                "Standard for egg-white cocktails like an amaretto sour or "
                "whiskey sour, and their vegan aquafaba-based versions, "
                "anywhere a recipe wants a stable, silky foam on top of the "
                "drink."
            ),
            "substitute_note": (
                "There's no real substitute if a recipe specifically calls "
                "for it, the technique is what builds an egg-white or "
                "aquafaba foam before the drink is chilled and diluted with "
                "ice."
            ),
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "Can I skip the dry shake and just shake with ice?",
                    "answer": (
                        "You can, but the drink usually comes out thinner "
                        "and less foamy, the ice dilutes and chills the "
                        "mixture before the egg white gets fully whipped, so "
                        "the foam that does form tends to be thin and "
                        "short-lived."
                    ),
                },
                {
                    "question": "How long should a dry shake take?",
                    "answer": (
                        "About 15-20 seconds of vigorous shaking, longer "
                        "than a normal wet shake, since building real foam "
                        "from raw egg white or aquafaba takes more agitation "
                        "than just chilling a drink does."
                    ),
                },
            ],
            "related_recipe_slugs": ["amaretto-sour"],
        },
    },
    {
        "slug": "what-is-rehydrating",
        "template_type": "definition",
        "title": "What Is Rehydrating?",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Rehydrating means soaking a dried ingredient, like dried "
                "chiles or mushrooms, until it softens back toward its "
                "original texture. How and why it's done."
            ),
            "hero_image_query": "dried chiles soaking in hot water",
            "link_terms": ["rehydrate", "rehydrates", "rehydrated", "rehydrating"],
            "direct_answer": (
                "Rehydrating means soaking a dried ingredient, most often "
                "dried chiles, mushrooms, or fruit, in a liquid, usually "
                "hot water, until it softens back toward its original "
                "texture before cooking with it."
            ),
            "expanded_explanation": (
                "Drying removes most of an ingredient's water content, "
                "which concentrates its flavor but leaves it tough, "
                "brittle, or leathery. Soaking it in hot water, or another "
                "liquid like broth, lets it reabsorb moisture and soften "
                "enough to blend smoothly or chew comfortably, hot liquid "
                "works faster than cold since heat speeds up how quickly "
                "the dried tissue reabsorbs water."
            ),
            "usage_origin": (
                "Common for dried chiles before blending into a marinade or "
                "sauce (like guajillo chiles in an al pastor marinade), "
                "dried mushrooms before adding to a broth or filling, and "
                "dried fruit before baking with it."
            ),
            "substitute_note": (
                "Hot water works faster than cold; for chiles specifically, "
                "toasting them briefly in a dry pan first, until fragrant, "
                "not burnt, deepens their flavor before soaking."
            ),
            "substitute_page_slug": None,
            "faqs": [
                {
                    "question": "How long does rehydrating usually take?",
                    "answer": (
                        "For dried chiles, about 10-15 minutes in hot water "
                        "is typical. Tougher or larger dried ingredients, "
                        "like whole dried mushrooms, can take 20-30 minutes "
                        "or longer to fully soften."
                    ),
                },
                {
                    "question": "Can I use the soaking liquid afterward?",
                    "answer": (
                        "Often yes, and it's worth saving, it picks up "
                        "flavor from whatever was soaking in it and can be "
                        "strained and used as a base for a sauce or broth "
                        "instead of being poured out."
                    ),
                },
            ],
            "related_recipe_slugs": ["chicken-al-pastor"],
        },
    },
    {
        "slug": "gelato-vs-ice-cream",
        "template_type": "comparison",
        "title": "Gelato vs. Ice Cream: What's the Difference?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Gelato vs. ice cream: the real differences are butterfat, "
                "churning speed, and serving temperature, not just the name."
            ),
            "hero_image_query": "gelato and ice cream side by side",
            "item_a_name": "Gelato",
            "item_b_name": "Ice Cream",
            "comparison_table": [
                {"attribute": "Milk-to-cream ratio", "item_a": "More milk, less cream", "item_b": "More cream, less milk"},
                {"attribute": "Churning speed", "item_a": "Slow, less air incorporated", "item_b": "Fast, more air incorporated"},
                {"attribute": "Serving temperature", "item_a": "Warmer, around 10-15°F (-12 to -9°C)", "item_b": "Colder, around 0-5°F (-18 to -15°C)"},
                {"attribute": "Texture", "item_a": "Dense, intensely flavored", "item_b": "Lighter, airier"},
                {"attribute": "Typical fat content", "item_a": "Roughly 4-8%", "item_b": "Roughly 10-18%"},
            ],
            "verdict": (
                "Neither is objectively better, gelato delivers more "
                "concentrated flavor per bite and a denser texture, while ice "
                "cream's higher fat and air content give it a lighter, richer "
                "mouthfeel. Preference comes down to whether you want intensity "
                "or richness."
            ),
            "sections": [
                {
                    "heading": "Gelato",
                    "body": (
                        "Made with more milk than cream and churned slowly at "
                        "low speed, gelato traps less air, which is why it "
                        "tastes so much more intensely flavored, there's "
                        "simply less air diluting each bite."
                    ),
                },
                {
                    "heading": "Ice Cream",
                    "body": (
                        "Higher cream content and faster churning incorporate "
                        "more air (\"overrun\"), producing a lighter, fluffier "
                        "texture, and it's served notably colder, which is why "
                        "gelato feels softer straight out of the case."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "Is gelato lower in calories than ice cream?",
                    "answer": (
                        "Often, since it typically uses less cream, but it "
                        "varies by recipe, always check labels rather than "
                        "assuming, since some gelato is made quite rich."
                    ),
                },
                {
                    "question": "Can I make gelato in a regular ice cream maker?",
                    "answer": (
                        "Yes, use a milk-forward base and churn at the "
                        "machine's slower setting if it has one, then serve it "
                        "slightly warmer than you would ice cream for the "
                        "right texture."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "baking-powder-vs-baking-soda",
        "template_type": "comparison",
        "title": "Baking Powder vs. Baking Soda: What's the Difference?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Baking powder vs. baking soda: they're not interchangeable. "
                "The real difference is whether an acid is already built in."
            ),
            "hero_image_query": "baking powder and baking soda side by side",
            "item_a_name": "Baking Powder",
            "item_b_name": "Baking Soda",
            "comparison_table": [
                {"attribute": "Composition", "item_a": "Baking soda + a built-in dry acid", "item_b": "Pure sodium bicarbonate"},
                {"attribute": "Needs an acidic ingredient?", "item_a": "No, it's self-contained", "item_b": "Yes, needs buttermilk, lemon juice, etc."},
                {"attribute": "Leavening strength", "item_a": "Weaker per volume", "item_b": "About 3-4x stronger per volume"},
                {"attribute": "Common uses", "item_a": "Cakes, pancakes, biscuits with no acidic ingredient", "item_b": "Recipes already containing buttermilk, yogurt, cocoa, or citrus"},
            ],
            "verdict": (
                "Use baking soda when the recipe already has an acidic "
                "ingredient for it to react with; use baking powder when it "
                "doesn't. Many recipes actually use both, for different "
                "reasons, baking soda to neutralize acid and add browning, "
                "baking powder for the actual lift."
            ),
            "sections": [
                {
                    "heading": "Baking Powder",
                    "body": (
                        "A complete leavening system on its own: it pairs "
                        "sodium bicarbonate with a powdered acid (like cream of "
                        "tartar), so it reacts with moisture and heat alone, "
                        "without needing an acidic ingredient elsewhere in the "
                        "recipe."
                    ),
                },
                {
                    "heading": "Baking Soda",
                    "body": (
                        "Pure sodium bicarbonate, roughly 3-4 times stronger "
                        "than baking powder by volume, but it needs an acidic "
                        "ingredient in the batter to trigger the reaction that "
                        "produces lift."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "What happens if I use baking soda instead of baking powder?",
                    "answer": (
                        "Without an acidic ingredient to react with, the baking "
                        "soda mostly won't activate, and what little does react "
                        "can leave a metallic, soapy taste, the two aren't a "
                        "safe 1:1 swap."
                    ),
                },
                {
                    "question": "Why do some recipes use both baking powder and baking soda?",
                    "answer": (
                        "The baking soda neutralizes the recipe's acidic "
                        "ingredients (which also helps browning), while the "
                        "baking powder provides the actual leavening lift, "
                        "they're doing two different jobs, not duplicating one."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "yam-vs-sweet-potato",
        "template_type": "comparison",
        "title": "Yam vs. Sweet Potato: What's the Difference?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Yam vs. sweet potato: in most US grocery stores, they're both "
                "sweet potatoes. The real botanical difference explained."
            ),
            "hero_image_query": "yam and sweet potato side by side",
            "item_a_name": "Yam",
            "item_b_name": "Sweet Potato",
            "comparison_table": [
                {"attribute": "Plant family", "item_a": "Dioscoreaceae (a monocot)", "item_b": "Convolvulaceae, the morning glory family (a dicot)"},
                {"attribute": "Skin", "item_a": "Rough, bark-like, hard to peel raw", "item_b": "Thin, smooth"},
                {"attribute": "Flesh", "item_a": "Starchy, dry, white to purple", "item_b": "Moist, sweet, orange (most common variety)"},
                {"attribute": "US grocery labeling", "item_a": "Rare, true yams are uncommon in US stores", "item_b": "What's almost always sold as \"yam\" in the US"},
            ],
            "verdict": (
                "If you bought it at a typical US supermarket labeled \"yam,\" "
                "it's almost certainly a sweet potato, true yams are a "
                "different plant entirely and are mostly found in African, "
                "Caribbean, and Asian specialty markets."
            ),
            "sections": [
                {
                    "heading": "Yam",
                    "body": (
                        "A true yam is a starchy tuber from a completely "
                        "different plant family than the sweet potato, with "
                        "rough, bark-like skin and drier, starchier flesh. "
                        "They're a staple crop across Africa, the Caribbean, "
                        "and parts of Asia."
                    ),
                },
                {
                    "heading": "Sweet Potato",
                    "body": (
                        "What most people in the US actually mean by \"yam\", "
                        "a naturally sweet root vegetable with moist, orange "
                        "flesh (though white and purple varieties exist too), "
                        "from a completely different plant family than true yams."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "Why does the US mislabel sweet potatoes as yams?",
                    "answer": (
                        "When orange-fleshed sweet potatoes were introduced to "
                        "US markets, producers used \"yam\" to distinguish them "
                        "from the paler sweet potato varieties already sold, "
                        "the label stuck even though true yams are a different "
                        "plant entirely."
                    ),
                },
                {
                    "question": "Can I substitute one for the other in a recipe?",
                    "answer": (
                        "In practice, most US recipes calling for \"yams\" mean "
                        "sweet potatoes and the two are used interchangeably in "
                        "American cooking, true yams, when available, behave "
                        "differently (starchier, less sweet) and may need "
                        "adjusted cook times."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "bourbon-vs-whiskey",
        "template_type": "comparison",
        "title": "Bourbon vs. Whiskey: What's the Difference?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Bourbon vs. whiskey: bourbon is a legally defined type of "
                "whiskey, not a separate category. What actually makes it "
                "bourbon."
            ),
            "hero_image_query": "bourbon and whiskey glasses",
            "item_a_name": "Bourbon",
            "item_b_name": "Whiskey",
            "comparison_table": [
                {"attribute": "Category", "item_a": "A specific type of whiskey", "item_b": "The broad category bourbon belongs to"},
                {"attribute": "Grain requirement", "item_a": "At least 51% corn", "item_b": "Varies, rye, barley, wheat, corn, or blends"},
                {"attribute": "Where it can be made", "item_a": "Must be made in the United States", "item_b": "Made worldwide (Scotch, Irish, Japanese, etc.)"},
                {"attribute": "Barrel requirement", "item_a": "New, charred oak barrels only", "item_b": "Varies by style and country"},
            ],
            "verdict": (
                "Every bourbon is a whiskey, but not every whiskey is a "
                "bourbon, bourbon is a legally defined American style with "
                "specific requirements (corn content, new charred oak barrels, "
                "US production) that most other whiskeys don't have to meet."
            ),
            "sections": [
                {
                    "heading": "Bourbon",
                    "body": (
                        "By US federal regulation, bourbon must be made in the "
                        "United States from a mash of at least 51% corn, aged "
                        "in new, charred oak barrels, and meet specific "
                        "distillation and bottling proof limits."
                    ),
                },
                {
                    "heading": "Whiskey",
                    "body": (
                        "The umbrella term for any spirit distilled from "
                        "fermented grain mash and aged in wood, Scotch, Irish "
                        "whiskey, rye, and bourbon are all whiskeys, each with "
                        "their own specific production rules."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "Does bourbon have to be made in Kentucky?",
                    "answer": (
                        "No, that's a common myth, bourbon can legally be made "
                        "anywhere in the United States. Kentucky produces the "
                        "large majority of it by tradition and industry "
                        "concentration, not legal requirement."
                    ),
                },
                {
                    "question": "Is Tennessee whiskey the same as bourbon?",
                    "answer": (
                        "Tennessee whiskey meets bourbon's legal requirements "
                        "but adds an extra charcoal-filtering step (the "
                        "Lincoln County Process) and must be made in Tennessee, "
                        "which is why it's labeled as its own category rather "
                        "than simply called bourbon."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "kosher-salt-vs-sea-salt",
        "template_type": "comparison",
        "title": "Kosher Salt vs. Sea Salt: What's the Difference?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Kosher salt vs. sea salt: the real differences are crystal "
                "shape, density, and source, and why they aren't "
                "interchangeable by volume."
            ),
            "hero_image_query": "kosher salt and sea salt side by side",
            "item_a_name": "Kosher Salt",
            "item_b_name": "Sea Salt",
            "comparison_table": [
                {"attribute": "Source", "item_a": "Mined or evaporated, processed into large flakes", "item_b": "Evaporated directly from seawater"},
                {"attribute": "Crystal shape", "item_a": "Large, irregular flakes", "item_b": "Varies, fine to coarse, often more uniform"},
                {"attribute": "Additives", "item_a": "Usually none", "item_b": "Usually none, though iodized versions exist for both"},
                {"attribute": "Density (same volume)", "item_a": "Less dense, less salt by weight per cup", "item_b": "More dense, more salt by weight per cup"},
            ],
            "verdict": (
                "For cooking, kosher salt's large, easy-to-pinch flakes make "
                "it the preferred everyday salt among professional cooks. Sea "
                "salt's denser crystals (and sometimes trace minerals) make it "
                "a better finishing salt where you want a bit of crunch and "
                "flavor on top of the dish."
            ),
            "sections": [
                {
                    "heading": "Kosher Salt",
                    "body": (
                        "Named for its historical use in the koshering "
                        "(salting) process for meat, not because it's "
                        "inherently more kosher than other salt. Its large, "
                        "flat, irregular crystals are easy to pinch and "
                        "distribute evenly, which is why it's the default in "
                        "most professional kitchens."
                    ),
                },
                {
                    "heading": "Sea Salt",
                    "body": (
                        "Evaporated directly from seawater rather than mined or "
                        "further processed, sea salt ranges from fine to very "
                        "coarse and can carry trace minerals that add subtle "
                        "flavor and color variations depending on its source."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "Can I substitute kosher salt and sea salt 1:1?",
                    "answer": (
                        "Not reliably by volume, their crystal sizes differ "
                        "enough that a tablespoon of one can weigh noticeably "
                        "more or less than a tablespoon of the other. Weighing "
                        "salt, or adjusting to taste, is more reliable than a "
                        "straight volume swap."
                    ),
                },
                {
                    "question": "Why do recipes specifically call for kosher salt?",
                    "answer": (
                        "Its large, consistent flakes make measuring and "
                        "seasoning by feel (pinching) more predictable than "
                        "with fine table salt, which packs much more densely "
                        "into the same volume and can easily over-salt a dish."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "jam-vs-jelly",
        "template_type": "comparison",
        "title": "Jam vs. Jelly: What's the Difference?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Jam vs. jelly: the difference is what part of the fruit goes "
                "in, crushed fruit versus strained juice."
            ),
            "hero_image_query": "jam and jelly jars side by side",
            "item_a_name": "Jam",
            "item_b_name": "Jelly",
            "comparison_table": [
                {"attribute": "Made from", "item_a": "Crushed or chopped whole fruit", "item_b": "Strained fruit juice only"},
                {"attribute": "Texture", "item_a": "Chunky to soft-set, some fruit pieces", "item_b": "Smooth, firm, translucent"},
                {"attribute": "Seeds/skins", "item_a": "Often present", "item_b": "Removed by straining"},
                {"attribute": "Set", "item_a": "Softer, spreadable", "item_b": "Firmer, holds a distinct shape when unmolded"},
            ],
            "verdict": (
                "Jam keeps the fruit's texture and is the more versatile "
                "everyday spread; jelly is smoother and firmer, better suited "
                "to recipes wanting a clean, jiggly set with no fruit pieces."
            ),
            "sections": [
                {
                    "heading": "Jam",
                    "body": (
                        "Made by cooking crushed or chopped fruit with sugar "
                        "(and often pectin) until thickened, the fruit pieces "
                        "themselves remain in the final product, giving jam its "
                        "characteristic chunky, spreadable texture."
                    ),
                },
                {
                    "heading": "Jelly",
                    "body": (
                        "Made from fruit juice that's been strained clear of "
                        "pulp, seeds, and skins before being cooked with sugar "
                        "and pectin, producing a smooth, firm, translucent set."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "Can I use jam and jelly interchangeably in a recipe?",
                    "answer": (
                        "For most everyday uses (toast, PB&J) yes, but for "
                        "recipes that specifically want a smooth glaze or a "
                        "clean unmolded shape, jelly's firmer, pulp-free set "
                        "works better than jam's chunkier texture."
                    ),
                },
                {
                    "question": "What is preserves, then?",
                    "answer": (
                        "Preserves contain even larger, often whole pieces of "
                        "fruit suspended in a light syrup or gel, making them "
                        "chunkier than jam, which typically uses crushed rather "
                        "than whole fruit."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "parsley-vs-cilantro",
        "template_type": "comparison",
        "title": "Parsley vs. Cilantro: What's the Difference?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Parsley vs. cilantro: they look almost identical but taste "
                "completely different. How to tell them apart and when to use "
                "each."
            ),
            "hero_image_query": "parsley and cilantro side by side",
            "item_a_name": "Parsley",
            "item_b_name": "Cilantro",
            "comparison_table": [
                {"attribute": "Leaf shape", "item_a": "Pointed, more jagged edges", "item_b": "Rounder, more scalloped edges"},
                {"attribute": "Flavor", "item_a": "Mild, slightly peppery, grassy", "item_b": "Bright, citrusy, or soapy to a genetic subset of people"},
                {"attribute": "Common cuisines", "item_a": "Mediterranean, European", "item_b": "Mexican, Southeast Asian, Indian"},
                {"attribute": "Stems", "item_a": "Tougher, often discarded", "item_b": "Tender, often used along with the leaves"},
            ],
            "verdict": (
                "They're easy to mix up by sight in a grocery bin, but the "
                "flavor difference is unmistakable once tasted. Use parsley "
                "for a mild, background herbal note; use cilantro when the "
                "recipe wants its distinct bright, citrusy punch."
            ),
            "sections": [
                {
                    "heading": "Parsley",
                    "body": (
                        "A mild, versatile herb used across Mediterranean and "
                        "European cooking, often as a background flavor or "
                        "garnish rather than a dominant note. Flat-leaf "
                        "(Italian) parsley has more flavor than curly parsley, "
                        "which is mostly used for garnish."
                    ),
                },
                {
                    "heading": "Cilantro",
                    "body": (
                        "The leaves of the coriander plant, with a bright, "
                        "citrusy flavor central to Mexican, Indian, and "
                        "Southeast Asian cooking. A genetic variant makes it "
                        "taste soapy and unpleasant to a meaningful minority of "
                        "people, which is why reactions to it are so polarized."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "Why does cilantro taste like soap to some people?",
                    "answer": (
                        "A genetic variant related to olfactory receptor genes "
                        "makes some people perceive the aldehydes in cilantro as "
                        "soapy rather than citrusy, it's a real, documented "
                        "genetic difference, not just pickiness."
                    ),
                },
                {
                    "question": "Can I substitute parsley for cilantro in a recipe?",
                    "answer": (
                        "You can for a similar visual garnish, but the flavor "
                        "will be quite different, parsley lacks cilantro's "
                        "bright, citrusy character entirely, so it's a "
                        "substitution of convenience, not a flavor match."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "oat-milk-vs-almond-milk",
        "template_type": "comparison",
        "title": "Oat Milk vs. Almond Milk: What's the Difference?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Oat milk vs. almond milk: how they compare on taste, "
                "nutrition, and how well each froths and bakes."
            ),
            "hero_image_query": "oat milk and almond milk cartons",
            "item_a_name": "Oat Milk",
            "item_b_name": "Almond Milk",
            "comparison_table": [
                {"attribute": "Base ingredient", "item_a": "Blended oats and water", "item_b": "Blended almonds and water"},
                {"attribute": "Texture", "item_a": "Creamier, naturally thicker", "item_b": "Thinner, more watery"},
                {"attribute": "Calories (typical, per cup)", "item_a": "~120", "item_b": "~30-40 (unsweetened)"},
                {"attribute": "Frothing for coffee", "item_a": "Froths well, closer to dairy", "item_b": "Froths less well, can separate"},
                {"attribute": "Common allergen concerns", "item_a": "Gluten cross-contamination possible unless certified gluten-free", "item_b": "Tree nut allergy"},
            ],
            "verdict": (
                "Oat milk's creamier texture makes it the better choice for "
                "coffee drinks and baking; almond milk's lower calorie count "
                "makes it appealing for those watching calorie intake. Neither "
                "is nutritionally a like-for-like replacement for dairy milk's "
                "protein content."
            ),
            "sections": [
                {
                    "heading": "Oat Milk",
                    "body": (
                        "Made by blending oats with water and straining, oat "
                        "milk has a naturally creamy texture and mild sweetness "
                        "that froths and steams closer to dairy milk than most "
                        "other plant milks, part of why it's become popular "
                        "in coffee shops specifically."
                    ),
                },
                {
                    "heading": "Almond Milk",
                    "body": (
                        "Made from blended almonds and water, almond milk is "
                        "thinner and lower in calories than oat milk, with a "
                        "mild, slightly nutty flavor, but it's not an option for "
                        "anyone with a tree nut allergy."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "Which one is better for coffee?",
                    "answer": (
                        "Oat milk generally froths and steams better, giving a "
                        "creamier latte texture closer to dairy milk. Almond "
                        "milk can curdle or separate in hot, acidic coffee more "
                        "easily than oat milk."
                    ),
                },
                {
                    "question": "Is either one a good source of protein like dairy milk?",
                    "answer": (
                        "No, both are notably lower in protein than dairy "
                        "milk (roughly 2-3g per cup versus dairy's 8g). Soy "
                        "milk is the plant-based option closest to dairy's "
                        "protein content."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "prawn-vs-shrimp",
        "template_type": "comparison",
        "title": "Prawn vs. Shrimp: What's the Difference?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Prawn vs. shrimp: there's a real biological difference, but "
                "the words are also used regionally and interchangeably. Both "
                "explained."
            ),
            "hero_image_query": "prawns and shrimp side by side",
            "item_a_name": "Prawn",
            "item_b_name": "Shrimp",
            "comparison_table": [
                {"attribute": "Biological classification", "item_a": "Different suborder (Dendrobranchiata)", "item_b": "Different suborder (Pleocyemata)"},
                {"attribute": "Gill structure", "item_a": "Branching gills", "item_b": "Lamellar (plate-like) gills"},
                {"attribute": "Body shape", "item_a": "Straighter body segments", "item_b": "More curled body segments"},
                {"attribute": "Common usage", "item_a": "\"Prawn\" common in UK, Australia, and India, often for larger specimens", "item_b": "\"Shrimp\" common in US, often used generically"},
            ],
            "verdict": (
                "Biologically, they're genuinely different suborders of "
                "crustacean. Commercially and in most kitchens, though, the "
                "terms are used loosely and often interchangeably, especially "
                "by size (bigger ones get called \"prawns\" regardless of "
                "actual species) rather than strict taxonomy."
            ),
            "sections": [
                {
                    "heading": "Prawn",
                    "body": (
                        "Biologically distinct from shrimp, with branching "
                        "gills and straighter body segments. \"Prawn\" is the "
                        "more common everyday term in the UK, Australia, and "
                        "India, and is often applied to larger specimens "
                        "regardless of true species."
                    ),
                },
                {
                    "heading": "Shrimp",
                    "body": (
                        "The more common term in North America, used broadly "
                        "for both true shrimp and, commercially, for what would "
                        "biologically be classified as prawns, the culinary "
                        "usage doesn't track the scientific distinction closely."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "Can I use prawns and shrimp interchangeably in a recipe?",
                    "answer": (
                        "Yes, for virtually all cooking purposes, the flavor "
                        "and cooking behavior are close enough that recipes "
                        "don't meaningfully distinguish between them, whichever "
                        "term the recipe or the market uses."
                    ),
                },
                {
                    "question": "Why does the US mostly say \"shrimp\" and other countries say \"prawn\"?",
                    "answer": (
                        "It's largely a matter of regional culinary tradition "
                        "and marketing history rather than a strict rule, both "
                        "true shrimp and true prawns are sold and eaten "
                        "everywhere, but the common name that stuck varies by "
                        "region."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "white-pepper-vs-black-pepper",
        "template_type": "comparison",
        "title": "White Pepper vs. Black Pepper: What's the Difference?",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "White pepper vs. black pepper: same plant, different "
                "processing, and a real difference in flavor and best uses."
            ),
            "hero_image_query": "white pepper and black pepper side by side",
            "item_a_name": "White Pepper",
            "item_b_name": "Black Pepper",
            "comparison_table": [
                {"attribute": "Source", "item_a": "Same plant (Piper nigrum), fully ripened, outer skin removed", "item_b": "Same plant, unripe berries, dried whole with skin on"},
                {"attribute": "Flavor", "item_a": "Milder, more fermented/earthy", "item_b": "Sharper, more floral and pungent"},
                {"attribute": "Color in dishes", "item_a": "Invisible in light-colored sauces", "item_b": "Visible dark flecks"},
                {"attribute": "Common cuisines", "item_a": "Chinese, Thai, French white sauces", "item_b": "Used nearly universally"},
            ],
            "verdict": (
                "Use white pepper when you want pepper's heat without visible "
                "black specks, light-colored sauces, mashed potatoes, "
                "certain Asian soups. Use black pepper for its sharper, more "
                "aromatic flavor everywhere else."
            ),
            "sections": [
                {
                    "heading": "White Pepper",
                    "body": (
                        "Made from fully ripened peppercorns that have been "
                        "soaked to remove the dark outer skin before drying, "
                        "revealing the pale seed inside. The soaking process "
                        "gives it a milder, slightly fermented, earthier flavor "
                        "than black pepper."
                    ),
                },
                {
                    "heading": "Black Pepper",
                    "body": (
                        "Made from unripe green peppercorns, dried whole with "
                        "the skin intact, which darkens to black. The skin "
                        "contributes much of black pepper's sharper, more "
                        "floral and pungent flavor compared to white pepper."
                    ),
                },
            ],
            "faqs": [
                {
                    "question": "Is white pepper spicier than black pepper?",
                    "answer": (
                        "Not spicier overall, it's generally described as "
                        "milder and earthier, though it does carry a slightly "
                        "different, sometimes more musty heat than black "
                        "pepper's sharper bite."
                    ),
                },
                {
                    "question": "Why do Chinese and Thai recipes often call for white pepper specifically?",
                    "answer": (
                        "It's a traditional flavor choice in many East and "
                        "Southeast Asian dishes, and its lack of dark flecks "
                        "keeps light-colored soups, sauces, and stir-fries "
                        "visually clean, both a flavor and a presentation "
                        "reason."
                    ),
                },
            ],
            "item_a_link": None,
            "item_b_link": None,
        },
    },
    {
        "slug": "sour-cream-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Sour Cream",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Out of sour cream? Here are four ranked substitutes with exact "
                "ratios, for both baking and toppings."
            ),
            "hero_image_query": "sour cream in a bowl",
            "ranked_substitutes": [
                {"name": "Plain Greek yogurt", "ratio": "1:1", "best_for": "Both baking and toppings", "note": "Very close in tang and thickness; the closest all-around substitute."},
                {"name": "Crème fraîche", "ratio": "1:1", "best_for": "Cooking and sauces", "note": "Milder and richer, and won't curdle when heated the way sour cream can."},
                {"name": "Buttermilk", "ratio": "Use ¾ the amount, thinned slightly", "best_for": "Baking only", "note": "Adds similar tang but is much thinner, best in batters, not as a dollop-on-top topping."},
                {"name": "Mayonnaise", "ratio": "1:1", "best_for": "Cold dips and dressings only", "note": "Richer and less tangy; works for dips but not for baking, where it behaves very differently under heat."},
            ],
            "baking_vs_cooking_note": (
                "For baking, Greek yogurt or thinned buttermilk work best, "
                "they contribute similar moisture and acidity for leavening "
                "reactions. For hot sauces and soups, crème fraîche is the "
                "safest choice since it won't curdle the way sour cream and "
                "yogurt both can under high heat."
            ),
            "faqs": [
                {
                    "question": "Can I substitute Greek yogurt for sour cream in baking?",
                    "answer": (
                        "Yes, 1:1, Greek yogurt's thickness and tang are very "
                        "close to sour cream's, and it performs almost "
                        "identically in most baked goods."
                    ),
                },
                {
                    "question": "Why does my substitute curdle when I add it to a hot dish?",
                    "answer": (
                        "Lower-fat dairy substitutes (yogurt, buttermilk) are "
                        "more prone to curdling under high heat than sour "
                        "cream. Temper them by stirring in a little of the hot "
                        "liquid first, or add them off the heat at the end of "
                        "cooking."
                    ),
                },
            ],
            "hub_page_slug": None,
            "recipe_slugs": [],
        },
    },
    {
        "slug": "buttermilk-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Buttermilk",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Out of buttermilk? A simple milk-and-acid substitute works in "
                "minutes, plus other ranked options."
            ),
            "hero_image_query": "buttermilk in a glass",
            "ranked_substitutes": [
                {"name": "Milk + lemon juice or white vinegar", "ratio": "1 cup milk + 1 tbsp acid, rested 5-10 minutes", "best_for": "Both baking and cooking", "note": "The classic, near-universal substitute, the acid curdles the milk slightly, mimicking buttermilk's tang and thinness."},
                {"name": "Plain yogurt, thinned with milk", "ratio": "¾ cup yogurt + ¼ cup milk, whisked smooth", "best_for": "Baking", "note": "Close in tang and thickness once thinned; a very reliable substitute."},
                {"name": "Sour cream, thinned with milk", "ratio": "¾ cup sour cream + ¼ cup milk", "best_for": "Baking", "note": "Similar to the yogurt version, richer, but works the same way."},
                {"name": "Cream of tartar + milk", "ratio": "1¾ tsp cream of tartar per cup of milk", "best_for": "Baking, when no citrus or vinegar is on hand", "note": "A less common but effective acid source for the same curdling effect."},
            ],
            "baking_vs_cooking_note": (
                "All of these substitutes work for baking, where buttermilk's "
                "role is mainly acidity (to react with baking soda) and a "
                "little extra moisture. For drinking or a savory buttermilk "
                "dressing, the thinned yogurt or sour cream versions taste "
                "closer to the real thing than the milk-and-acid version."
            ),
            "faqs": [
                {
                    "question": "How long do I need to let the milk-and-acid mixture sit?",
                    "answer": (
                        "About 5-10 minutes at room temperature, it will look "
                        "slightly curdled and thickened, which is exactly the "
                        "texture you want before using it in the recipe."
                    ),
                },
                {
                    "question": "Can I use non-dairy milk to make a buttermilk substitute?",
                    "answer": (
                        "Yes, soy milk curdles most reliably with an acid "
                        "added, similar to dairy milk. Almond and oat milk work "
                        "too, though the curdling reaction is less pronounced."
                    ),
                },
            ],
            "hub_page_slug": None,
            "recipe_slugs": [],
        },
    },
    {
        "slug": "vanilla-extract-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Vanilla Extract",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Out of vanilla extract? Here are four ranked substitutes, "
                "including how much vanilla bean or paste to use instead."
            ),
            "hero_image_query": "vanilla extract bottle",
            "ranked_substitutes": [
                {"name": "Vanilla bean paste", "ratio": "1:1", "best_for": "Both baking and no-bake desserts", "note": "Nearly identical flavor to extract, with visible vanilla bean flecks as a bonus."},
                {"name": "Scraped vanilla bean pod", "ratio": "1 whole bean per teaspoon of extract called for", "best_for": "Custards, ice cream, and other cooked applications", "note": "The most intense, purest vanilla flavor, but more expensive and requires scraping out the seeds."},
                {"name": "Maple syrup", "ratio": "Use 2x the amount of extract called for", "best_for": "Baking where a little extra sweetness and moisture is fine", "note": "Adds a different, maple-forward flavor rather than a true vanilla stand-in."},
                {"name": "Almond extract", "ratio": "Use half the amount of vanilla called for", "best_for": "Cookies and cakes where a flavor shift is acceptable", "note": "Much stronger than vanilla and tastes distinctly different, not a flavor match, just a way to avoid leaving the recipe flavorless."},
            ],
            "baking_vs_cooking_note": (
                "Vanilla bean paste is the closest substitute across the "
                "board and can replace extract in any recipe without changing "
                "the character of the dish. The other options each shift the "
                "flavor slightly, which matters more in delicate recipes "
                "(vanilla ice cream, pound cake) than in ones with lots of "
                "other competing flavors (spiced cookies, chocolate desserts)."
            ),
            "faqs": [
                {
                    "question": "Can I just leave vanilla extract out of a recipe entirely?",
                    "answer": (
                        "Usually yes without ruining the recipe, vanilla is "
                        "mostly a flavor enhancer rather than a structural "
                        "ingredient, so the baked good will still set and bake "
                        "properly, just taste slightly flatter."
                    ),
                },
                {
                    "question": "Is imitation vanilla extract a fine substitute for real vanilla extract?",
                    "answer": (
                        "For most baked goods, yes, imitation vanilla (made "
                        "from synthetic vanillin) is much cheaper and tastes "
                        "close enough in most recipes, though real extract has "
                        "more complexity and holds up better in delicate, "
                        "vanilla-forward recipes."
                    ),
                },
            ],
            "hub_page_slug": None,
            "recipe_slugs": [],
        },
    },
    {
        "slug": "fish-sauce-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Fish Sauce",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Out of fish sauce, or need a vegetarian alternative? Here are "
                "four ranked substitutes with exact ratios."
            ),
            "hero_image_query": "fish sauce bottle",
            "ranked_substitutes": [
                {"name": "Soy sauce + a squeeze of lime", "ratio": "1:1, plus a small squeeze of lime juice", "best_for": "Vegetarian/vegan cooking", "note": "Lacks fish sauce's deep umami funk, but adds comparable saltiness and a similar savory backbone."},
                {"name": "Worcestershire sauce", "ratio": "1:1", "best_for": "Western dishes wanting umami depth", "note": "Contains anchovies, so not vegetarian, but its flavor profile is genuinely close to fish sauce's savory funk."},
                {"name": "Oyster sauce, thinned with water", "ratio": "Use half the amount, thinned with a little water", "best_for": "Stir-fries", "note": "Sweeter and thicker than fish sauce; works well in cooked dishes but not in dipping sauces."},
                {"name": "Miso paste, thinned with water", "ratio": "1 tsp miso whisked into 1 tbsp water, per tablespoon of fish sauce", "best_for": "Vegetarian/vegan cooking", "note": "A different but genuinely deep umami flavor; works especially well in soups and braises."},
            ],
            "baking_vs_cooking_note": (
                "There's no true substitute for fish sauce's specific "
                "fermented flavor, but soy sauce with lime is the closest "
                "everyday pantry swap for most Southeast Asian dishes, while "
                "Worcestershire is the better match if a slightly funkier, "
                "more complex flavor is wanted and a fish-based product is "
                "acceptable."
            ),
            "faqs": [
                {
                    "question": "Is there a good vegan substitute for fish sauce?",
                    "answer": (
                        "Yes, soy sauce with a squeeze of lime, or thinned "
                        "miso paste, are both common vegan substitutes. Some "
                        "brands also sell a plant-based \"vegan fish sauce\" made "
                        "from fermented mushrooms or seaweed."
                    ),
                },
                {
                    "question": "Can I make my own fish sauce substitute at home?",
                    "answer": (
                        "A quick approximation: simmer soy sauce with a piece "
                        "of dried seaweed or a splash of clam juice for a few "
                        "minutes, then strain, it won't fully replicate fish "
                        "sauce's fermented depth, but adds real savory "
                        "complexity beyond plain soy sauce alone."
                    ),
                },
            ],
            "hub_page_slug": None,
            "recipe_slugs": ["chicken-al-pastor"],
        },
    },
    {
        "slug": "butter-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Butter",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Out of butter, dairy-free, or just want a healthier swap? "
                "Here are four ranked substitutes with exact ratios."
            ),
            "hero_image_query": "butter and alternatives",
            "ranked_substitutes": [
                {"name": "Neutral vegetable oil", "ratio": "Use ¾ the amount of butter called for", "best_for": "Quick breads, muffins, brownies", "note": "Adds moisture but no structure, best in recipes that don't rely on butter for a flaky or creamed texture."},
                {"name": "Unsweetened applesauce", "ratio": "Use half the amount, plus a little extra flour if the batter seems too wet", "best_for": "Lower-fat baking", "note": "Cuts fat and calories significantly but changes texture, denser, moister, less rich."},
                {"name": "Coconut oil, solid", "ratio": "1:1", "best_for": "Dairy-free baking, pie crusts", "note": "Behaves similarly to butter when solid and cold, including in flaky doughs; adds a mild coconut flavor."},
                {"name": "Vegan butter or margarine", "ratio": "1:1", "best_for": "Dairy-free baking that needs butter's exact texture", "note": "The closest 1:1 substitute across the board, since it's specifically formulated to mimic butter's behavior."},
            ],
            "baking_vs_cooking_note": (
                "For pie crusts and laminated doughs (croissants, puff "
                "pastry), stick with a solid fat that stays firm when cold, "
                "coconut oil or vegan butter, not liquid oil. For quick breads "
                "and most cookies and cakes, oil or applesauce substitutes "
                "work fine since those recipes don't depend on butter staying "
                "solid for their structure."
            ),
            "faqs": [
                {
                    "question": "Can I substitute oil for butter in cookies?",
                    "answer": (
                        "You can, but expect a flatter, denser, chewier cookie "
                        "rather than the light, slightly cakey texture creamed "
                        "butter and sugar produces, oil doesn't trap air the "
                        "way solid butter does when creamed."
                    ),
                },
                {
                    "question": "Which butter substitute is best for a dairy allergy?",
                    "answer": (
                        "A dedicated vegan butter or margarine formulated to "
                        "replace real butter is the most reliable choice, since "
                        "it's engineered to match butter's fat content and "
                        "melting behavior far more closely than oil or "
                        "applesauce."
                    ),
                },
            ],
            "hub_page_slug": None,
            "recipe_slugs": [],
        },
    },
    {
        "slug": "creme-fraiche-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Crème Fraîche",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Out of crème fraîche? Here are three ranked substitutes, plus "
                "how to make your own at home overnight."
            ),
            "hero_image_query": "creme fraiche substitute ingredients",
            "ranked_substitutes": [
                {"name": "Sour cream", "ratio": "1:1", "best_for": "Cold toppings and dips", "note": "Tangier and lower in fat; can curdle if boiled the way crème fraîche won't."},
                {"name": "Mascarpone thinned with a little cream", "ratio": "1:1", "best_for": "Desserts and rich sauces", "note": "Milder and richer, closer to crème fraîche's fat content than sour cream."},
                {"name": "Homemade version: heavy cream + buttermilk", "ratio": "1 cup cream + 1 tbsp buttermilk, rested 12-24 hours at room temperature", "best_for": "Any use, if you have a day's notice", "note": "The truest substitute, since it's essentially the same product made at home."},
            ],
            "baking_vs_cooking_note": (
                "For hot sauces and soups where crème fraîche's heat-stability "
                "matters, the homemade version or mascarpone hold up better "
                "than sour cream, which is more prone to curdling under direct "
                "heat."
            ),
            "faqs": [
                {
                    "question": "How long does it take to make crème fraîche at home?",
                    "answer": (
                        "About 12-24 hours at room temperature for the cream "
                        "and buttermilk mixture to thicken and develop its "
                        "characteristic tang, then it should be refrigerated."
                    ),
                },
                {
                    "question": "Can I use crème fraîche and sour cream interchangeably?",
                    "answer": (
                        "For cold applications, yes, with a slight flavor and "
                        "richness difference. For hot sauces, crème fraîche is "
                        "the safer choice since sour cream is more likely to "
                        "curdle or separate."
                    ),
                },
            ],
            "hub_page_slug": "creme-fraiche",
            "recipe_slugs": [],
        },
    },
    {
        "slug": "gruyere-cheese-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Gruyère Cheese",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Out of gruyère? Here are three ranked substitutes that melt "
                "and taste similarly, for fondue, gratins, and French onion "
                "soup."
            ),
            "hero_image_query": "gruyere cheese substitute options",
            "ranked_substitutes": [
                {"name": "Comté", "ratio": "1:1", "best_for": "Any use, fondue, gratins, soups", "note": "The closest possible substitute; a French cousin cheese with nearly identical melting and flavor."},
                {"name": "Swiss Emmental", "ratio": "1:1", "best_for": "Melted dishes and sandwiches", "note": "Milder and sweeter, with the classic large holes; melts just as smoothly."},
                {"name": "Fontina", "ratio": "1:1", "best_for": "Gratins and casseroles", "note": "Buttery and mild rather than nutty, but melts exceptionally well as a stand-in."},
            ],
            "baking_vs_cooking_note": (
                "All three substitutes melt smoothly enough for fondue, "
                "gratins, and French onion soup. Comté is the closest flavor "
                "match; Emmental and Fontina are milder but still perform well "
                "in any recipe relying on a smooth melt."
            ),
            "faqs": [
                {
                    "question": "Can I use cheddar instead of gruyère?",
                    "answer": (
                        "Cheddar melts differently (more likely to turn "
                        "greasy or separate at high heat) and has a sharper, "
                        "less nutty flavor, it works in a pinch, but Comté, "
                        "Emmental, or Fontina are much closer substitutes."
                    ),
                },
                {
                    "question": "What's the best gruyère substitute for French onion soup specifically?",
                    "answer": (
                        "Comté or Emmental, both of which broil into the same "
                        "stretchy, golden-brown crust gruyère is known for on "
                        "top of the soup."
                    ),
                },
            ],
            "hub_page_slug": "gruyere-cheese",
            "recipe_slugs": ["chicken-broccoli-rice-casserole"],
        },
    },
    {
        "slug": "cardamom-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Cardamom",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Out of cardamom? Here are three ranked substitutes, since "
                "there's no perfect match for its unique floral-citrus flavor."
            ),
            "hero_image_query": "cardamom pods and ground cardamom",
            "ranked_substitutes": [
                {"name": "Cinnamon + a pinch of nutmeg", "ratio": "Equal parts cinnamon, plus a small pinch of nutmeg, in place of cardamom", "best_for": "Baking", "note": "A different but pleasant warm-spice profile; won't replicate cardamom's floral citrus note."},
                {"name": "Allspice", "ratio": "Use half the amount of cardamom called for", "best_for": "Baking and spice blends", "note": "Allspice is more intensely flavored, so use less; closer to cardamom's complexity than plain cinnamon."},
                {"name": "Ginger + a pinch of black pepper", "ratio": "Equal parts ginger, plus a small pinch of pepper", "best_for": "Savory dishes and chai-style drinks", "note": "Approximates cardamom's warmth and slight bite in savory or spiced-drink contexts."},
            ],
            "baking_vs_cooking_note": (
                "None of these substitutes truly replicate cardamom's "
                "distinct floral-citrus flavor, they're workable stand-ins "
                "for the general \"warm spice\" role it plays, not a flavor "
                "match. If cardamom is the star flavor of the dish (like "
                "cardamom buns), it's worth seeking out the real thing rather "
                "than substituting."
            ),
            "faqs": [
                {
                    "question": "Is there any spice that really tastes like cardamom?",
                    "answer": (
                        "Not closely, cardamom's floral, citrusy, slightly "
                        "eucalyptus-like flavor is fairly unique among common "
                        "spices, which is why all the usual substitutes are "
                        "approximations rather than close matches."
                    ),
                },
                {
                    "question": "Can I substitute ground cardamom for whole pods, or vice versa?",
                    "answer": (
                        "Roughly ⅛ teaspoon of ground cardamom per whole pod "
                        "called for. Ground cardamom loses potency faster than "
                        "whole pods, so use slightly more if the ground spice "
                        "has been open a while."
                    ),
                },
            ],
            "hub_page_slug": None,
            "recipe_slugs": [],
        },
    },
    {
        "slug": "tahini-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Tahini",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Out of tahini? Here are three ranked substitutes for hummus, "
                "sauces, and baking."
            ),
            "hero_image_query": "tahini substitute ingredients",
            "ranked_substitutes": [
                {"name": "Sunflower seed butter", "ratio": "1:1", "best_for": "Nut-free needs, hummus, sauces", "note": "The closest nut-free substitute, though it lacks tahini's distinct roasted-sesame flavor."},
                {"name": "Almond butter", "ratio": "1:1", "best_for": "Sauces and dressings, not traditional hummus", "note": "Sweeter and richer; changes the flavor character noticeably."},
                {"name": "Peanut butter (unsweetened, natural)", "ratio": "1:1", "best_for": "Sauces where a peanut flavor is welcome", "note": "Works well in noodle sauces and dressings, but tastes distinctly like peanut butter rather than tahini."},
            ],
            "baking_vs_cooking_note": (
                "For hummus specifically, sunflower seed butter is by far the "
                "closest substitute in both texture and neutral-enough flavor. "
                "For dressings, noodle sauces, and baking, any of the three "
                "work fine since the flavor shift is less central to the dish."
            ),
            "faqs": [
                {
                    "question": "Can I make hummus without tahini or any substitute at all?",
                    "answer": (
                        "Yes, a tahini-free hummus made with just chickpeas, "
                        "lemon, garlic, and olive oil is still genuinely good, "
                        "just missing tahini's nutty depth rather than tasting "
                        "unfinished."
                    ),
                },
                {
                    "question": "Is sunflower seed butter as thick as tahini?",
                    "answer": (
                        "Generally yes, similar pourable-paste consistency, "
                        "though brands vary, thin it with a small amount of "
                        "water or oil if it's noticeably thicker than the "
                        "tahini a recipe expects."
                    ),
                },
            ],
            "hub_page_slug": None,
            "recipe_slugs": [],
        },
    },
    {
        "slug": "egg-substitute",
        "template_type": "substitute",
        "title": "Best Substitutes for Eggs in Baking",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Out of eggs, or baking vegan? Here are four ranked egg "
                "substitutes with exact ratios for one egg."
            ),
            "hero_image_query": "egg substitute ingredients flaxseed and applesauce",
            "ranked_substitutes": [
                {"name": "Flax egg (ground flaxseed + water)", "ratio": "1 tbsp ground flaxseed + 3 tbsp water, rested 5 minutes, per egg", "best_for": "Muffins, quick breads, cookies", "note": "Adds binding similar to egg; slightly denser crumb and a mild nutty flavor."},
                {"name": "Unsweetened applesauce", "ratio": "¼ cup per egg", "best_for": "Moist baked goods (muffins, cakes)", "note": "Adds moisture but little binding or lift; best combined with a bit of extra leavening."},
                {"name": "Mashed banana", "ratio": "¼ cup (about half a banana) per egg", "best_for": "Banana bread, muffins, pancakes", "note": "Adds noticeable banana flavor, so best where that's already welcome in the recipe."},
                {"name": "Commercial egg replacer powder", "ratio": "Per package instructions, usually mixed with water", "best_for": "Recipes needing the closest all-around performance", "note": "Formulated specifically to mimic egg's binding and leavening, the most reliable option across recipe types."},
            ],
            "baking_vs_cooking_note": (
                "These substitutes work for baking, where eggs mainly provide "
                "binding, moisture, and some lift. None of them substitute "
                "well for eggs in dishes where the egg itself is the star, "
                "scrambled eggs, omelets, quiches, since there's no "
                "substitute for egg's specific set and texture there."
            ),
            "faqs": [
                {
                    "question": "Which egg substitute works best for cookies?",
                    "answer": (
                        "A flax egg or a commercial egg replacer both work "
                        "well for cookies, providing binding without adding "
                        "too much extra moisture, which can otherwise make "
                        "cookies spread more than intended."
                    ),
                },
                {
                    "question": "Can I substitute more than 2 eggs in one recipe with these?",
                    "answer": (
                        "It gets riskier the more eggs a recipe calls for, "
                        "eggs provide real structure in recipes with 3+ eggs "
                        "(like a sponge cake), and substitutes can't fully "
                        "replicate that at scale. These substitutes work most "
                        "reliably for recipes calling for 1-2 eggs."
                    ),
                },
            ],
            "hub_page_slug": None,
            "recipe_slugs": [],
        },
    },
    {
        "slug": "taco-recipes",
        "template_type": "category_roundup",
        "title": "Taco Recipes",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Taco recipes organized by protein - chicken, beef, fish, and "
                "vegetarian - with a real curated pick instead of an "
                "auto-generated list."
            ),
            "intro": (
                "A good taco comes down to a well-seasoned filling and a "
                "warm, pliable tortilla - everything else is topping "
                "preference. These are the taco fillings worth putting in "
                "regular rotation, organized by protein."
            ),
            "recipe_cards": [
                {"title": "Chicken Al Pastor Tacos", "slug": "chicken-al-pastor", "description": "Achiote-and-pineapple marinated chicken, seared hard and chopped for tacos.", "image_query": "chicken al pastor tacos"},
                {"title": "Carne Asada Tacos", "slug": None, "description": "Grilled, citrus-marinated skirt steak, sliced thin against the grain.", "image_query": "carne asada tacos"},
                {"title": "Baja Fish Tacos", "slug": None, "description": "Crispy beer-battered fish with cabbage slaw and a creamy chipotle sauce.", "image_query": "baja fish tacos"},
                {"title": "Birria Tacos", "slug": None, "description": "Slow-braised, chile-spiced beef tacos, dipped and served with their own consommé.", "image_query": "birria tacos"},
                {"title": "Black Bean and Sweet Potato Tacos", "slug": None, "description": "A hearty vegetarian filling with roasted sweet potato and smoky black beans.", "image_query": "black bean sweet potato tacos"},
                {"title": "Shrimp Tacos", "slug": None, "description": "Quick-seared, chili-lime shrimp with a bright cabbage and cilantro slaw.", "image_query": "shrimp tacos"},
            ],
            "sub_categories": [
                {"label": "Meat", "items": ["Chicken Al Pastor Tacos", "Carne Asada Tacos", "Birria Tacos"]},
                {"label": "Seafood", "items": ["Baja Fish Tacos", "Shrimp Tacos"]},
                {"label": "Vegetarian", "items": ["Black Bean and Sweet Potato Tacos"]},
            ],
            "faqs": [
                {
                    "question": "What's the best way to warm tortillas for tacos?",
                    "answer": (
                        "Directly over a gas flame for a few seconds per side "
                        "for a slight char, or in a dry skillet over medium "
                        "heat, both are better than microwaving, which leaves "
                        "them gummy rather than pliable."
                    ),
                },
                {
                    "question": "Corn or flour tortillas for tacos?",
                    "answer": (
                        "Traditionally corn, especially for Mexican-style "
                        "fillings like al pastor and carne asada, flour "
                        "tortillas are more common for Tex-Mex-style tacos and "
                        "burritos. Either works; it's largely regional "
                        "preference."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "pie-recipes",
        "template_type": "category_roundup",
        "title": "Pie Recipes",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Pie recipes organized by type - fruit, custard, and "
                "cream - with a real curated pick instead of an "
                "auto-generated list."
            ),
            "intro": (
                "Every pie comes down to the same two decisions: what goes in "
                "the crust, and what goes on top of it (or doesn't). These are "
                "the pies worth mastering, organized by type."
            ),
            "recipe_cards": [
                {"title": "Classic Apple Pie", "slug": None, "description": "A double-crust pie with cinnamon-spiced apples, baked until the filling bubbles through the vents.", "image_query": "apple pie"},
                {"title": "Pumpkin Pie", "slug": None, "description": "A silky custard pie spiced with cinnamon, ginger, and clove in a single crust.", "image_query": "pumpkin pie"},
                {"title": "Key Lime Pie", "slug": None, "description": "A tart, creamy custard pie in a graham cracker crust, no baking required for the filling.", "image_query": "key lime pie"},
                {"title": "Chocolate Cream Pie", "slug": None, "description": "A rich chocolate pudding filling topped with whipped cream in a baked crust.", "image_query": "chocolate cream pie"},
                {"title": "Pecan Pie", "slug": None, "description": "A gooey, deeply sweet filling packed with toasted pecans in a single crust.", "image_query": "pecan pie"},
                {"title": "Cherry Pie", "slug": None, "description": "A double-crust pie with a tart-sweet cherry filling, best made with fresh or frozen sour cherries.", "image_query": "cherry pie"},
            ],
            "sub_categories": [
                {"label": "Fruit", "items": ["Classic Apple Pie", "Cherry Pie"]},
                {"label": "Custard", "items": ["Pumpkin Pie", "Key Lime Pie", "Pecan Pie"]},
                {"label": "Cream", "items": ["Chocolate Cream Pie"]},
            ],
            "faqs": [
                {
                    "question": "Why does my pie crust shrink or slide down the sides while baking?",
                    "answer": (
                        "Usually the dough wasn't chilled enough before baking, "
                        "letting the gluten relax and the fat melt too early. "
                        "Chill the shaped crust for at least 30 minutes before "
                        "it goes in the oven, and use pie weights for a "
                        "blind-baked crust."
                    ),
                },
                {
                    "question": "Should I bake a pie on the bottom rack of the oven?",
                    "answer": (
                        "For most fruit and custard pies, yes, the bottom "
                        "rack gets more direct heat, which helps the bottom "
                        "crust cook through and stay crisp rather than turning "
                        "soggy under a wet filling."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "duck-recipes",
        "template_type": "category_roundup",
        "title": "Duck Recipes",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Duck recipes organized by cut and method - breast, confit, "
                "and whole roast - with a real curated pick instead of an "
                "auto-generated list."
            ),
            "intro": (
                "Duck's high fat content makes it forgiving and flavorful, "
                "but it rewards a slightly different technique than chicken - "
                "rendering the fat matters as much as the cooking "
                "temperature. These are the duck preparations worth learning."
            ),
            "recipe_cards": [
                {"title": "Pan-Seared Duck Breast", "slug": None, "description": "Scored, slowly rendered duck breast with crackling-crisp skin and a rosy center.", "image_query": "pan seared duck breast"},
                {"title": "Duck Confit", "slug": None, "description": "Duck legs slow-cooked and preserved in their own rendered fat until fall-apart tender.", "image_query": "duck confit"},
                {"title": "Whole Roast Duck", "slug": None, "description": "A whole roasted duck with crisp skin, basted and pricked to release excess fat as it cooks.", "image_query": "whole roast duck"},
                {"title": "Duck Fat Roasted Potatoes", "slug": None, "description": "Potatoes roasted in reserved duck fat for an especially crisp, savory crust.", "image_query": "duck fat potatoes"},
            ],
            "sub_categories": [
                {"label": "Breast", "items": ["Pan-Seared Duck Breast"]},
                {"label": "Whole Bird", "items": ["Whole Roast Duck"]},
                {"label": "Confit & Fat", "items": ["Duck Confit", "Duck Fat Roasted Potatoes"]},
            ],
            "faqs": [
                {
                    "question": "Why do you score duck breast skin before cooking?",
                    "answer": (
                        "Scoring the fat layer (without cutting into the meat) "
                        "helps it render out more quickly and evenly, which is "
                        "what produces genuinely crisp, non-rubbery skin."
                    ),
                },
                {
                    "question": "Should I start duck breast skin-side up or down?",
                    "answer": (
                        "Skin-side down, in a cold or barely warm pan, then "
                        "bring the heat up gradually, this slowly renders the "
                        "fat instead of scorching the skin before the fat has "
                        "had time to melt out."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "beet-recipes",
        "template_type": "category_roundup",
        "title": "Beet Recipes",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Beet recipes organized by preparation - roasted, pickled, and "
                "raw - with a real curated pick instead of an auto-generated "
                "list."
            ),
            "intro": (
                "Beets taste completely different depending on how they're "
                "prepared, earthy and sweet roasted, sharp and tangy "
                "pickled, crisp and peppery raw. These are the beet dishes "
                "worth trying, organized by preparation."
            ),
            "recipe_cards": [
                {"title": "Roasted Beet Salad with Goat Cheese", "slug": None, "description": "Sweet roasted beets with tangy goat cheese and toasted walnuts.", "image_query": "roasted beet salad goat cheese"},
                {"title": "Pickled Beets", "slug": None, "description": "Classic sweet-and-sour pickled beets, ready to can or refrigerate.", "image_query": "pickled beets"},
                {"title": "Shaved Raw Beet Salad", "slug": None, "description": "Thinly shaved raw beets with a bright citrus vinaigrette.", "image_query": "raw beet salad"},
                {"title": "Beet and Feta Hummus", "slug": None, "description": "A vibrant pink hummus made by blending roasted beets into the base.", "image_query": "beet hummus"},
            ],
            "sub_categories": [
                {"label": "Roasted", "items": ["Roasted Beet Salad with Goat Cheese"]},
                {"label": "Pickled", "items": ["Pickled Beets"]},
                {"label": "Raw", "items": ["Shaved Raw Beet Salad", "Beet and Feta Hummus"]},
            ],
            "faqs": [
                {
                    "question": "How do I keep beets from staining my hands and cutting board?",
                    "answer": (
                        "Wear disposable gloves while peeling and cutting, and "
                        "use a cutting board you don't mind staining (or line it "
                        "with parchment). The stain is just pigment and washes "
                        "off skin with soap and time, but can linger on porous "
                        "surfaces."
                    ),
                },
                {
                    "question": "Do I need to peel beets before roasting?",
                    "answer": (
                        "No, roast them whole with the skin on, wrapped in "
                        "foil, then the skin slips off easily by hand once "
                        "they're cooked and cooled slightly. Peeling raw beets "
                        "first is messier and unnecessary."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "fig-recipes",
        "template_type": "category_roundup",
        "title": "Fig Recipes",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Fig recipes for fresh and dried figs, savory and sweet, "
                "with a real curated pick instead of an auto-generated list."
            ),
            "intro": (
                "Fresh figs have a short season, so they're best used simply, "
                "with cheese, honey, or a quick roast. Dried figs work "
                "year-round in baking and preserves. These are the fig "
                "recipes worth making with either."
            ),
            "recipe_cards": [
                {"title": "Fig and Prosciutto Flatbread", "slug": None, "description": "Fresh figs, salty prosciutto, and melted gorgonzola over a crisp flatbread.", "image_query": "fig prosciutto flatbread"},
                {"title": "Honey-Roasted Figs", "slug": None, "description": "Fresh figs halved and roasted with honey until caramelized, served with yogurt or ice cream.", "image_query": "honey roasted figs"},
                {"title": "Fig Jam", "slug": None, "description": "A simple preserve made from fresh or dried figs, sugar, and lemon.", "image_query": "fig jam"},
                {"title": "Fig and Goat Cheese Salad", "slug": None, "description": "Fresh figs, creamy goat cheese, and arugula with a balsamic drizzle.", "image_query": "fig goat cheese salad"},
            ],
            "sub_categories": [
                {"label": "Savory", "items": ["Fig and Prosciutto Flatbread", "Fig and Goat Cheese Salad"]},
                {"label": "Sweet", "items": ["Honey-Roasted Figs", "Fig Jam"]},
            ],
            "faqs": [
                {
                    "question": "How do I tell when a fresh fig is ripe?",
                    "answer": (
                        "A ripe fig gives slightly to gentle pressure and often "
                        "shows a small split or bead of syrup near the stem "
                        "end. Firm, unyielding figs won't ripen much further "
                        "once picked."
                    ),
                },
                {
                    "question": "Can I substitute dried figs for fresh in these recipes?",
                    "answer": (
                        "For jam and baking, yes, rehydrate dried figs in "
                        "warm water for 15-20 minutes first. For recipes that "
                        "showcase fresh fig's texture (salads, roasted whole), "
                        "dried figs are a poor substitute."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "radish-recipes",
        "template_type": "category_roundup",
        "title": "Radish Recipes",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Radish recipes beyond the raw salad topping - roasted, "
                "pickled, and sautéed - with a real curated pick instead of "
                "an auto-generated list."
            ),
            "intro": (
                "Radishes lose most of their sharp bite when cooked, turning "
                "mild and almost sweet, a very different vegetable from the "
                "raw, peppery version most people know. These recipes cover "
                "both sides."
            ),
            "recipe_cards": [
                {"title": "Roasted Radishes with Butter", "slug": None, "description": "Halved radishes roasted until tender and lightly caramelized, tossed with butter and herbs.", "image_query": "roasted radishes"},
                {"title": "Quick-Pickled Radishes", "slug": None, "description": "Thinly sliced radishes pickled in a vinegar brine, ready in an hour.", "image_query": "pickled radishes"},
                {"title": "Radishes with Butter and Salt", "slug": None, "description": "The classic French bistro snack - crisp raw radishes, good butter, and flaky salt.", "image_query": "radishes with butter and salt"},
                {"title": "Sautéed Radish Greens", "slug": None, "description": "The often-discarded radish tops, quickly sautéed like any other leafy green.", "image_query": "sauteed radish greens"},
            ],
            "sub_categories": [
                {"label": "Cooked", "items": ["Roasted Radishes with Butter", "Sautéed Radish Greens"]},
                {"label": "Raw & Pickled", "items": ["Quick-Pickled Radishes", "Radishes with Butter and Salt"]},
            ],
            "faqs": [
                {
                    "question": "Can I eat radish greens?",
                    "answer": (
                        "Yes, they're edible and taste similar to other "
                        "peppery greens like arugula or mustard greens. Wash "
                        "them well, since they can hold grit, and use them "
                        "quickly since they wilt faster than the radish root."
                    ),
                },
                {
                    "question": "Do roasted radishes still taste peppery like raw ones?",
                    "answer": (
                        "No, roasting mellows radishes considerably, turning "
                        "their sharp bite mild and slightly sweet, closer to a "
                        "roasted turnip than a raw radish."
                    ),
                },
            ],
            "related_collection_slugs": ["turnip-recipes"],
        },
    },
    {
        "slug": "turnip-recipes",
        "template_type": "category_roundup",
        "title": "Turnip Recipes",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Turnip recipes for roasting, mashing, and gratins, with a "
                "real curated pick instead of an auto-generated list."
            ),
            "intro": (
                "Turnips are often overlooked next to potatoes, but they roast "
                "and mash just as well with a sharper, slightly peppery edge. "
                "These recipes make the case for keeping them in rotation."
            ),
            "recipe_cards": [
                {"title": "Roasted Turnips", "slug": None, "description": "Cubed turnips roasted until caramelized at the edges and tender inside.", "image_query": "roasted turnips"},
                {"title": "Mashed Turnips", "slug": None, "description": "A lighter, slightly peppery alternative to mashed potatoes.", "image_query": "mashed turnips"},
                {"title": "Turnip and Potato Gratin", "slug": None, "description": "Thinly sliced turnips layered with potatoes in a creamy baked gratin.", "image_query": "turnip potato gratin"},
                {"title": "Turnip Soup", "slug": None, "description": "A simple, creamy pureed soup built on turnips and a light broth base.", "image_query": "turnip soup"},
            ],
            "sub_categories": [
                {"label": "Roasted & Mashed", "items": ["Roasted Turnips", "Mashed Turnips"]},
                {"label": "Baked & Soup", "items": ["Turnip and Potato Gratin", "Turnip Soup"]},
            ],
            "faqs": [
                {
                    "question": "Do I need to peel turnips before cooking?",
                    "answer": (
                        "For young, small turnips, the skin is thin enough to "
                        "leave on. Larger, older turnips have a tougher skin "
                        "that's worth peeling for a better texture."
                    ),
                },
                {
                    "question": "What's the difference between a turnip and a rutabaga?",
                    "answer": (
                        "Turnips are smaller with white-and-purple skin and a "
                        "sharper flavor; rutabagas are larger, denser, sweeter, "
                        "and have yellowish flesh. They're related but distinct "
                        "root vegetables, not the same thing under two names."
                    ),
                },
            ],
            "related_collection_slugs": ["radish-recipes"],
        },
    },
    {
        "slug": "venison-recipes",
        "template_type": "category_roundup",
        "title": "Venison Recipes",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Venison recipes for steaks, roasts, and ground meat, with "
                "notes on why lean game meat needs different handling than "
                "beef."
            ),
            "intro": (
                "Venison is much leaner than beef, which means it dries out "
                "and turns tough far more easily if treated like a fatty ribeye. "
                "These recipes are built around that difference rather than "
                "ignoring it."
            ),
            "recipe_cards": [
                {"title": "Pan-Seared Venison Backstrap", "slug": None, "description": "Quick-seared venison loin, cooked no further than medium-rare to stay tender.", "image_query": "seared venison backstrap"},
                {"title": "Venison Chili", "slug": None, "description": "Ground venison chili, simmered long enough to stay tender despite its low fat content.", "image_query": "venison chili"},
                {"title": "Braised Venison Shoulder", "slug": None, "description": "A tougher cut slow-braised in red wine and stock until fall-apart tender.", "image_query": "braised venison"},
                {"title": "Venison Burgers", "slug": None, "description": "Ground venison mixed with a little added fat (bacon or butter) to keep the patties juicy.", "image_query": "venison burger"},
            ],
            "sub_categories": [
                {"label": "Quick-Cooked", "items": ["Pan-Seared Venison Backstrap", "Venison Burgers"]},
                {"label": "Low & Slow", "items": ["Venison Chili", "Braised Venison Shoulder"]},
            ],
            "faqs": [
                {
                    "question": "Why does venison taste gamey, and can that be reduced?",
                    "answer": (
                        "Some of the flavor comes from the animal's diet and "
                        "age, but a lot of \"gamey\" taste actually comes from "
                        "poor field dressing or overcooking. Trimming silverskin "
                        "and connective tissue thoroughly, and not overcooking "
                        "lean cuts, both meaningfully reduce it."
                    ),
                },
                {
                    "question": "Why does venison need to be cooked differently than beef?",
                    "answer": (
                        "It has much less intramuscular fat than beef, so lean "
                        "cuts (backstrap, tenderloin) dry out and toughen "
                        "quickly past medium-rare, while tougher cuts (shoulder, "
                        "shank) still need low, slow, moist cooking to break "
                        "down connective tissue, the same logic as beef, just "
                        "less margin for error on the lean cuts."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "persimmon-recipes",
        "template_type": "category_roundup",
        "title": "Persimmon Recipes",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Persimmon recipes for both fuyu and hachiya varieties, "
                "sliced raw or baked, with a real curated pick instead of an "
                "auto-generated list."
            ),
            "intro": (
                "Which persimmon recipe works depends entirely on the "
                "variety: firm fuyu persimmons are eaten raw like an apple, "
                "while soft, ripe hachiya persimmons are almost always baked "
                "or blended, never eaten firm. These recipes cover both."
            ),
            "recipe_cards": [
                {"title": "Sliced Fuyu Persimmon Salad", "slug": None, "description": "Crisp, raw fuyu persimmon slices with arugula, pomegranate, and a light vinaigrette.", "image_query": "fuyu persimmon salad"},
                {"title": "Persimmon Bread", "slug": None, "description": "A moist quick bread made from soft, fully ripe hachiya persimmon pulp.", "image_query": "persimmon bread"},
                {"title": "Roasted Fuyu Persimmons", "slug": None, "description": "Fuyu persimmon wedges roasted until caramelized at the edges.", "image_query": "roasted persimmons"},
                {"title": "Persimmon Pudding", "slug": None, "description": "A traditional steamed or baked pudding made from hachiya persimmon pulp and warm spices.", "image_query": "persimmon pudding"},
            ],
            "sub_categories": [
                {"label": "Raw (Fuyu)", "items": ["Sliced Fuyu Persimmon Salad", "Roasted Fuyu Persimmons"]},
                {"label": "Baked (Hachiya)", "items": ["Persimmon Bread", "Persimmon Pudding"]},
            ],
            "faqs": [
                {
                    "question": "What's the difference between fuyu and hachiya persimmons?",
                    "answer": (
                        "Fuyu persimmons are squat and firm, eaten crisp like "
                        "an apple even when ripe. Hachiya persimmons are "
                        "acorn-shaped and intensely astringent until they "
                        "become fully soft and jelly-like, at which point "
                        "they're used in baking, never eaten firm."
                    ),
                },
                {
                    "question": "What happens if I eat an underripe hachiya persimmon?",
                    "answer": (
                        "It will taste unpleasantly astringent and chalky, "
                        "coating your mouth in a dry, puckering sensation, a "
                        "hachiya must be fully soft, almost to the point of "
                        "looking overripe, before it's palatable."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "buttermilk-recipes",
        "template_type": "category_roundup",
        "title": "Buttermilk Recipes",
        "batch_number": 2,
        "content": {
            "meta_description": (
                "Recipes for using up a carton of buttermilk - baking, "
                "marinades, and dressings - with a real curated pick instead "
                "of an auto-generated list."
            ),
            "intro": (
                "Buttermilk's tang and acidity do real work in a recipe, "
                "tenderizing meat, activating baking soda, thinning a "
                "dressing, not just adding flavor. These are the best ways "
                "to use up a carton before it goes to waste."
            ),
            "recipe_cards": [
                {"title": "Buttermilk Biscuits", "slug": None, "description": "Flaky, tender biscuits leavened partly by buttermilk's acidity reacting with baking soda.", "image_query": "buttermilk biscuits"},
                {"title": "Buttermilk Fried Chicken", "slug": None, "description": "Chicken marinated in buttermilk overnight for extra tenderness before frying.", "image_query": "buttermilk fried chicken"},
                {"title": "Buttermilk Pancakes", "slug": None, "description": "Fluffier, tangier pancakes than the standard milk-based version.", "image_query": "buttermilk pancakes"},
                {"title": "Buttermilk Ranch Dressing", "slug": None, "description": "A classic tangy, herby ranch dressing built on a buttermilk base.", "image_query": "buttermilk ranch dressing"},
            ],
            "sub_categories": [
                {"label": "Baking", "items": ["Buttermilk Biscuits", "Buttermilk Pancakes"]},
                {"label": "Savory", "items": ["Buttermilk Fried Chicken", "Buttermilk Ranch Dressing"]},
            ],
            "faqs": [
                {
                    "question": "Can I substitute regular milk for buttermilk in these recipes?",
                    "answer": (
                        "Not without a substitute, regular milk lacks the "
                        "acidity that reacts with baking soda in biscuits and "
                        "pancakes, and lacks the tenderizing effect for fried "
                        "chicken. See the buttermilk substitute guide if you're "
                        "out."
                    ),
                },
                {
                    "question": "How long does buttermilk keep in the fridge?",
                    "answer": (
                        "Typically 1-2 weeks past the printed date if kept cold "
                        "and sealed, it's already cultured and acidic, which "
                        "gives it a longer shelf life than regular milk."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    # Cuisine collections. Where the site already has a genuinely matching
    # recipe (per that recipe's own content, not a stretch), it's included
    # with its real slug; every other card is an aspirational slug: None
    # placeholder, same pattern the other category_roundup pages already
    # use (e.g. duck-recipes, radish-recipes). Not every cuisine collection
    # links back to itself from a recipe's own category_link -- that field
    # only holds one value, and several of these recipes already point
    # elsewhere (chicken-al-pastor -> taco-recipes), which stays as-is.
    {
        "slug": "italian-recipes",
        "template_type": "category_roundup",
        "title": "Italian Recipes",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Italian recipes from weeknight pasta to slow braises - with "
                "a real curated pick instead of an auto-generated list."
            ),
            "intro": (
                "Italian cooking leans on a small set of excellent "
                "ingredients treated simply rather than a long list of "
                "components, good olive oil, real parmesan, tomatoes at "
                "their peak. These are the dishes worth learning properly, "
                "from quick weeknight pasta to the kind of braise that "
                "takes all afternoon."
            ),
            "recipe_cards": [
                {
                    "title": "Parmesan Crusted Chicken",
                    "slug": "parmesan-crusted-chicken",
                    "description": "A mayonnaise-and-parmesan crust that bakes deeply golden without deep-frying.",
                    "image_query": "parmesan crusted chicken",
                },
                {"title": "Classic Margherita Pizza", "slug": None, "description": "San Marzano tomatoes, fresh mozzarella, and basil on a properly stretched dough.", "image_query": "margherita pizza"},
                {"title": "Creamy Mushroom Risotto", "slug": None, "description": "Arborio rice slowly coaxed into a creamy texture with ladle after ladle of warm stock.", "image_query": "mushroom risotto"},
                {"title": "Homemade Fettuccine Alfredo", "slug": None, "description": "Butter, parmesan, and pasta water emulsified into a real sauce, no cream needed.", "image_query": "fettuccine alfredo"},
                {"title": "Eggplant Parmesan", "slug": None, "description": "Breaded, fried eggplant layered with marinara and melted cheese, baked until bubbling.", "image_query": "eggplant parmesan"},
                {"title": "Tiramisu", "slug": None, "description": "Espresso-soaked ladyfingers layered with a mascarpone cream, no baking required.", "image_query": "tiramisu"},
            ],
            "sub_categories": [
                {"label": "Pasta & Risotto", "items": ["Creamy Mushroom Risotto", "Homemade Fettuccine Alfredo"]},
                {"label": "Mains", "items": ["Parmesan Crusted Chicken", "Classic Margherita Pizza", "Eggplant Parmesan"]},
                {"label": "Dessert", "items": ["Tiramisu"]},
            ],
            "faqs": [
                {
                    "question": "What's the one ingredient worth splurging on for Italian cooking?",
                    "answer": (
                        "A good extra-virgin olive oil, it's used raw far more "
                        "often in Italian cooking than in most cuisines, "
                        "finishing dishes and dressing salads, where a "
                        "cheap, flavorless oil is much more noticeable than "
                        "it would be buried in a long-cooked sauce."
                    ),
                },
                {
                    "question": "Is Italian-American food (like this parmesan crusted chicken) the same as Italian food?",
                    "answer": (
                        "Not exactly, dishes like chicken parmesan and this "
                        "parmesan-crusted version are Italian-inspired "
                        "adaptations that developed in the US, using Italian "
                        "ingredients and technique but not found in the same "
                        "form in Italy itself."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "mexican-recipes",
        "template_type": "category_roundup",
        "title": "Mexican Recipes",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Mexican recipes from tacos to rice pudding - with a real "
                "curated pick instead of an auto-generated list."
            ),
            "intro": (
                "Mexican cooking varies enormously by region, but dried "
                "chiles, lime, and fresh herbs show up again and again as "
                "the backbone of real flavor, not the bottled taco seasoning "
                "shortcut. These are real, traditional-leaning picks, not "
                "Tex-Mex approximations."
            ),
            "recipe_cards": [
                {
                    "title": "Chicken Al Pastor",
                    "slug": "chicken-al-pastor",
                    "description": "Achiote-and-pineapple marinated chicken, seared hard for a charred, sweet-spicy crust.",
                    "image_query": "chicken al pastor tacos",
                },
                {
                    "title": "Arroz con Leche",
                    "slug": "arroz-con-leche",
                    "description": "Traditional cinnamon rice pudding, simmered low and slow until creamy.",
                    "image_query": "arroz con leche rice pudding",
                },
                {"title": "Chiles Rellenos", "slug": None, "description": "Roasted poblano chiles stuffed with cheese, battered, and fried until golden.", "image_query": "chiles rellenos"},
                {"title": "Pozole Rojo", "slug": None, "description": "A deep red, chile-based hominy soup, traditionally slow-simmered with pork.", "image_query": "pozole rojo"},
                {"title": "Elote (Mexican Street Corn)", "slug": None, "description": "Grilled corn slathered with crema, cotija, chile powder, and lime.", "image_query": "elote mexican street corn"},
                {"title": "Tres Leches Cake", "slug": None, "description": "A light sponge cake soaked in three kinds of milk until soft and custardy.", "image_query": "tres leches cake"},
            ],
            "sub_categories": [
                {"label": "Mains", "items": ["Chicken Al Pastor", "Chiles Rellenos", "Pozole Rojo"]},
                {"label": "Sides", "items": ["Elote (Mexican Street Corn)"]},
                {"label": "Dessert", "items": ["Arroz con Leche", "Tres Leches Cake"]},
            ],
            "faqs": [
                {
                    "question": "What's the difference between real Mexican food and Tex-Mex?",
                    "answer": (
                        "Tex-Mex developed in the US and leans heavily on "
                        "shredded cheese, flour tortillas, and cumin-forward "
                        "seasoning blends. Traditional Mexican cooking varies "
                        "by region but relies more on fresh and dried chiles, "
                        "corn, and herbs like epazote and cilantro for its "
                        "flavor base."
                    ),
                },
                {
                    "question": "Do I need a lot of specialty ingredients to cook Mexican food at home?",
                    "answer": (
                        "A handful go a long way, dried chiles (guajillo, "
                        "ancho, pasilla), achiote paste, and good corn "
                        "tortillas cover most of what these recipes need, "
                        "and all are increasingly common in regular "
                        "supermarkets, not just Latin grocery stores."
                    ),
                },
            ],
            "related_collection_slugs": ["taco-recipes"],
        },
    },
    {
        "slug": "polish-recipes",
        "template_type": "category_roundup",
        "title": "Polish Recipes",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Polish recipes - hearty, comforting classics from pierogi "
                "to kielbasa - with a real curated pick instead of an "
                "auto-generated list."
            ),
            "intro": (
                "Polish cooking is built for cold weather, hearty, "
                "slow-cooked, and rarely fussy about presentation. These are "
                "the dishes that show up at a real Polish table again and "
                "again, not a tourist-menu sampler."
            ),
            "recipe_cards": [
                {"title": "Potato and Cheese Pierogi", "slug": None, "description": "Hand-folded dumplings filled with mashed potato and farmer's cheese, pan-fried in butter.", "image_query": "potato pierogi"},
                {"title": "Bigos (Hunter's Stew)", "slug": None, "description": "A slow-simmered stew of sauerkraut, fresh cabbage, and mixed meats, better the next day.", "image_query": "bigos hunters stew"},
                {"title": "Kielbasa and Sauerkraut", "slug": None, "description": "Smoked kielbasa simmered with tangy sauerkraut, onion, and a touch of caraway.", "image_query": "kielbasa and sauerkraut"},
                {"title": "Zurek (Sour Rye Soup)", "slug": None, "description": "A tangy, fermented rye-based soup, traditionally served with a hard-boiled egg and sausage.", "image_query": "zurek sour rye soup"},
                {"title": "Placki Ziemniaczane (Potato Pancakes)", "slug": None, "description": "Crisp, pan-fried shredded potato pancakes, served with sour cream or applesauce.", "image_query": "polish potato pancakes"},
                {"title": "Paczki (Polish Doughnuts)", "slug": None, "description": "Rich, yeasted doughnuts filled with fruit preserves and dusted with powdered sugar.", "image_query": "paczki polish doughnuts"},
            ],
            "sub_categories": [
                {"label": "Mains", "items": ["Bigos (Hunter's Stew)", "Kielbasa and Sauerkraut"]},
                {"label": "Soup & Sides", "items": ["Zurek (Sour Rye Soup)", "Potato and Cheese Pierogi", "Placki Ziemniaczane (Potato Pancakes)"]},
                {"label": "Dessert", "items": ["Paczki (Polish Doughnuts)"]},
            ],
            "faqs": [
                {
                    "question": "What's the difference between Polish kielbasa and other sausages?",
                    "answer": (
                        "\"Kielbasa\" is actually just the Polish word for "
                        "sausage in general, but in the US it usually refers "
                        "specifically to wiejska-style smoked pork sausage, "
                        "seasoned with garlic and marjoram, denser and more "
                        "coarsely ground than a hot dog."
                    ),
                },
                {
                    "question": "Are pierogi always potato-filled?",
                    "answer": (
                        "No, potato and cheese is the most common filling "
                        "outside Poland, but traditional fillings also "
                        "include sauerkraut and mushroom, ground meat, and "
                        "sweet versions filled with fruit like blueberries "
                        "or farmer's cheese and sugar."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "indian-recipes",
        "template_type": "category_roundup",
        "title": "Indian Recipes",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Indian recipes built on real spice technique, not a jar of "
                "pre-mixed curry powder - with a real curated pick instead "
                "of an auto-generated list."
            ),
            "intro": (
                "Indian cooking is regionally enormous, what's typical in "
                "Punjab looks nothing like what's typical in Kerala, but "
                "whole and ground spices bloomed in hot oil are the common "
                "thread across nearly all of it. These are dishes worth "
                "learning the real technique for, not a shortcut version."
            ),
            "recipe_cards": [
                {"title": "Butter Chicken (Murgh Makhani)", "slug": None, "description": "Tandoori-charred chicken simmered in a rich, tomato-and-cream sauce.", "image_query": "butter chicken murgh makhani"},
                {"title": "Chana Masala", "slug": None, "description": "Chickpeas simmered in a tangy, spiced tomato gravy, a staple vegetarian main.", "image_query": "chana masala"},
                {"title": "Chicken Biryani", "slug": None, "description": "Layered, fragrant basmati rice and marinated chicken, cooked together under a sealed lid.", "image_query": "chicken biryani"},
                {"title": "Saag Paneer", "slug": None, "description": "Firm paneer cheese simmered in a pureed, spiced spinach sauce.", "image_query": "saag paneer"},
                {"title": "Homemade Naan", "slug": None, "description": "Pillowy, blistered flatbread, traditionally cooked against the wall of a tandoor.", "image_query": "homemade naan bread"},
                {"title": "Gulab Jamun", "slug": None, "description": "Fried milk-solid dumplings soaked in a cardamom-and-rosewater syrup.", "image_query": "gulab jamun"},
            ],
            "sub_categories": [
                {"label": "Mains", "items": ["Butter Chicken (Murgh Makhani)", "Chana Masala", "Chicken Biryani", "Saag Paneer"]},
                {"label": "Bread", "items": ["Homemade Naan"]},
                {"label": "Dessert", "items": ["Gulab Jamun"]},
            ],
            "faqs": [
                {
                    "question": "What's the difference between curry powder and how Indian food is actually spiced?",
                    "answer": (
                        "Pre-mixed \"curry powder\" is largely a British "
                        "colonial invention, not how most Indian cooking "
                        "actually works. Traditional cooking usually builds "
                        "a spice blend fresh for each dish, often blooming "
                        "whole spices in hot oil first, rather than reaching "
                        "for one all-purpose jar."
                    ),
                },
                {
                    "question": "Do I need a tandoor to make tandoori or naan recipes at home?",
                    "answer": (
                        "No, a very hot home oven (with a pizza stone or "
                        "cast iron pan preheated inside) or a hot skillet "
                        "gets a reasonable approximation for naan. It won't "
                        "have the exact smoky char of a real clay tandoor, "
                        "but it's a workable substitute."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "chinese-recipes",
        "template_type": "category_roundup",
        "title": "Chinese Recipes",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Chinese recipes built on real wok technique - with a real "
                "curated pick instead of an auto-generated list."
            ),
            "intro": (
                "Chinese cooking spans wildly different regional styles, "
                "from Sichuan's numbing chile heat to Cantonese's lighter, "
                "steamed and stir-fried dishes, but a properly hot wok and "
                "prepped ingredients (everything cut and ready before the "
                "heat goes on) matter across nearly all of it."
            ),
            "recipe_cards": [
                {"title": "Kung Pao Chicken", "slug": None, "description": "Stir-fried chicken, peanuts, and dried chiles in a tangy, savory-sweet sauce.", "image_query": "kung pao chicken"},
                {"title": "Pork and Chive Dumplings", "slug": None, "description": "Hand-folded dumplings, pan-fried until crisp on the bottom and steamed through.", "image_query": "pork chive dumplings"},
                {"title": "Mapo Tofu", "slug": None, "description": "Silken tofu simmered in a numbing, chile-and-fermented-bean sauce with ground pork.", "image_query": "mapo tofu"},
                {"title": "Char Siu (Chinese BBQ Pork)", "slug": None, "description": "Pork shoulder marinated in a sweet, five-spice glaze and roasted until sticky.", "image_query": "char siu bbq pork"},
                {"title": "Egg Fried Rice", "slug": None, "description": "Day-old rice, cold and dry enough to fry separately rather than clump into mush.", "image_query": "egg fried rice"},
                {"title": "Scallion Pancakes", "slug": None, "description": "Flaky, layered flatbread laminated with scallion and oil, pan-fried until crisp.", "image_query": "scallion pancakes"},
            ],
            "sub_categories": [
                {"label": "Mains", "items": ["Kung Pao Chicken", "Mapo Tofu", "Char Siu (Chinese BBQ Pork)"]},
                {"label": "Dumplings & Bread", "items": ["Pork and Chive Dumplings", "Scallion Pancakes"]},
                {"label": "Rice", "items": ["Egg Fried Rice"]},
            ],
            "faqs": [
                {
                    "question": "Do I really need a wok, or does a regular skillet work?",
                    "answer": (
                        "A wok's shape helps food move and cook more evenly "
                        "over very high heat, but a large, heavy skillet "
                        "works reasonably well at home, where most stovetops "
                        "can't get a wok as hot as a restaurant burner "
                        "anyway."
                    ),
                },
                {
                    "question": "Why does restaurant fried rice taste different from homemade?",
                    "answer": (
                        "Mostly heat and rice moisture, restaurant burners "
                        "run much hotter than home stoves, and day-old, "
                        "refrigerated rice fries drier and separates better "
                        "than fresh rice, which tends to clump and steam "
                        "instead of frying."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "japanese-recipes",
        "template_type": "category_roundup",
        "title": "Japanese Recipes",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Japanese recipes from traditional classics to modern "
                "fusion favorites - with a real curated pick instead of an "
                "auto-generated list."
            ),
            "intro": (
                "Japanese cooking prizes letting a few good ingredients "
                "speak clearly, whether that's a precisely seasoned bowl of "
                "rice or a quick, modern crowd-pleaser built on the same "
                "flavors. These cover both the traditional and the "
                "newer, casserole-scale takes on sushi flavors."
            ),
            "recipe_cards": [
                {
                    "title": "Sushi Bake",
                    "slug": "sushi-bake",
                    "description": "Seasoned sushi rice under a baked, creamy seafood topping, all the flavor, none of the rolling.",
                    "image_query": "sushi bake casserole",
                },
                {"title": "Chicken Katsu", "slug": None, "description": "Panko-breaded, fried chicken cutlet, sliced and served with a tangy tonkatsu sauce.", "image_query": "chicken katsu"},
                {"title": "Miso Soup", "slug": None, "description": "A simple, savory soup built on dashi and fermented miso paste.", "image_query": "miso soup"},
                {"title": "Teriyaki Salmon", "slug": None, "description": "Pan-glazed salmon in a sweet-savory soy, mirin, and sugar reduction.", "image_query": "teriyaki salmon"},
                {"title": "Yaki Onigiri (Grilled Rice Balls)", "slug": None, "description": "Pan-seared rice balls brushed with soy sauce until the outside turns crisp and toasty.", "image_query": "yaki onigiri grilled rice balls"},
                {"title": "Matcha Cheesecake", "slug": None, "description": "A Japanese-style light, jiggly cheesecake with earthy matcha folded through it.", "image_query": "matcha cheesecake"},
            ],
            "sub_categories": [
                {"label": "Mains", "items": ["Sushi Bake", "Chicken Katsu", "Teriyaki Salmon"]},
                {"label": "Soup & Rice", "items": ["Miso Soup", "Yaki Onigiri (Grilled Rice Balls)"]},
                {"label": "Dessert", "items": ["Matcha Cheesecake"]},
            ],
            "faqs": [
                {
                    "question": "Is sushi bake a traditional Japanese dish?",
                    "answer": (
                        "No, it's a modern Filipino-American fusion dish, "
                        "built on Japanese sushi flavors (seasoned rice, "
                        "nori, a creamy seafood topping) but served "
                        "casserole-style rather than rolled, it's not "
                        "something you'd find as a traditional dish in Japan "
                        "itself."
                    ),
                },
                {
                    "question": "What's the difference between short-grain and long-grain rice for these recipes?",
                    "answer": (
                        "Short-grain (sushi) rice is stickier and clumps "
                        "together once seasoned, which is what makes it "
                        "work for sushi, onigiri, and similar dishes. "
                        "Long-grain rice stays too separate and won't hold "
                        "together the same way."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "french-recipes",
        "template_type": "category_roundup",
        "title": "French Recipes",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "French recipes from weeknight classics to real technique-driven "
                "cooking - with a real curated pick instead of an "
                "auto-generated list."
            ),
            "intro": (
                "French cooking's reputation for being fussy mostly comes "
                "from restaurant tasting menus, most of the actual home "
                "repertoire is rustic and forgiving, built on a handful of "
                "real techniques (a good stock, a proper sear, patience with "
                "onions) rather than a long list of specialty ingredients."
            ),
            "recipe_cards": [
                {"title": "Coq au Vin", "slug": None, "description": "Chicken braised slowly in red wine with mushrooms, pearl onions, and bacon.", "image_query": "coq au vin"},
                {"title": "French Onion Soup", "slug": None, "description": "Deeply caramelized onions in a rich beef broth, topped with broiled cheese and bread.", "image_query": "french onion soup"},
                {"title": "Ratatouille", "slug": None, "description": "A slow-cooked medley of summer vegetables, each cooked separately before combining.", "image_query": "ratatouille"},
                {"title": "Quiche Lorraine", "slug": None, "description": "A custard tart filled with bacon and gruyère in a buttery, blind-baked crust.", "image_query": "quiche lorraine"},
                {"title": "Beef Bourguignon", "slug": None, "description": "Beef chuck braised for hours in red wine until fall-apart tender.", "image_query": "beef bourguignon"},
                {"title": "Crème Brûlée", "slug": None, "description": "A silky vanilla custard with a torched, crackling sugar shell on top.", "image_query": "creme brulee"},
            ],
            "sub_categories": [
                {"label": "Mains", "items": ["Coq au Vin", "Beef Bourguignon", "Quiche Lorraine"]},
                {"label": "Soup & Sides", "items": ["French Onion Soup", "Ratatouille"]},
                {"label": "Dessert", "items": ["Crème Brûlée"]},
            ],
            "faqs": [
                {
                    "question": "Do I need special French wine for recipes like coq au vin or beef bourguignon?",
                    "answer": (
                        "No, an inexpensive, drinkable red you'd actually "
                        "want to sip works fine, the classic guidance is to "
                        "cook with a wine you wouldn't mind drinking, not a "
                        "specific expensive bottle."
                    ),
                },
                {
                    "question": "Why do French recipes so often call for cooking onions low and slow?",
                    "answer": (
                        "Real caramelization (as opposed to just browning) "
                        "takes time, 30-45 minutes of low, patient heat "
                        "breaks onions down into a deeply sweet, jammy "
                        "texture that rushing over higher heat can't "
                        "replicate, it just browns and burns the surface "
                        "instead."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "thai-recipes",
        "template_type": "category_roundup",
        "title": "Thai Recipes",
        "batch_number": 3,
        "content": {
            "meta_description": (
                "Thai recipes built on real balance between sweet, sour, "
                "salty, and spicy - with a real curated pick instead of an "
                "auto-generated list."
            ),
            "intro": (
                "Thai cooking is built around balancing four flavors at "
                "once, sweet, sour, salty, and spicy, rather than any one "
                "of them dominating. These lean on real, fresh aromatics "
                "(lemongrass, galangal, fresh chiles) rather than a "
                "shortcut jarred paste."
            ),
            "recipe_cards": [
                {"title": "Pad Thai", "slug": None, "description": "Stir-fried rice noodles in a tamarind-based sauce with shrimp, egg, and peanuts.", "image_query": "pad thai"},
                {"title": "Green Curry Chicken", "slug": None, "description": "Chicken simmered in a fragrant, coconut-milk-based curry with Thai basil.", "image_query": "green curry chicken"},
                {"title": "Tom Yum Soup", "slug": None, "description": "A hot and sour shrimp soup built on lemongrass, galangal, and lime leaf.", "image_query": "tom yum soup"},
                {"title": "Som Tum (Green Papaya Salad)", "slug": None, "description": "Shredded unripe papaya pounded with chile, lime, and fish sauce in a mortar and pestle.", "image_query": "som tum green papaya salad"},
                {"title": "Mango Sticky Rice", "slug": None, "description": "Sweetened coconut sticky rice served alongside ripe mango slices.", "image_query": "mango sticky rice"},
                {"title": "Thai Basil Chicken (Pad Kra Pao)", "slug": None, "description": "Quickly stir-fried ground chicken with garlic, chile, and Thai holy basil.", "image_query": "thai basil chicken pad kra pao"},
            ],
            "sub_categories": [
                {"label": "Mains", "items": ["Pad Thai", "Green Curry Chicken", "Thai Basil Chicken (Pad Kra Pao)"]},
                {"label": "Soup & Salad", "items": ["Tom Yum Soup", "Som Tum (Green Papaya Salad)"]},
                {"label": "Dessert", "items": ["Mango Sticky Rice"]},
            ],
            "faqs": [
                {
                    "question": "Can I make Thai curry pastes from scratch, or is store-bought fine?",
                    "answer": (
                        "Store-bought paste is a genuinely fine shortcut, "
                        "even many Thai home cooks use it, homemade paste is "
                        "more work (pounding fresh aromatics in a mortar and "
                        "pestle) but does taste noticeably fresher and more "
                        "vibrant if you have the time."
                    ),
                },
                {
                    "question": "What's the difference between Thai basil and regular basil?",
                    "answer": (
                        "Thai basil has a more anise-like, slightly spicy "
                        "flavor and holds up better to high heat than sweet "
                        "Italian basil, which wilts and loses flavor faster "
                        "in a hot stir-fry. They're not a clean 1:1 swap for "
                        "each other."
                    ),
                },
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "conversion-calculator",
        "template_type": "tool_page",
        "title": "Kitchen Measurement Conversion Calculator",
        "batch_number": 0,
        "content": {
            "tool": "conversion_calculator",
            "meta_description": (
                "Free kitchen measurement conversion calculator, convert cups, "
                "tablespoons, grams, ounces, and oven temperatures between US and "
                "metric."
            ),
        },
    },
    {
        "slug": "time-temperature-guide",
        "template_type": "tool_page",
        "title": "Cooking Time & Temperature Guide",
        "batch_number": 0,
        "content": {
            "tool": "time_temperature_guide",
            "meta_description": (
                "Cooking time and temperature guide by protein and method (oven, "
                "air fryer, grill), plus USDA safe minimum internal temperatures."
            ),
        },
    },
    {
        "slug": "recipe-generator",
        "template_type": "tool_page",
        "title": "Custom Recipe Generator",
        "batch_number": 0,
        "content": {
            "tool": "recipe_generator",
            "meta_description": (
                "Tell us what's in your kitchen and get a recipe idea back, a "
                "custom recipe generator built around the ingredients you already "
                "have."
            ),
        },
    },
]


def _find_double_dashes(pages: list[dict]) -> list[tuple[str, str]]:
    """Walks every string value in `pages`' content and returns
    (location, offending value) pairs for anything containing a "--"
    construction. Used to guard against that pattern silently creeping
    back into new content batches, see _check_no_double_dashes below for
    why this needs to be more than a one-time cleanup."""
    hits: list[tuple[str, str]] = []

    def walk(value, location: str) -> None:
        if isinstance(value, str):
            if "--" in value:
                hits.append((location, value))
        elif isinstance(value, dict):
            for key, sub_value in value.items():
                walk(sub_value, f"{location}.{key}")
        elif isinstance(value, list):
            for i, sub_value in enumerate(value):
                walk(sub_value, f"{location}[{i}]")

    for page in pages:
        walk(page["content"], page["slug"])
    return hits


def _check_no_double_dashes() -> None:
    """The "word, dash, dash, word" construction reads as an obvious
    AI-writing tell, per direct user feedback, and every occurrence of it
    was deliberately stripped from this file's content once already.
    Because resync_content() (see below) now pushes every edit here
    straight into production on the next deploy, a new content batch that
    reintroduces this pattern would reach the live site just as reliably
    as a real fix would, so this raises immediately at import time rather
    than relying on whoever adds the next batch to remember and catch it
    themselves. Fix an offender with a comma, or a single hyphen when it's
    introducing a list right after the word describing it, never another
    double dash.
    """
    hits = _find_double_dashes(SEED_PAGES)
    if not hits:
        return
    shown = "\n".join(f"  {location}: {text!r}" for location, text in hits[:15])
    more = f"\n  ...and {len(hits) - 15} more" if len(hits) > 15 else ""
    raise ValueError(
        f"Found {len(hits)} double dash construction(s) in SEED_PAGES "
        f"content, fix each with a comma or a single hyphen:\n{shown}{more}"
    )


_check_no_double_dashes()


def seed(db: Session) -> int:
    """Insert the seed pages if they don't already exist. Returns the number inserted."""
    inserted = 0
    for page in SEED_PAGES:
        exists = db.query(Page).filter(Page.slug == page["slug"]).first()
        if exists:
            continue
        db.add(
            Page(
                slug=page["slug"],
                template_type=page["template_type"],
                title=page["title"],
                status="draft",
                batch_number=page["batch_number"],
                content=page["content"],
            )
        )
        inserted += 1
    db.commit()
    return inserted



# Fields that live inside a page's content but are populated by
# fetch_stock_images.py at runtime, not defined in SEED_PAGES at all -- a
# resync must never touch these, or every already-fetched real photo would
# get silently wiped out the next time an unrelated content edit ships.
_RUNTIME_IMAGE_KEYS = ("image_url", "image_attribution")


def _merge_recipe_cards(existing_cards: list[dict], seed_cards: list[dict]) -> list[dict]:
    """recipe_cards is a list, not a flat set of keys, so it needs its own
    merge: take each card's fields from SEED_PAGES (title, description,
    image_query, ...) but keep whatever image fields that specific card
    (matched by title) already has, since those came from fetch_images(),
    not from SEED_PAGES."""
    existing_by_title = {c.get("title"): c for c in existing_cards}
    merged = []
    for seed_card in seed_cards:
        existing_card = existing_by_title.get(seed_card.get("title"), {})
        merged_card = dict(seed_card)
        for key in _RUNTIME_IMAGE_KEYS:
            if key in existing_card:
                merged_card[key] = existing_card[key]
        merged.append(merged_card)
    return merged


def resync_content(db: Session) -> int:
    """seed() never overwrites a page that already exists, which protects
    real runtime state (a fetched stock photo, most of all) but also means
    any later edit to a page's copy in SEED_PAGES, fixing a typo, sharpening
    an awkward sentence, correcting a stock-photo query, never reaches a
    page once it's already been seeded once. Only genuinely new pages
    (a new slug) pick up SEED_PAGES edits without this.

    Re-syncs every field of a page's content from SEED_PAGES except the
    runtime image fields (see _RUNTIME_IMAGE_KEYS) and recipe_cards' own
    per-card image fields (see _merge_recipe_cards), which don't exist in
    SEED_PAGES at all and would otherwise be wiped out by a naive
    overwrite. Safe to run on every startup: idempotent, a no-op once a
    page's non-image content already matches SEED_PAGES.
    """
    seed_by_slug = {p["slug"]: p["content"] for p in SEED_PAGES}
    updated = 0
    for page in db.query(Page).filter(Page.slug.in_(seed_by_slug.keys())).all():
        seed_content = seed_by_slug[page.slug]
        # A deep copy, not a reference -- see fetch_stock_images.py's
        # fetch_images() for why mutating page.content directly would
        # silently fail to persist.
        content = copy.deepcopy(page.content)
        changed = False
        for key, seed_value in seed_content.items():
            if key in _RUNTIME_IMAGE_KEYS:
                continue
            if key == "recipe_cards":
                merged = _merge_recipe_cards(content.get(key, []), seed_value)
                if merged != content.get(key):
                    content[key] = merged
                    changed = True
            elif content.get(key) != seed_value:
                content[key] = seed_value
                changed = True
        if changed:
            page.content = content
            updated += 1
    if updated:
        db.commit()
    return updated


if __name__ == "__main__":
    session = SessionLocal()
    try:
        count = seed(session)
        print(f"Seeded {count} page(s).")
    finally:
        session.close()
