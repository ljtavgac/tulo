"""Builds the Batch API request file for a set of CONTENT_QUEUE.csv rows.

Usage:
    python3 content/scripts/build_batch_requests.py content/pilot_batch_50.csv

Reads no API key and makes no network calls -- this only assembles the JSONL
request file (one line per row, matching the Message Batches API's request
shape) plus a manifest with a rough cost/token estimate, so it can be
reviewed before anything is ever submitted. See
content/BATCH_CONTENT_PIPELINE_PLAN.md for the pipeline this is Phase 1b of.

Output goes to content/scripts/output/, gitignored (see .gitignore) since a
request file's exact content is reproducible from the CSV plus these
templates and doesn't need to be tracked, and a results file will later
contain the actual generated page content, which belongs in seed_templates.py
once integrated, not as loose JSON in the repo.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from prompt_templates import MAX_TOKENS_BY_TYPE, build_request_params  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_TEMPLATES_PATH = REPO_ROOT / "backend" / "app" / "seed_templates.py"
OUTPUT_DIR = Path(__file__).parent / "output"

# Rough cost model for the manifest estimate only (not used for anything
# billed) -- Sonnet 5 Batch API pricing confirmed earlier this session:
# $1/MTok input, $5/MTok output. ~4 characters per token is a standard rough
# estimate for English text, good enough for a planning number, not an exact
# one -- the pilot's real usage numbers (returned with the actual batch
# results) replace this estimate once the pilot runs.
INPUT_COST_PER_MTOK = 1.0
OUTPUT_COST_PER_MTOK = 5.0
CHARS_PER_TOKEN = 4
# Real completions rarely use every allotted output token; used only to turn
# max_tokens into a spend estimate, not an actual cap prediction.
ASSUMED_OUTPUT_FRACTION = 0.75


def extract_existing_pages() -> tuple[set[str], list[dict], list[dict]]:
    """Regex-parses SEED_PAGES directly out of seed_templates.py rather than
    importing that module, since importing it would pull in the backend's
    SQLAlchemy dependencies for no reason this script needs. Returns
    (all existing slugs, category_roundup {title, slug} list,
    howto_technique {title, slug} list)."""
    text = SEED_TEMPLATES_PATH.read_text()
    pattern = re.compile(
        r'"slug":\s*"([^"]+)",\s*\n\s*"template_type":\s*"([^"]+)",\s*\n\s*"title":\s*"([^"]+)"'
    )
    all_slugs: set[str] = set()
    collections: list[dict] = []
    techniques: list[dict] = []
    for slug, template_type, title in pattern.findall(text):
        all_slugs.add(slug)
        if template_type == "category_roundup":
            collections.append({"title": title, "slug": slug})
        elif template_type == "howto_technique":
            techniques.append({"title": title, "slug": slug})
    return all_slugs, collections, techniques


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def unique_slug(title: str, taken: set[str]) -> str:
    base = slugify(title)
    slug = base
    n = 2
    while slug in taken:
        slug = f"{base}-{n}"
        n += 1
    taken.add(slug)
    return slug


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <content_queue_csv>")
        raise SystemExit(1)

    csv_path = Path(sys.argv[1])
    with csv_path.open() as f:
        rows = list(csv.DictReader(f))

    existing_slugs, collections, techniques = extract_existing_pages()
    print(f"Found {len(existing_slugs)} existing slugs, {len(collections)} collections, {len(techniques)} how-to pages.")

    OUTPUT_DIR.mkdir(exist_ok=True)
    requests_path = OUTPUT_DIR / f"{csv_path.stem}_requests.jsonl"
    manifest_path = OUTPUT_DIR / f"{csv_path.stem}_manifest.json"

    per_type_counts: dict[str, int] = {}
    total_input_chars = 0
    total_output_tokens_budget = 0
    custom_ids: list[dict] = []

    with requests_path.open("w") as out:
        for row in rows:
            template_type = row["template_type"]
            # Based on the raw queue keyword, not proposed_article_title --
            # that column is a naive "keyword + Recipe" template that's wrong
            # for anything but recipe_or_dish (e.g. "Nigiri" -> "Nigiri
            # Recipe" for an ingredient_hub row). This custom_id is only a
            # stable identifier for pairing a request with its result; the
            # real slug gets derived from the model's own generated `title`
            # field during Phase 2 integration, checked for collisions again
            # at that point.
            slug = unique_slug(row["title"], existing_slugs)

            params = build_request_params(row, collections, techniques)
            line = {"custom_id": slug, "params": params}
            out.write(json.dumps(line, ensure_ascii=False) + "\n")

            per_type_counts[template_type] = per_type_counts.get(template_type, 0) + 1
            total_input_chars += len(params["system"]) + len(params["messages"][0]["content"])
            total_output_tokens_budget += MAX_TOKENS_BY_TYPE[template_type]
            custom_ids.append({"custom_id": slug, "title_hint": row["title"], "template_type": template_type})

    est_input_tokens = total_input_chars / CHARS_PER_TOKEN
    est_output_tokens = total_output_tokens_budget * ASSUMED_OUTPUT_FRACTION
    est_input_cost = est_input_tokens / 1_000_000 * INPUT_COST_PER_MTOK
    est_output_cost = est_output_tokens / 1_000_000 * OUTPUT_COST_PER_MTOK
    est_total_cost = est_input_cost + est_output_cost

    manifest = {
        "source_csv": str(csv_path),
        "total_requests": len(rows),
        "requests_per_template_type": per_type_counts,
        "estimated_input_tokens": round(est_input_tokens),
        "estimated_output_tokens_budget": round(est_output_tokens),
        "estimated_cost_usd": round(est_total_cost, 2),
        "estimated_cost_breakdown": {
            "input_usd": round(est_input_cost, 2),
            "output_usd": round(est_output_cost, 2),
        },
        "note": (
            "Cost estimate only, based on max_tokens budgets and a rough "
            "4-chars-per-token heuristic -- not billed, no API calls were "
            "made building this file. Real usage numbers come back with the "
            "actual batch results."
        ),
        "requests": custom_ids,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"\nWrote {len(rows)} requests to {requests_path}")
    print(f"Wrote manifest to {manifest_path}")
    print(f"\nPer-template-type counts: {per_type_counts}")
    print(f"Estimated cost: ${est_total_cost:.2f} (input ${est_input_cost:.2f} + output budget ${est_output_cost:.2f})")


if __name__ == "__main__":
    main()
