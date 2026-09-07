"""
Seeds one hand-authored example page per template type, for the template
review step described in WORKFLOW.md ("build order: templates before
content"). Titles/keywords below are copied from real CONTENT_QUEUE.csv
rows as plain literals -- this module never reads or writes that CSV file.

Run standalone with `python -m app.seed_templates`, or it runs
automatically on API startup if the pages table is empty (see main.py).
"""

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
                "came here for -- visible the moment the page loads."
            ),
        },
    },
    {
        "slug": "banana-nut-bread",
        "template_type": "recipe_or_dish",
        "title": "Banana Nut Bread Recipe",
        "batch_number": 1,
        "content": {
            "hero_image_query": "banana nut bread",
            "why_it_works": (
                "Extra-ripe, well-spotted bananas add natural sweetness and "
                "moisture, so this loaf stays tender without drying out -- and "
                "a quick one-bowl method means less cleanup."
            ),
            "prep_time_minutes": 15,
            "cook_time_minutes": 60,
            "total_time_minutes": 75,
            "servings": 10,
            # Quantities are numeric (base_qty / base_qty_metric) rather than
            # free-text strings so the frontend's serving-size scaler can
            # actually recalculate them, not just relabel a fixed string.
            "ingredients": [
                {"name": "ripe bananas, mashed", "base_qty": 3, "unit_us": "medium banana(s)", "base_qty_metric": 340, "unit_metric": "g", "hub_slug": None},
                {"name": "unsalted butter, melted", "base_qty": 1 / 3, "unit_us": "cup", "base_qty_metric": 75, "unit_metric": "g", "hub_slug": None},
                {"name": "granulated sugar", "base_qty": 0.75, "unit_us": "cup", "base_qty_metric": 150, "unit_metric": "g", "hub_slug": None},
                {"name": "large egg, beaten", "base_qty": 1, "unit_us": "egg(s)", "base_qty_metric": 1, "unit_metric": "egg(s)", "hub_slug": None},
                {"name": "vanilla extract", "base_qty": 1, "unit_us": "tsp", "base_qty_metric": 5, "unit_metric": "ml", "hub_slug": None},
                {"name": "baking soda", "base_qty": 1, "unit_us": "tsp", "base_qty_metric": 5, "unit_metric": "g", "hub_slug": None},
                {"name": "salt", "base_qty": 0.25, "unit_us": "tsp", "base_qty_metric": 1.5, "unit_metric": "g", "hub_slug": None},
                {"name": "all-purpose flour", "base_qty": 1.5, "unit_us": "cups", "base_qty_metric": 190, "unit_metric": "g", "hub_slug": None},
                {"name": "walnuts, chopped", "base_qty": 1, "unit_us": "cup", "base_qty_metric": 120, "unit_metric": "g", "hub_slug": None},
            ],
            "instructions": [
                "Preheat the oven to 350°F (175°C). Grease a 9x5-inch loaf pan.",
                "In a large bowl, mash the ripe bananas with a fork until smooth.",
                "Stir the melted butter into the mashed banana.",
                "Mix in the sugar, beaten egg, and vanilla extract.",
                "Sprinkle the baking soda and salt over the mixture and stir in.",
                "Add the flour and mix until just combined -- don't overmix, or the bread will turn out dense.",
                "Fold in the chopped walnuts.",
                "Pour the batter into the prepared loaf pan.",
                "Bake for 55-65 minutes, until a toothpick inserted into the center comes out clean.",
                "Cool in the pan for 10 minutes, then turn out onto a wire rack to cool completely before slicing.",
            ],
            "technique_link": None,
            "related_recipe_slugs": [],
            "category_link": {"title": "Eggplant Recipes", "slug": "eggplant-recipes"},
        },
    },
    {
        "slug": "chives",
        "template_type": "ingredient_hub",
        "title": "Chives",
        "batch_number": 1,
        "content": {
            "hero_image_query": "fresh chives",
            "description": (
                "Chives (Allium schoenoprasum) are the mildest member of the onion "
                "family, grown for their thin, hollow, grass-like green stems. They "
                "deliver a delicate onion flavor without the sharpness of scallions "
                "or raw onion, which is why they're used as a finishing herb rather "
                "than a base cooking ingredient."
            ),
            "substitutes": [
                {"name": "Scallion greens (green onion tops)", "ratio": "1:1", "note": "Slightly stronger onion flavor, but the closest visual and flavor match."},
                {"name": "Green onion, whole", "ratio": "1:1", "note": "Similar flavor profile to scallion greens, a bit more oniony overall."},
                {"name": "Parsley + a pinch of onion powder", "ratio": "1:1 (as parsley)", "note": "Use for the color/garnish effect without onion flavor; add onion powder separately to taste."},
                {"name": "Leek greens, finely minced", "ratio": "1:1", "note": "Milder and slightly sweeter; mince very finely since leek greens are more fibrous."},
            ],
            "substitute_page_slug": None,
            "storage": (
                "Fresh chives wilt quickly. Wrap loosely in a damp paper towel and "
                "store in a sealed container or bag in the refrigerator crisper "
                "drawer -- they'll keep for about a week. For longer storage, snip "
                "and freeze in an airtight bag or ice cube tray with a little water "
                "or oil; frozen chives lose their crisp texture but keep their "
                "flavor well for cooked dishes."
            ),
            "uses": (
                "Snip with scissors directly onto finished dishes -- baked potatoes, "
                "scrambled eggs, soups, dips, and salads. Chives lose flavor and turn "
                "dull if cooked for long, so add them at the very end or as a garnish "
                "rather than early in cooking."
            ),
            "nutrition_note": (
                "Chives are low in calories and used in small quantities, but they "
                "contain vitamin K, vitamin C, and modest amounts of vitamin A -- "
                "more of a flavor accent than a significant nutrient source at "
                "typical serving sizes."
            ),
            "recipe_slugs": [],
            "related_ingredient_slugs": [],
        },
    },
    {
        "slug": "how-to-cook-spaghetti-squash",
        "template_type": "howto_technique",
        "title": "How to Cook Spaghetti Squash",
        "batch_number": 1,
        "content": {
            "hero_image_query": "roasted spaghetti squash",
            "steps": [
                "Preheat the oven to 400°F (200°C).",
                "Slice the spaghetti squash in half lengthwise, from stem to base. If the whole squash is hard to cut, microwave it whole for 3-4 minutes first to soften the skin.",
                "Scoop out the seeds and stringy pulp from the center with a spoon, just like a pumpkin.",
                "Drizzle the cut sides with olive oil and season with salt and pepper.",
                "Place both halves cut-side down on a parchment-lined baking sheet.",
                "Roast for 40-50 minutes, until the skin gives slightly when pressed and a fork slides in easily.",
                "Let the squash cool for about 10 minutes -- it holds heat and can burn fingers if handled right away.",
                "Using a fork, scrape the flesh lengthwise from the skin. It separates into long, spaghetti-like strands.",
            ],
            "common_mistakes": [
                "Roasting cut-side up: cut-side down traps steam and keeps the flesh moist; cut-side up dries the strands out on the surface while leaving the center undercooked.",
                "Undercooking: if a fork doesn't glide through easily, the strands come out short and won't separate cleanly. Give it the full roasting time rather than checking too early.",
                "Not draining excess moisture: spaghetti squash holds a lot of water. If the dish will sit or be sauced, salt the strands lightly and let them sit in a colander for a few minutes to release extra liquid.",
            ],
            "equipment": ["Sharp chef's knife", "Baking sheet", "Parchment paper (optional)", "Fork"],
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
            "hero_image_query": "tahini paste jar",
            "direct_answer": (
                "Tahini is a smooth paste made from toasted, ground sesame seeds -- "
                "similar in consistency to thin peanut butter, with a nutty, "
                "slightly bitter flavor and no added sweetness."
            ),
            "expanded_explanation": (
                "It's a foundational ingredient in Middle Eastern and Mediterranean "
                "cooking, made by grinding hulled sesame seeds, sometimes lightly "
                "toasted first, into a smooth, pourable paste, often with a touch of "
                "oil to help it emulsify. Quality varies by roast level and grind -- "
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
            "related_recipe_slugs": [],
        },
    },
    {
        "slug": "cappuccino-vs-latte",
        "template_type": "comparison",
        "title": "Cappuccino vs. Latte: What's the Difference?",
        "batch_number": 1,
        "content": {
            "item_a_name": "Cappuccino",
            "item_b_name": "Latte",
            "comparison_table": [
                {"attribute": "Espresso", "item_a": "1-2 shots", "item_b": "1-2 shots"},
                {"attribute": "Steamed milk", "item_a": "Roughly equal part to the espresso", "item_b": "Much larger proportion -- 2-3x the espresso"},
                {"attribute": "Milk foam", "item_a": "Thick, deep foam layer (about a third of the drink)", "item_b": "Thin foam layer, just enough to cap the drink"},
                {"attribute": "Typical size", "item_a": "5-6 oz", "item_b": "8-12+ oz"},
                {"attribute": "Texture", "item_a": "Light, airy, more foam than liquid milk", "item_b": "Silky, milk-forward, less foam"},
            ],
            "verdict": (
                "Choose a cappuccino for a stronger, more concentrated coffee-forward "
                "drink with a distinct foam texture. Choose a latte for a milkier, "
                "smoother, more mellow drink -- and more room for flavored syrups, "
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
                        "and a thin layer of foam -- the higher milk ratio is also what "
                        "makes lattes the go-to canvas for latte art."
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
                        "dissipates -- not ideal for thick or dense baked goods, "
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
                        "flour with it -- not as a direct add-in alongside the "
                        "regular flour."
                    ),
                },
            ],
            "baking_vs_cooking_note": (
                "The substitutes above are for baking soda's leavening role in baked "
                "goods. If a savory recipe calls for a pinch of baking soda for "
                "browning or tenderizing (stir-fries, caramelizing onions), there "
                "isn't a good direct substitute -- it's best to simply omit it there."
            ),
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
            "intro": (
                "Eggplant's spongy texture takes on flavor differently depending on "
                "how it's cooked -- roasted until creamy, breaded and fried, or "
                "simmered low and slow. These are the eggplant recipes worth having "
                "in rotation, organized by cooking method."
            ),
            "recipe_cards": [
                {"title": "Baba Ganoush", "slug": None, "description": "Smoky, roasted eggplant dip blended with tahini, garlic, and lemon.", "image_query": "baba ganoush"},
                {"title": "Eggplant Parmesan", "slug": None, "description": "Breaded, fried (or baked) eggplant layered with marinara and melted cheese.", "image_query": "eggplant parmesan"},
                {"title": "Roasted Eggplant with Garlic and Herbs", "slug": None, "description": "The simplest way to cook eggplant -- olive oil, high heat, and just enough seasoning to let it shine.", "image_query": "roasted eggplant"},
                {"title": "Eggplant Curry (Baingan Bharta)", "slug": None, "description": "Charred, mashed eggplant simmered with tomatoes, onion, and warm spices.", "image_query": "baingan bharta"},
                {"title": "Grilled Eggplant Slices", "slug": None, "description": "Salted, grilled eggplant rounds with a quick balsamic glaze.", "image_query": "grilled eggplant"},
                {"title": "Miso-Glazed Eggplant (Nasu Dengaku)", "slug": None, "description": "Broiled eggplant halves topped with a sweet-savory miso glaze.", "image_query": "nasu dengaku"},
            ],
            "sub_categories": [
                {"label": "Mediterranean", "items": ["Baba Ganoush", "Grilled Eggplant Slices"]},
                {"label": "Comfort Food", "items": ["Eggplant Parmesan"]},
                {"label": "Global", "items": ["Eggplant Curry (Baingan Bharta)", "Miso-Glazed Eggplant (Nasu Dengaku)"]},
            ],
            "related_collection_slugs": [],
        },
    },
    {
        "slug": "conversion-calculator",
        "template_type": "tool_page",
        "title": "Kitchen Measurement Conversion Calculator",
        "batch_number": 0,
        "content": {"tool": "conversion_calculator"},
    },
    {
        "slug": "time-temperature-guide",
        "template_type": "tool_page",
        "title": "Cooking Time & Temperature Guide",
        "batch_number": 0,
        "content": {"tool": "time_temperature_guide"},
    },
    {
        "slug": "recipe-generator",
        "template_type": "tool_page",
        "title": "Custom Recipe Generator",
        "batch_number": 0,
        "content": {"tool": "recipe_generator"},
    },
]


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


if __name__ == "__main__":
    session = SessionLocal()
    try:
        count = seed(session)
        print(f"Seeded {count} page(s).")
    finally:
        session.close()
