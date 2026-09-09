"""Regenerates specific failed rows from a batch via the live (non-batch)
Messages API, retrying each up to a few times until it passes the same
validation as validate_batch_results.py. For a small, bounded fix-pass list
(see BATCH_CONTENT_PIPELINE_PLAN.md Phase 2 step 6) -- not meant for
hundreds of rows, which would go through a second small Batch request
instead.

Usage:
    ANTHROPIC_API_KEY=... python3 content/scripts/fix_pass.py \
        content/pilot_batch_50.csv custom_id_1 custom_id_2 ...

Writes content/scripts/output/<csv_stem>_fixed.jsonl in the same
{"custom_id", "result": {"type": "succeeded", "message": {...}}} shape as a
batch results line, so validate_batch_results.py and the integration script
can treat it identically to a normal batch result.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import (  # noqa: E402
    build_id_to_row,
    extract_existing_pages,
    load_id_to_row_from_manifest,
)
from prompt_templates import build_request_params  # noqa: E402
from validation import extract_content, validate_content  # noqa: E402

MAX_ATTEMPTS = 4


def call_messages_api(params: dict, api_key: str) -> dict:
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(params).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main() -> None:
    csv_path = Path(sys.argv[1])
    target_custom_ids = sys.argv[2:]
    if not target_custom_ids:
        print("Usage: python3 fix_pass.py <csv> <custom_id> [<custom_id> ...]")
        raise SystemExit(1)

    api_key = os.environ["PIPELINE_ANTHROPIC_API_KEY"]

    existing_slugs, collections, techniques, hubs = extract_existing_pages()
    collection_slugs = {c["slug"] for c in collections}
    technique_slugs = {t["slug"] for t in techniques}
    hub_slugs = {h["slug"] for h in hubs}

    manifest_path = Path(__file__).parent / "output" / f"{csv_path.stem}_manifest.json"
    if manifest_path.exists():
        id_to_row = load_id_to_row_from_manifest(csv_path, manifest_path)
    else:
        print(f"WARNING: no manifest at {manifest_path}, re-deriving custom_ids -- "
              "only safe if seed_templates.py hasn't changed since this batch was built.")
        id_to_row = build_id_to_row(csv_path, existing_slugs)

    output_path = Path(__file__).parent / "output" / f"{csv_path.stem}_fixed.jsonl"
    fixed_lines = []

    for custom_id in target_custom_ids:
        row = id_to_row.get(custom_id)
        if row is None:
            print(f"[{custom_id}] ERROR: could not find matching CSV row, skipping")
            continue

        template_type = row["template_type"]
        params = build_request_params(row, collections, techniques)

        for attempt in range(1, MAX_ATTEMPTS + 1):
            print(f"[{custom_id}] attempt {attempt}/{MAX_ATTEMPTS}...")
            message = call_messages_api(params, api_key)
            try:
                content = extract_content(message)
            except (ValueError, json.JSONDecodeError) as e:
                print(f"  -> couldn't extract content ({e}), retrying")
                continue
            problems = validate_content(custom_id, template_type, content, collection_slugs, technique_slugs, hub_slugs)
            if not problems:
                print(f"  -> clean")
                fixed_lines.append({
                    "custom_id": custom_id,
                    "result": {"type": "succeeded", "message": message},
                })
                break
            print(f"  -> still has issues: {problems}")
        else:
            print(f"[{custom_id}] FAILED after {MAX_ATTEMPTS} attempts, needs manual attention")

    with output_path.open("w") as out:
        for line in fixed_lines:
            out.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(fixed_lines)}/{len(target_custom_ids)} fixed results to {output_path}")


if __name__ == "__main__":
    main()
