"""Full-site backfill: real nutrition_per_unit data for every ingredient_hub
substitute that has a ratio_multiplier but is still missing it -- the same
gap fixed by hand for olive-oil/balsamic-vinegar (see that commit), at the
site's actual remaining scale (962 of 991 hubs as of 2026-09-14, ~3,766
substitute entries). The generation schema (prompt_templates.py's
INGREDIENT_HUB_SCHEMA) already makes this required going forward for any
NEW hub; this is the one-time catch-up for everything already live.

One real-time Messages API call per hub (not per substitute -- a hub
typically has 2-6 substitutes, so this keeps request count at ~962 rather
than ~3,766, and gives the model the whole hub's context in one shot),
using the same bounded-concurrency real-time pattern as
submit_realtime_fallback.py. Nutrition values are requested in whatever
single customary unit this specific ingredient is normally measured in
(matching NUTRITION_PER_UNIT_SCHEMA's own convention, e.g. per tablespoon
for an oil, per cup for a flour) -- the model reports which unit it used
(unit_used) for validation/spot-checking, but that field is never written
to seed_templates.py itself; nutrition_per_unit has always been implicitly
"per 1 of whatever unit the recipe's own ingredient entry uses," matching
how a swap's live math already works (RecipeIngredientsPanel.tsx multiplies
the ORIGINAL ingredient's own base_qty by ratio_multiplier, then by
nutrition_per_unit -- so the two must already agree on units by editorial
convention, the same way this site's actually-published recipes always
measure a given pantry ingredient in the same customary unit).

Patches seed_templates.py's source TEXT directly (never a full
re-serialization, which would destroy every hand-written "#" comment in the
file) using each hub entry's own AST node positions to find exactly where
each substitute dict's closing brace is, regardless of whether that dict is
written single-line or multi-line in the source -- far more robust at this
scale than a regex that has to handle thousands of inconsistently-formatted
dicts.

Usage:
    PIPELINE_ANTHROPIC_API_KEY=... python3 content/scripts/backfill_substitute_nutrition.py \\
        [--limit N] [--concurrency 10] [--dry-run] [--slugs slug1,slug2,...]

    --limit N        Only process the first N hubs needing backfill (for a
                      test run before committing to the full ~962).
    --slugs a,b,c    Only process these specific hub slugs (overrides --limit).
    --dry-run        Do everything except write seed_templates.py -- prints
                      what WOULD be patched instead.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_TEMPLATES_PATH = REPO_ROOT / "backend" / "app" / "seed_templates.py"

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"
DEFAULT_CONCURRENCY = 10
MAX_ATTEMPTS = 3

ENTRY_SPLIT_RE = re.compile(r'(?=    \{\n        "slug")')

NUTRITION_FIELDS = ("calories", "protein_g", "carbs_g", "fat_g")

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "unit_used": {
            "type": "string",
            "description": "The single customary unit you're reporting nutrition per one of (e.g. 'tablespoon', 'teaspoon', 'cup', 'ounce') -- must be the same unit this ingredient is normally measured in on this site, not an arbitrary one.",
        },
        "substitutes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Must exactly match one of the substitute names given to you, verbatim."},
                    "calories": {"type": "number"},
                    "protein_g": {"type": "number"},
                    "carbs_g": {"type": "number"},
                    "fat_g": {"type": "number"},
                },
                "required": ["name", "calories", "protein_g", "carbs_g", "fat_g"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["unit_used", "substitutes"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are providing real, accurate nutrition data for a food website's ingredient-substitute swap feature. For a given ingredient and a list of its common substitutes, report real per-unit nutrition (calories, protein, carbs, fat) for EACH substitute, all expressed per the SAME single customary unit -- the unit this ingredient is normally measured in in a home recipe (e.g. tablespoon for an oil or vinegar, teaspoon for a spice, cup for a flour or a liquid used in volume, ounce for a cheese).

Use real, standard nutrition data (USDA-style figures) for each substitute as it's actually consumed/used (e.g. "melted butter" as melted butter, not raw cold butter if that changes the relevant figure -- it usually doesn't for butter, but consider it for anything where preparation state matters). Be realistic: a substitute's numbers should differ sensibly from the original ingredient's own real nutrition where the two genuinely differ (a sugar substitute isn't zero-calorie unless it truly is), and should NOT differ if they're nutritionally almost identical (two very similar oils).

Report the exact unit you used (unit_used) and give every substitute name back verbatim as given to you, in the same order. Do not skip any."""


