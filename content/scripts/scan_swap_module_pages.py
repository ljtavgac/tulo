"""One-off analysis: which published recipe_or_dish pages have the
ingredient-swap / live-calorie-counter module active, and which of those
only became active because of the substitute nutrition_per_unit backfill
(content/scripts/backfill_substitute_nutrition.py).

Reimplements (read-only, against the SEED_PAGES source of truth rather
than a live DB) the exact same resolution logic main.py uses at request
time -- _ingredient_hub_slugs_by_title / _resolve_hub_slug /
_swappable_substitutes_for -- plus RecipeIngredientsPanel.tsx's own
frontend gating (a substitute needs BOTH ratio_multiplier and
nutrition_per_unit to appear as a swap option; the live nutrition-diff
block additionally needs the recipe's own ingredient to carry
nutrition_per_unit too). Two distinct results are reported since they're
gated slightly differently:

  - "swap dropdown" pages: at least one ingredient has a swappable
    substitute (ratio_multiplier + nutrition_per_unit) -- the "I don't
    have this" picker shows up.
  - "live calorie module" pages: the stricter set (RecipeIngredientsPanel
    line ~87) -- the ingredient itself also needs nutrition_per_unit, so
    swapping it recomputes a live macro total, not just a name/qty swap.

Usage:
    python3 content/scripts/scan_swap_module_pages.py [--before <git-ref>]

    --before <git-ref>   Also compute the same scan against
                          seed_templates.py as it existed at that ref, and
                          report which pages are newly active now vs. then.
                          Typically the commit right before the backfill
                          started (e845d8f in this run).
"""

from __future__ import annotations

import argparse
import importlib
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))


def _load_seed_pages_from_text(module_text: str, module_name: str):
    """Returns SEED_PAGES from the given seed_templates.py source text.
    Can't just exec() it as a standalone script -- it has a real relative
    import (`from .content_audit import ...`), which only works when the
    module is loaded as part of its actual package. Writes it into the
    (already-on-sys.path) app package under a throwaway name and imports
    it properly instead."""
    tmp_path = REPO_ROOT / "backend" / "app" / f"_{module_name}.py"
    tmp_path.write_text(module_text)
    try:
        mod = importlib.import_module(f"app._{module_name}")
        return mod.SEED_PAGES
    finally:
        tmp_path.unlink()


def _hub_titles(seed_pages: list[dict]) -> dict[str, str]:
    return {
        p["title"].strip().lower(): p["slug"]
        for p in seed_pages
        if p["template_type"] == "ingredient_hub" and not p["content"].get("unpublished")
    }


# Mirrors main.py's own _HUB_MATCH_LEADING_SAFE_WORDS /
# _HUB_MATCH_TRAILING_CLAUSE_SAFE_WORDS / _resolve_hub_slug exactly -- see
# that module for the full rationale (curated, food-noun-free descriptor
# lists only, never a substring/fuzzy match, "ground" deliberately
# excluded). Keep these two copies in sync by hand if either changes.
_HUB_MATCH_LEADING_SAFE_WORDS = {
    "fresh", "unsalted", "dried", "large", "small", "fine", "finely",
    "granulated", "kosher", "powdered", "toasted", "unsweetened", "frozen",
    "plain", "whole", "chopped", "minced", "diced", "sliced", "shredded",
    "grated", "cubed", "crumbled", "raw", "cooked",
}
_HUB_MATCH_TRAILING_CLAUSE_SAFE_WORDS = {
    "for", "chopped", "and", "sliced", "minced", "diced", "into", "cut",
    "finely", "softened", "thinly", "inch", "peeled", "freshly",
    "garnish", "melted", "or", "divided", "serving", "the", "on", "shredded",
    "halved", "drained", "skinless", "frying", "smashed", "plus", "optional",
    "rinsed", "cubed", "beaten", "quartered", "skin", "pieces", "thick",
    "packed", "room", "temperature", "at", "to", "taste", "strips", "wedges",
    "bite", "sized", "size", "crushed", "trimmed", "boneless",
    "cubes", "julienned", "zested", "seeded", "stemmed",
}


def _exact_hub_match(key: str, hub_titles: dict[str, str]) -> str | None:
    if key in hub_titles:
        return hub_titles[key]
    if key.endswith("s") and key[:-1] in hub_titles:
        return hub_titles[key[:-1]]
    return None


