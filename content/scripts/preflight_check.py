"""Mandatory pre-flight gate: run this before submitting ANY real batch
(pilot or full), and any time prompt_templates.py's schemas change. Exits
non-zero if anything here would have broken the pilot the same way real
bugs actually broke it that run -- see "Bulletproofing the next batch" in
BATCH_CONTENT_PIPELINE_PLAN.md for the full incident list this gate closes.

What it checks, and which real incident each one guards against:
1. check_schemas_match_types.py -- every schema covers every field
   frontend/lib/types.ts actually requires. (Guards against the
   how-to-make-garlic-confit crash: a schema silently missing a required
   field.)
2. check_queue_duplicates.py -- CONTENT_QUEUE.csv has no queue/queue or
   queue/published topic collision. (Guards against the corn-starch /
   gruyère-cheese collisions found by chance in the 50-row pilot.)
3. **One real generation per template type, against the live Messages
   API with output_config** -- not a schema re-read, an actual call.
   (Guards against the step_notes/output_config 400 error, which static
   schema review completely missed and only a real test generation
   caught.) Each result is:
   - checked for a clean extract_content() (catches an output_config
     shape the schema can't actually satisfy, a 400, or any other
     request-level failure)
   - run through validate_content() (catches type/field problems the
     same way a real batch result would be caught)
   - checked for max_tokens headroom (catches a budget that's too tight
     before it silently truncates a large fraction of a real batch)

This makes "did this work" a thing this script proves empirically before
any spend commitment, instead of something inferred from re-reading code
that already looked right once and still weren't (this is the exact
failure mode that let the step_notes bug reach a real 48-page pilot).

Usage:
    PIPELINE_ANTHROPIC_API_KEY=... python3 content/scripts/preflight_check.py
    PIPELINE_ANTHROPIC_API_KEY=... python3 content/scripts/preflight_check.py content/pilot_batch_50.csv
"""

from __future__ import annotations

import csv
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import extract_existing_pages  # noqa: E402
from prompt_templates import MAX_TOKENS_BY_TYPE, SCHEMA_BY_TYPE, build_request_params  # noqa: E402
from validation import extract_content, validate_content  # noqa: E402
import check_queue_duplicates  # noqa: E402
import check_schemas_match_types  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUEUE_PATH = REPO_ROOT / "content" / "CONTENT_QUEUE.csv"
TOKEN_HEADROOM_WARN_THRESHOLD = 0.85


def call_messages_api(params: dict, api_key: str) -> dict:
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(params).encode(),
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def pick_sample_row_per_type(csv_path: Path) -> dict[str, dict]:
    """One representative not_started row per template_type actually
    present in this batch's CSV -- exercises build_request_params() the
    same way the real batch will, rather than a synthetic hand-written
    prompt that might not match what actually gets submitted."""
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    sample: dict[str, dict] = {}
    for row in rows:
        t = row.get("template_type")
        if row.get("status") == "not_started" and t in SCHEMA_BY_TYPE and t not in sample:
            sample[t] = row
    return sample


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_QUEUE_PATH
    failures: list[str] = []

    print("=== 1. Schema completeness vs. frontend/lib/types.ts ===")
    try:
        check_schemas_match_types.main()
    except SystemExit:
        failures.append("check_schemas_match_types.py found a gap")
    print()

    print(f"=== 2. Duplicate/collision check against {csv_path} ===")
    try:
        check_queue_duplicates.main()
    except SystemExit:
        failures.append("check_queue_duplicates.py found an exact collision")
    print()

    print("=== 3. Real per-template-type generation via output_config ===")
    api_key = os.environ.get("PIPELINE_ANTHROPIC_API_KEY")
    if not api_key:
        print("SKIPPED: PIPELINE_ANTHROPIC_API_KEY not set -- this is the single most important "
              "check (it's the one that actually caught the step_notes/output_config 400 error "
              "that static schema review missed) and should not be skipped before a real batch.")
        failures.append("live generation check skipped -- no API key")
    else:
        existing_slugs, collections, techniques = extract_existing_pages()
        collection_slugs = {c["slug"] for c in collections}
        technique_slugs = {t["slug"] for t in techniques}
        sample_rows = pick_sample_row_per_type(csv_path)

        for template_type in SCHEMA_BY_TYPE:
            row = sample_rows.get(template_type)
            if row is None:
                print(f"[{template_type}] no not_started row of this type in {csv_path}, skipping")
                continue
            print(f"[{template_type}] generating from real row {row['title']!r}...")
            params = build_request_params(row, collections, techniques)
            try:
                message = call_messages_api(params, api_key)
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")
                print(f"  -> HTTP {e.code}: {body[:500]}")
                failures.append(f"[{template_type}] request-level failure: HTTP {e.code}")
                continue

            try:
                content = extract_content(message)
            except (ValueError, json.JSONDecodeError) as e:
                print(f"  -> couldn't extract content: {e}")
                failures.append(f"[{template_type}] couldn't extract content: {e}")
                continue

            issues = validate_content(row["title"], template_type, content, collection_slugs, technique_slugs)
            if issues:
                print(f"  -> {len(issues)} validation issue(s):")
                for issue in issues:
                    print(f"     - {issue}")
                failures.append(f"[{template_type}] {len(issues)} validation issue(s)")
            else:
                print("  -> clean")

            usage = message.get("usage", {})
            output_tokens = usage.get("output_tokens", 0)
            budget = MAX_TOKENS_BY_TYPE[template_type]
            if output_tokens / budget >= TOKEN_HEADROOM_WARN_THRESHOLD:
                print(f"  -> WARNING: used {output_tokens}/{budget} tokens "
                      f"({output_tokens / budget:.0%}) of its max_tokens budget")
                failures.append(f"[{template_type}] low max_tokens headroom: {output_tokens}/{budget}")

    print()
    if failures:
        print(f"PRE-FLIGHT FAILED: {len(failures)} problem(s) found. Do not submit the real batch yet:")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)
    print("PRE-FLIGHT PASSED: schemas complete, no queue collisions, all template types generate "
          "and validate cleanly with healthy max_tokens headroom. Safe to submit.")


if __name__ == "__main__":
    main()