def build_user_prompt(hub_title: str, hub_description: str, substitutes: list[dict]) -> str:
    lines = [
        f"Ingredient: {hub_title}",
        f"Description: {hub_description}" if hub_description else "",
        "",
        "Substitutes needing nutrition data (report per the same one customary unit for all of them):",
    ]
    for sub in substitutes:
        ratio_note = f" (ratio: {sub['ratio']})" if sub.get("ratio") else ""
        lines.append(f'- "{sub["name"]}"{ratio_note}: {sub.get("note", "")}')
    return "\n".join(l for l in lines if l is not None)


def extract_needs() -> list[dict]:
    """Every ingredient_hub whose content has at least one substitute with a
    real ratio_multiplier but no nutrition_per_unit yet. Imports
    seed_templates.py directly (the real, live SEED_PAGES structure) rather
    than re-parsing the source text for this part -- only the later patch
    step needs to operate on raw text, to preserve comments/formatting."""
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from app.seed_templates import SEED_PAGES  # noqa: E402

    needs = []
    for page in SEED_PAGES:
        if page["template_type"] != "ingredient_hub":
            continue
        content = page["content"]
        missing = [
            sub
            for sub in content.get("substitutes", [])
            if sub.get("ratio_multiplier") is not None and "nutrition_per_unit" not in sub
        ]
        if missing:
            needs.append(
                {
                    "slug": page["slug"],
                    "title": page["title"],
                    "description": content.get("description", ""),
                    "substitutes": [
                        {"name": s["name"], "ratio": s.get("ratio", ""), "note": s.get("note", "")}
                        for s in missing
                    ],
                }
            )
    return needs


def build_request_params(hub: dict) -> dict:
    return {
        "model": MODEL,
        "max_tokens": 3000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": build_user_prompt(hub["title"], hub["description"], hub["substitutes"])}],
        "output_config": {"format": {"type": "json_schema", "schema": RESPONSE_SCHEMA}},
    }


def call_one(hub: dict, api_key: str) -> dict:
    """Real-time call for one hub, MAX_ATTEMPTS retries -- mirrors
    submit_realtime_fallback.py's call_one shape (succeeded/errored), plus
    response-shape validation (every requested substitute name must come
    back, case-sensitive exact match) since a silently-wrong or
    silently-missing substitute here would be far more costly than a
    missing image."""
    params = build_request_params(hub)
    expected_names = {s["name"] for s in hub["substitutes"]}
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(params).encode(),
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                message = json.loads(resp.read())
            text = "".join(block["text"] for block in message["content"] if block["type"] == "text")
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as e:
                # Real, confirmed (2026-09-14): a full 957-hub run hit this
                # on 20 hubs, all 3 attempts, with a 200 OK but an empty or
                # truncated `text` -- stop_reason here is exactly the clue
                # needed to tell "ran out of max_tokens" (stop_reason ==
                # "max_tokens", the actual bug) apart from some other
                # response shape, without having to reproduce it blind.
                stop_reason = message.get("stop_reason", "?")
                raise ValueError(f"{e} (stop_reason={stop_reason}, response text length={len(text)})") from e
            returned_names = {s["name"] for s in parsed["substitutes"]}
            if returned_names != expected_names:
                last_error = f"name mismatch: expected {expected_names}, got {returned_names}"
                print(f"  [{hub['slug']}] attempt {attempt}: {last_error}")
                continue
            for sub in parsed["substitutes"]:
                for field in NUTRITION_FIELDS:
                    val = sub[field]
                    if not isinstance(val, (int, float)) or val < 0:
                        raise ValueError(f"{sub['name']}.{field} = {val!r} is not a valid non-negative number")
            return {"slug": hub["slug"], "status": "succeeded", "unit_used": parsed["unit_used"], "substitutes": parsed["substitutes"]}
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            last_error = f"HTTP {e.code}: {body[:300]}"
            if e.code == 429:
                time.sleep(5 * attempt)
        except Exception as e:
            last_error = str(e)
            # A non-429 failure retried with zero delay in a
            # concurrency=10 loop just repeats the same request under the
            # same conditions -- confirmed live (2026-09-14): 20/957 hubs
            # got an empty/malformed response on ALL 3 immediate-retry
            # attempts. A short backoff gives a transient issue (API load,
            # a momentary hiccup) an actual chance to have cleared by the
            # next attempt instead of just re-hitting it instantly.
            time.sleep(3 * attempt)
        print(f"  [{hub['slug']}] attempt {attempt}/{MAX_ATTEMPTS} failed: {last_error}")
    return {"slug": hub["slug"], "status": "errored", "error": last_error}


