"""Generates real recipe_or_dish pages for a category_roundup page's
unlinked placeholder cards (recipe_cards entries with slug: null), so a
brand-new collection isn't 100% aspirational -- see the "generate matching
recipes too" decision in BATCH_CONTENT_PIPELINE_PLAN.md.

Deliberately does NOT touch the collection's own recipe_cards list at all:
main.py's live category_roundup serving path already fills a placeholder
card in by title match against any recipe whose category_link points back
at the collection (see _recipes_linking_to + the title-matching block in
main.py) -- this only needs to publish the recipe correctly, the site
connects it automatically on the next request.

title and category_link are force-set to the known-correct values after
generation rather than trusted to the model: title must match the card's
title exactly (case-insensitive) for the live title-matching fill to find
it, and category_link must point at exactly this collection -- both are
already known with certainty here, so there's no reason to leave either
to chance the way an independent recipe's category_link genuinely is.

Usage:
    python3 content/scripts/generate_companion_recipes.py <collection_slug> [<collection_slug> ...]

Writes content/scripts/output/companion_<collection_slug>.jsonl in the
same {"custom_id", "result": {...}} shape validate_content /
integrate_batch_results.py already understand.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import extract_existing_pages, slugify  # noqa: E402
from prompt_templates import EXAMPLES, MAX_TOKENS_BY_TYPE, MODEL, STYLE_GUIDE, SCHEMA_BY_TYPE, to_strict_schema  # noqa: E402
from validation import extract_content, validate_content  # noqa: E402

MAX_ATTEMPTS = 4
OUTPUT_DIR = Path(__file__).parent / "output"


def find_unlinked_cards(collection_slug: str) -> tuple[str, list[dict]]:
    text = (Path(__file__).resolve().parents[2] / "backend" / "app" / "seed_templates.py").read_text()
    idx = text.index(f'"slug": "{collection_slug}"')
    title_match = re.search(r'"title": "([^"]+)"', text[idx:idx + 200])
    collection_title = title_match.group(1)
    end = text.index('"sub_categories"', idx)
    snippet = text[idx:end]
    cards = re.findall(r'"title": "([^"]+)",\s*\n\s*"slug": None,\s*\n\s*"description": "([^"]+)"', snippet)
    return collection_title, [{"title": t, "description": d} for t, d in cards]


def build_companion_params(card: dict, collection_title: str, collection_slug: str, collections: list[dict], techniques: list[dict]) -> dict:
    schema = SCHEMA_BY_TYPE["recipe_or_dish"]
    example = EXAMPLES["recipe_or_dish"]
    collection_list = "\n".join(f"- {c['title']} (slug: {c['slug']})" for c in collections)
    technique_list = "\n".join(f"- {t['title']} (slug: {t['slug']})" for t in techniques)

    user_message = (
        "Write the content for one new Tulo recipe page.\n\n"
        f"This recipe is being written specifically to fill an existing planned entry on the "
        f"\"{collection_title}\" collection page. Use this EXACT title, verbatim, not a paraphrase: "
        f"\"{card['title']}\"\n"
        f"Planned description for this dish: {card['description']}\n\n"
        f"Existing collections available for category_link (use one of these exactly, "
        "or null if none genuinely fit, never invent a new one):\n" + collection_list + "\n\n"
        "Existing how-to pages available for technique_link (use one of these exactly, "
        "or null if the recipe doesn't rely on one of these specific techniques):\n" + technique_list + "\n\n"
        "Here is a real, already-published example of this template type, showing the "
        "expected tone, depth, and exact field usage:\n\n"
        + json.dumps(example, indent=2, ensure_ascii=False)
        + "\n\nNow write a complete, original recipe matching the exact title and description above, "
        "in the same style and depth."
    )

    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS_BY_TYPE["recipe_or_dish"],
        "system": STYLE_GUIDE,
        "messages": [{"role": "user", "content": user_message}],
        "output_config": {"format": {"type": "json_schema", "schema": to_strict_schema(schema)}},
    }


def call_messages_api(params: dict, api_key: str) -> dict:
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(params).encode(),
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main() -> None:
    collection_slugs = sys.argv[1:]
    if not collection_slugs:
        print("Usage: python3 generate_companion_recipes.py <collection_slug> [<collection_slug> ...]")
        raise SystemExit(1)

    api_key = os.environ["PIPELINE_ANTHROPIC_API_KEY"]
    existing_slugs, collections, techniques = extract_existing_pages()
    collection_slug_set = {c["slug"] for c in collections}
    technique_slug_set = {t["slug"] for t in techniques}

    for collection_slug in collection_slugs:
        collection_title, cards = find_unlinked_cards(collection_slug)
        print(f"\n=== {collection_title} ({collection_slug}): {len(cards)} unlinked card(s) ===")

        fixed_lines = []
        taken = set(existing_slugs)
        for card in cards:
            custom_id = slugify(card["title"])
            base = custom_id
            n = 2
            while custom_id in taken:
                custom_id = f"{base}-{n}"
                n += 1
            taken.add(custom_id)

            params = build_companion_params(card, collection_title, collection_slug, collections, techniques)

            for attempt in range(1, MAX_ATTEMPTS + 1):
                print(f"[{custom_id}] attempt {attempt}/{MAX_ATTEMPTS}...")
                message = call_messages_api(params, api_key)
                try:
                    content = extract_content(message)
                except (ValueError, json.JSONDecodeError) as e:
                    print(f"  -> couldn't extract content ({e}), retrying")
                    continue

                # Force the two fields that MUST be exactly right for the
                # live auto-fill to find this recipe -- see module docstring.
                content["title"] = card["title"]
                content["category_link"] = {"title": collection_title, "slug": collection_slug}

                problems = validate_content(custom_id, "recipe_or_dish", content, collection_slug_set, technique_slug_set)
                if not problems:
                    print("  -> clean")
                    message["content"] = [{"type": "text", "text": json.dumps(content)}]
                    fixed_lines.append({"custom_id": custom_id, "result": {"type": "succeeded", "message": message}})
                    break
                print(f"  -> issues: {problems}")
            else:
                print(f"[{custom_id}] FAILED after {MAX_ATTEMPTS} attempts")

        out_path = OUTPUT_DIR / f"companion_{collection_slug}.jsonl"
        OUTPUT_DIR.mkdir(exist_ok=True)
        with out_path.open("w") as out:
            for line in fixed_lines:
                out.write(json.dumps(line, ensure_ascii=False) + "\n")
        print(f"Wrote {len(fixed_lines)}/{len(cards)} companion recipes to {out_path}")


if __name__ == "__main__":
    main()
