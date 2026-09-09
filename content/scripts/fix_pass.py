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

import csv
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import extract_existing_pages, slugify  # noqa: E402
from prompt_templates import build_request_params  # noqa: E402
from validation import validate_content  # noqa: E402

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


def find_row_for_custom_id(rows: list[dict], custom_id: str, taken_slugs: set) -> dict:
    """custom_id was built by unique_slug(row['title'], existing_slugs) at
    build time. Rebuild the same mapping fresh to find which row produced it."""
    for row in rows:
        base = slugify(row["title"])
        candidate = base
        n = 2
        while candidate in taken_slugs:
            candidate = f"{base}-{n}"
            n += 1
        taken_slugs.add(candidate)
        if candidate == custom_id:
            return row
    raise ValueError(f"No row found producing custom_id {custom_id!r}")


def main() -> None:
    csv_path = Path(sys.argv[1])
    target_custom_ids = sys.argv[2:]
    if not target_custom_ids:
        print("Usage: python3 fix_pass.py <csv> <custom_id> [<custom_id> ...]")
        raise SystemExit(1)

    api_key = os.environ["PIPELINE_ANTHROPIC_API_KEY"]

    with csv_path.open() as f:
        rows = list(csv.DictReader(f))

    existing_slugs, collections, techniques = extract_existing_pages()
    collection_slugs = {c["slug"] for c in collections}
    technique_slugs = {t["slug"] for t in techniques}

    # Re-derive the exact same custom_id assignment build_batch_requests.py
    # used, so we can map custom_id -> original row.
    taken = set(existing_slugs)
    id_to_row = {}
    for row in rows:
        base = slugify(row["title"])
        candidate = base
        n = 2
        while candidate in taken:
            candidate = f"{base}-{n}"
            n += 1
        taken.add(candidate)
        id_to_row[candidate] = row

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
            tool_uses = [c for c in message["content"] if c["type"] == "tool_use"]
            if len(tool_uses) != 1:
                print(f"  -> got {len(tool_uses)} tool_use blocks, retrying")
                continue
            content = tool_uses[0]["input"]
            problems = validate_content(custom_id, template_type, content, collection_slugs, technique_slugs)
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