# ---------------------------------------------------------------------------
# Source-text patching -- AST-position-based, never a full re-serialization.
# ---------------------------------------------------------------------------


def _leading_balanced_dict_text(text: str) -> str:
    """Returns just the leading `{...}` (matching braces, string/escape
    aware) from the start of `text`, discarding everything after its
    closing brace. Needed because ENTRY_SPLIT_RE's split only inserts a
    boundary *before* each entry's own "{" -- the very LAST entry in
    SEED_PAGES has no following entry to bound it, so its raw entry_text
    also carries everything after the list closes (the seed()/
    resync_content() function bodies, etc.), which would break a bare
    `ast.parse(entry_text, mode="eval")` for that one entry."""
    text = text.lstrip()
    assert text.startswith("{")
    depth = 0
    in_string: str | None = None
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_string:
                in_string = None
            continue
        if ch in "\"'":
            in_string = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[: i + 1]
    raise ValueError("no balanced closing brace found")


def _dict_node_for_substitute(entry_text: str, target_name: str) -> ast.Dict | None:
    """Parses this one hub's entry text (a standalone `{...},` fragment) and
    returns the ast.Dict node for the substitute whose "name" == target_name,
    or None if not found. Isolates just the leading balanced `{...}` first
    (see _leading_balanced_dict_text) so trailing content after the dict --
    a comment before the next entry, or (for the last entry in SEED_PAGES)
    the module's trailing function definitions -- can never break the
    parse."""
    tree = ast.parse(_leading_balanced_dict_text(entry_text), mode="eval")
    node = tree.body
    if isinstance(node, ast.Tuple):
        node = node.elts[0]
    assert isinstance(node, ast.Dict)

    def _get(d: ast.Dict, key: str) -> ast.expr | None:
        for k, v in zip(d.keys, d.values):
            if isinstance(k, ast.Constant) and k.value == key:
                return v
        return None

    content_node = _get(node, "content")
    if content_node is None or not isinstance(content_node, ast.Dict):
        return None
    substitutes_node = _get(content_node, "substitutes")
    if substitutes_node is None or not isinstance(substitutes_node, ast.List):
        return None
    for sub_node in substitutes_node.elts:
        if not isinstance(sub_node, ast.Dict):
            continue
        name_node = _get(sub_node, "name")
        if isinstance(name_node, ast.Constant) and name_node.value == target_name:
            return sub_node
    return None


def _line_col_to_offset(text: str, line: int, col: int) -> int:
    """ast line numbers are 1-indexed; col is a 0-indexed offset into that
    line, but CPython's ast reports it in UTF-8 BYTES, not characters --
    confirmed live (2026-09-14): this broke on the very first full-dataset
    dry run, on creme-fraiche's "Mascarpone thinned with a little cream"
    substitute, one line after a "e with grave" in a nearby ingredient
    name shifted every subsequent byte offset on affected lines ahead of
    the true character offset. Decoding the line's UTF-8-truncated-to-col
    bytes back to a str and taking its length converts byte offset -> the
    real character offset this function actually needs."""
    lines = text.split("\n")
    line_text = lines[line - 1]
    char_col = len(line_text.encode("utf-8")[:col].decode("utf-8"))
    return sum(len(l) + 1 for l in lines[: line - 1]) + char_col


def _indent_of_line(text: str, offset: int) -> str:
    line_start = text.rfind("\n", 0, offset) + 1
    line = text[line_start:offset]
    return line[: len(line) - len(line.lstrip(" "))]