def _resolve_hub_slug(name: str, explicit: str | None, hub_titles: dict[str, str]) -> str | None:
    if explicit:
        return explicit
    key = name.strip().lower()

    match = _exact_hub_match(key, hub_titles)
    if match:
        return match

    stripped_paren = re.sub(r"\s*\([^)]*\)", "", key).strip()
    if stripped_paren != key:
        match = _exact_hub_match(stripped_paren, hub_titles)
        if match:
            return match
        key = stripped_paren

    if "," in key:
        prefix, clause = key.split(",", 1)
        prefix = prefix.strip()
        clause_words = re.findall(r"[a-z]+", clause)
        if clause_words and all(w in _HUB_MATCH_TRAILING_CLAUSE_SAFE_WORDS for w in clause_words):
            match = _exact_hub_match(prefix, hub_titles)
            if match:
                return match
            key = prefix

    words = key.split()
    while len(words) > 1 and words[0] in _HUB_MATCH_LEADING_SAFE_WORDS:
        words = words[1:]
        match = _exact_hub_match(" ".join(words), hub_titles)
        if match:
            return match

    return None


def _swappable_substitutes_for(hub: dict | None) -> list[dict]:
    if hub is None:
        return []
    return [s for s in hub["content"].get("substitutes", []) if s.get("ratio_multiplier") is not None]


def scan(seed_pages: list[dict]) -> dict[str, dict]:
    """Returns {recipe_slug: {"swap_dropdown": [ingredient names...],
    "live_calorie_module": [ingredient names...]}} for every published
    recipe_or_dish page with at least one qualifying ingredient."""
    hub_titles = _hub_titles(seed_pages)
    hubs_by_slug = {
        p["slug"]: p for p in seed_pages if p["template_type"] == "ingredient_hub" and not p["content"].get("unpublished")
    }

    results: dict[str, dict] = {}
    for page in seed_pages:
        if page["template_type"] != "recipe_or_dish" or page["content"].get("unpublished"):
            continue
        swap_dropdown_ings = []
        live_module_ings = []
        for ing in page["content"].get("ingredients", []):
            hub_slug = _resolve_hub_slug(ing.get("name", ""), ing.get("hub_slug"), hub_titles)
            if not hub_slug:
                continue
            hub = hubs_by_slug.get(hub_slug)
            substitutes = _swappable_substitutes_for(hub)
            if not substitutes:
                continue
            # Frontend swap-dropdown gate (RecipeIngredientsPanel.tsx ~247):
            # a substitute needs its OWN nutrition_per_unit to be offered.
            nutrition_subs = [s for s in substitutes if s.get("nutrition_per_unit")]
            if not nutrition_subs:
                continue
            swap_dropdown_ings.append(ing["name"])
            # Live calorie-module gate (~line 87): the recipe's own
            # ingredient also needs nutrition_per_unit.
            if ing.get("nutrition_per_unit"):
                live_module_ings.append(ing["name"])
        if swap_dropdown_ings:
            results[page["slug"]] = {
                "title": page["title"],
                "swap_dropdown": swap_dropdown_ings,
                "live_calorie_module": live_module_ings,
            }
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--before", default=None, help="git ref to diff against (e.g. a commit before the backfill).")
    args = parser.parse_args()

    current_text = (REPO_ROOT / "backend" / "app" / "seed_templates.py").read_text()
    current_pages = _load_seed_pages_from_text(current_text, "seed_templates_current")
    current_results = scan(current_pages)

    print(f"{len(current_results)} published recipe_or_dish page(s) currently have the swap dropdown active on at least one ingredient.")
    live_count = sum(1 for r in current_results.values() if r["live_calorie_module"])
    print(f"{live_count} of those also have the live calorie-counter module active (ingredient itself has nutrition_per_unit too).")

    before_results = {}
    if args.before:
        before_text = subprocess.run(
            ["git", "show", f"{args.before}:backend/app/seed_templates.py"],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
        ).stdout
        before_pages = _load_seed_pages_from_text(before_text, "seed_templates_before")
        before_results = scan(before_pages)
        newly_active = sorted(set(current_results) - set(before_results))
        print(f"\n{len(newly_active)} page(s) newly gained the swap dropdown since {args.before}:")
        for slug in newly_active:
            r = current_results[slug]
            live_tag = " [live calorie module too]" if r["live_calorie_module"] else ""
            print(f"  /food/recipes/{slug} -- {r['title']}{live_tag} ({', '.join(r['swap_dropdown'])})")

    print("\nFull current list:")
    for slug, r in sorted(current_results.items()):
        live_tag = " [live calorie module]" if r["live_calorie_module"] else ""
        print(f"  /food/recipes/{slug} -- {r['title']}{live_tag}: {', '.join(r['swap_dropdown'])}")


if __name__ == "__main__":
    main()