def patch_entry(entry_text: str, hub_slug: str, result: dict) -> str:
    """Applies every substitute's new nutrition_per_unit to this one hub's
    entry text, using AST node end-positions to know exactly where each
    substitute dict's closing brace is -- collecting all insertion points
    first, then applying them in reverse offset order so an earlier
    insertion never invalidates a later one's already-computed offset."""
    insertions: list[tuple[int, str]] = []
    for sub in result["substitutes"]:
        node = _dict_node_for_substitute(entry_text, sub["name"])
        if node is None:
            print(f"  [{hub_slug}] WARNING: couldn't locate substitute {sub['name']!r} in source text, skipping this one")
            continue
        end_offset = _line_col_to_offset(entry_text, node.end_lineno, node.end_col_offset)
        # end_offset points just past the dict's closing "}" -- back up one
        # to find it.
        close_brace_offset = end_offset - 1
        assert entry_text[close_brace_offset] == "}", (hub_slug, sub["name"], entry_text[close_brace_offset - 5 : close_brace_offset + 5])

        is_single_line = node.lineno == node.end_lineno
        nutrition_literal = (
            "{"
            + ", ".join(f'"{f}": {sub[f]}' for f in NUTRITION_FIELDS)
            + "}"
        )
        if is_single_line:
            insertion_offset = close_brace_offset
            insertion = f', "nutrition_per_unit": {nutrition_literal}'
        else:
            # Insert a whole new line *before* the closing brace's own line
            # (not right before the "}" character itself) -- inserting at
            # the brace position would leave that line's original leading
            # whitespace dangling with no newline after it, and glue the
            # new key onto the same line as the "}," that follows it.
            # Anchoring at the start of the close-brace's line instead
            # keeps that original "                }," line completely
            # untouched, just pushed down by one line.
            close_line_start = entry_text.rfind("\n", 0, close_brace_offset) + 1
            close_line_indent = _indent_of_line(entry_text, close_brace_offset)
            key_indent = close_line_indent + "    "
            insertion_offset = close_line_start
            insertion = f'{key_indent}"nutrition_per_unit": {nutrition_literal},\n'
        insertions.append((insertion_offset, insertion))

    for offset, insertion in sorted(insertions, key=lambda x: x[0], reverse=True):
        entry_text = entry_text[:offset] + insertion + entry_text[offset:]
    return entry_text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--slugs", default=None, help="Comma-separated hub slugs to process; overrides --limit.")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Bake locally and leave seed_templates.py staged/uncommitted -- for local dry runs. "
        "Default (no flag) commits and pushes to staging, matching audit_and_bake_all_images.py's pattern.",
    )
    args = parser.parse_args()

    api_key = os.environ["PIPELINE_ANTHROPIC_API_KEY"]

    needs = extract_needs()
    print(f"{len(needs)} ingredient_hub page(s) need backfill.")

    if args.slugs:
        wanted = set(args.slugs.split(","))
        needs = [h for h in needs if h["slug"] in wanted]
        missing = wanted - {h["slug"] for h in needs}
        if missing:
            print(f"WARNING: requested slugs not found among those needing backfill: {missing}")
    elif args.limit is not None:
        needs = needs[: args.limit]

    print(f"Processing {len(needs)} hub(s), concurrency={args.concurrency}...")

    results = []
    done = 0
    start = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(call_one, hub, api_key): hub["slug"] for hub in needs}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            print(f"[{done}/{len(needs)}] {result['slug']}: {result['status']} ({time.time() - start:.0f}s elapsed)")

    succeeded = [r for r in results if r["status"] == "succeeded"]
    errored = [r for r in results if r["status"] == "errored"]
    print(f"\n{len(succeeded)}/{len(results)} succeeded in {time.time() - start:.0f}s.")
    if errored:
        print(f"{len(errored)} failed after {MAX_ATTEMPTS} attempts:")
        for r in errored:
            print(f"  {r['slug']}: {r['error']}")

    if not succeeded:
        print("Nothing to patch.")
        return

    def build_patched_text() -> tuple[str, list[str]]:
        """Reads seed_templates.py FRESH (not whatever was on disk when
        this run started) and applies every succeeded result -- so a
        retry after `git reset --hard origin/staging` re-patches onto
        the latest content instead of the stale copy this process
        started with."""
        text = SEED_TEMPLATES_PATH.read_text()
        parts = ENTRY_SPLIT_RE.split(text)
        header, entries = parts[0], parts[1:]
        entry_by_slug: dict[str, int] = {}
        for i, entry in enumerate(entries):
            m = re.search(r'"slug": "([^"]+)"', entry)
            if m:
                entry_by_slug[m.group(1)] = i

        patched = []
        for result in succeeded:
            idx = entry_by_slug.get(result["slug"])
            if idx is None:
                print(f"WARNING: {result['slug']} not found in seed_templates.py entries, skipping")
                continue
            entries[idx] = patch_entry(entries[idx], result["slug"], result)
            patched.append(result["slug"])

        new_text = header + "".join(entries)
        # Never trust this output without a real syntax check -- a single
        # off-by-one in the AST-position math would silently corrupt the
        # 275K-line file otherwise.
        compile(new_text, str(SEED_TEMPLATES_PATH), "exec")
        return new_text, patched

    new_text, patched_slugs = build_patched_text()
    print(f"\nSyntax check passed. Patched {len(patched_slugs)} hub(s): {patched_slugs}")

    if args.dry_run:
        print("--dry-run: not writing seed_templates.py.")
        return

    if args.no_push:
        SEED_TEMPLATES_PATH.write_text(new_text)
        print(f"--no-push: wrote {SEED_TEMPLATES_PATH}, left modified and uncommitted.")
        return

    def run(*cmd_args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(cmd_args, cwd=str(REPO_ROOT), check=check)

    run("git", "config", "user.name", "tulo-content-bot")
    run("git", "config", "user.email", "content-bot@users.noreply.github.com")

    message = (
        f"Backfill nutrition_per_unit for {len(patched_slugs)} ingredient_hub substitute(s)\n\n"
        "One-time catch-up run of content/scripts/backfill_substitute_nutrition.py "
        "(see its own docstring) -- real per-unit nutrition data for existing "
        "ingredient-substitute swaps that predate INGREDIENT_HUB_SCHEMA making this "
        "required. Makes the ingredient-swap/live-calorie-counter module active on "
        "any recipe whose ingredient resolves to one of these hubs.\n\n"
        "Staging-only until a human reviews and merges this to main.\n"
    )

    # Commit + push with a fetch/reset/re-patch retry on a non-fast-forward
    # rejection -- real, confirmed (2026-09-14): an unrelated commit landed
    # on staging while this ran (a ~18-minute, 957-request real API job),
    # and losing the push meant losing all 937 already-paid-for results
    # with no way to recover them since the runner's workspace is gone the
    # moment the job ends. Retrying is cheap; re-running the whole batch
    # from scratch after a lost push is not.
    MAX_PUSH_ATTEMPTS = 3
    for push_attempt in range(1, MAX_PUSH_ATTEMPTS + 1):
        SEED_TEMPLATES_PATH.write_text(new_text)
        run("git", "add", str(SEED_TEMPLATES_PATH))
        status = subprocess.run(
            ["git", "status", "--porcelain", str(SEED_TEMPLATES_PATH)],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
        )
        if not status.stdout.strip():
            print("\nNo changes to commit (unexpected -- a successful patch should always change the file).")
            return
        run("git", "commit", "-m", message)
        push_result = run("git", "push", "origin", "HEAD:staging", check=False)
        if push_result.returncode == 0:
            print("\nCommitted and pushed to staging.")
            return
        print(f"\nPush attempt {push_attempt}/{MAX_PUSH_ATTEMPTS} rejected (remote moved) -- "
              "fetching, resetting to latest staging, and re-patching before retrying.")
        run("git", "fetch", "origin", "staging")
        run("git", "reset", "--hard", "origin/staging")
        new_text, patched_slugs = build_patched_text()
        print(f"Re-patched against latest staging: {len(patched_slugs)} hub(s): {patched_slugs}")

    # All retries exhausted -- do NOT let 937+ hubs' worth of real,
    # already-paid-for API output just vanish with the runner's workspace.
    # Leave it on disk, uncommitted, so the workflow's own artifact-upload
    # step (see backfill-substitute-nutrition.yml, `if: always()`) can
    # still capture it for manual recovery even though this run "failed."
    SEED_TEMPLATES_PATH.write_text(new_text)
    print(
        f"\nERROR: push still rejected after {MAX_PUSH_ATTEMPTS} attempts. "
        f"Left the patched file at {SEED_TEMPLATES_PATH} (uncommitted) instead of losing it -- "
        "recover it from this run's uploaded artifact and apply by hand."
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
