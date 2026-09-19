"""Fully automated daily content pipeline: selects the next N titles from
CONTENT_QUEUE.csv, generates + validates + integrates them into
seed_templates.py, pushes to staging, fetches images, and writes a "new
batch ready for review" summary. This is the whole loop
build_batch_requests.py / submit_realtime_fallback.py /
validate_batch_results.py / integrate_batch_results.py were each built to
handle one step of, by hand, during the pilot -- glued here into one
unattended run instead of a person stepping through each script in turn.

Usage:
    PIPELINE_ANTHROPIC_API_KEY=... \
    BACKEND_BASE_URL=https://your-staging-backend \
    ADMIN_TASK_TOKEN=... \
    python3 content/scripts/daily_batch.py [--count 100] [--dry-run]

Env vars:
    PIPELINE_ANTHROPIC_API_KEY  Anthropic API key for generation (real-time
                                Messages API -- see submit_realtime_fallback.py).
    BACKEND_BASE_URL            The STAGING backend's base URL (no trailing
                                slash) -- never point this at prod. This
                                script only ever pushes to and calls the
                                staging deployment; promotion to prod is a
                                separate, human-gated step (see
                                /admin/review-queue/approve-for-prod).
    ADMIN_TASK_TOKEN            Same token that gates every /admin/* route
                                on the staging backend.
    GMAIL_SMTP_USER,
    GMAIL_SMTP_APP_PASSWORD     Optional. A Gmail address and an App
                                Password for it (Google Account -> Security
                                -> 2-Step Verification -> App passwords --
                                a regular account password won't work for
                                SMTP once 2FA is on). When run from GitHub
                                Actions, GitHub's own workflow-run
                                notification email plus write_job_summary's
                                output (below) already cover "a new batch
                                is ready, here's the link" -- set these two
                                only if a separate, dedicated email is
                                wanted on top of that.
    NOTIFY_EMAIL_TO             Only used if the Gmail vars above are set.
                                Defaults to ljtavgac@gmail.com if unset.

Meant to run from a scheduled GitHub Actions workflow (see
.github/workflows/daily-batch.yml) with `contents: write` permission,
checked out at the `staging` branch. Every git operation below pushes to
`staging` only, never `main`.

--dry-run stops right after local verification, before any git push, image
fetch, or email -- selection, generation, validation, and the
seed_templates.py insertion all still happen for real (a genuine end-to-end
test of the content pipeline itself), just nothing leaves this machine.
CONTENT_QUEUE.csv and seed_templates.py are left modified on disk either
way; run this in a scratch clone for a real dry run, not a working tree
with uncommitted work in progress.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import smtplib
import subprocess
import sys
import tempfile
import time
from email.mime.text import MIMEText
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from bake_images_from_staging import bake  # noqa: E402
from build_batch_requests import extract_existing_pages, load_id_to_row_from_manifest  # noqa: E402
from generate_companion_recipes import find_unlinked_cards  # noqa: E402
from validation import extract_content, validate_content  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = REPO_ROOT / "content" / "CONTENT_QUEUE.csv"
SEED_TEMPLATES_PATH = REPO_ROOT / "backend" / "app" / "seed_templates.py"
SCRIPTS_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPTS_DIR / "output"

DEFAULT_COUNT = 100
QUEUE_FIELDNAMES = [
    "batch_number", "status", "title", "template_type", "volume", "kdi", "tier",
    "cluster_capture_potential", "proposed_article_title", "page_purpose", "category",
]

# Matches format_page_entry()'s exact, fixed key order in
# integrate_batch_results.py (slug, template_type, title, batch_number) --
# used to read back which slugs actually landed under a given batch_number
# after integration, rather than assuming a result's custom_id always
# equals its final slug (it doesn't: the final slug is derived from the
# *model's own* returned title, which can differ from the CSV title the
# custom_id was built from).
_PAGE_HEADER_RE = re.compile(
    r'"slug":\s*"([^"]+)",\s*\n\s*"template_type":\s*"[^"]+",\s*\n'
    r'\s*"title":\s*"(?:[^"\\]|\\.)*",\s*\n\s*"batch_number":\s*(\d+),'
)


def _slugs_for_batch(batch_number: int) -> list[str]:
    text = SEED_TEMPLATES_PATH.read_text()
    return [m.group(1) for m in _PAGE_HEADER_RE.finditer(text) if int(m.group(2)) == batch_number]


# Matches _PAGE_HEADER_RE above but pinned to template_type "category_roundup"
# specifically -- used right after the main batch's own integration to find
# any collection pages this run just created, so their still-unlinked cards
# (see generate_companion_recipes.py) get real matching recipes generated
# for them in the same run, instead of shipping a collection whose cards
# aren't clickable (the exact gap hit live on beets-recipes, batch 8: the
# roundup page published fine, but nothing ever generated its 6 cards'
# actual recipes).
_CATEGORY_ROUNDUP_HEADER_RE = re.compile(
    r'"slug":\s*"([^"]+)",\s*\n\s*"template_type":\s*"category_roundup",\s*\n'
    r'\s*"title":\s*"(?:[^"\\]|\\.)*",\s*\n\s*"batch_number":\s*(\d+),'
)


def _category_roundup_slugs_for_batch(batch_number: int) -> list[str]:
    text = SEED_TEMPLATES_PATH.read_text()
    return [m.group(1) for m in _CATEGORY_ROUNDUP_HEADER_RE.finditer(text) if int(m.group(2)) == batch_number]


def _write_queue_csv(path: Path, rows: list[dict]) -> None:
    """The one place CONTENT_QUEUE.csv (or a subset of it) ever gets
    written -- csv.DictWriter defaults to '\\r\\n' line endings per the
    CSV spec, but this repo's CONTENT_QUEUE.csv has always used plain
    '\\n'. Writing the default back once turned a 100-row change into a
    12,619-row diff (every single line "changed" purely on line-ending
    bytes) and the resulting confusing "0 new pages" commit -- a real
    bug hit on this pipeline's very first live run. Explicit
    lineterminator keeps a real 100-row change looking like one."""
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=QUEUE_FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _next_batch_number() -> int:
    """One higher than the highest batch_number already in SEED_PAGES.
    Regex-parsed directly rather than importing seed_templates.py, which
    would pull in the whole backend package (and its import-time guard
    checks) for a single number -- extract_existing_pages() in
    build_batch_requests.py already established this same
    parse-don't-import approach for this file."""
    numbers = [int(m) for m in re.findall(r'"batch_number":\s*(\d+)', SEED_TEMPLATES_PATH.read_text())]
    return (max(numbers) + 1) if numbers else 1


def select_next_batch(count: int) -> tuple[Path, int, list[dict]]:
    """Claims the next `count` not_started rows from CONTENT_QUEUE.csv --
    marks them 'claimed' and writes the CSV back immediately, before
    anything else in this run, so two overlapping runs (a retried Action,
    a manual re-run while a scheduled one is still going) can never
    select the same rows twice. Writes a subset CSV under output/ with
    batch_number overwritten to the new batch number on every row --
    integrate_batch_results.py reads batch_number straight from each CSV
    row, so this is what actually makes new pages land under the right
    batch_number rather than whatever placeholder value the row carried
    in the master queue."""
    with QUEUE_PATH.open(newline="") as f:
        rows = list(csv.DictReader(f))

    batch_number = _next_batch_number()
    selected: list[dict] = []
    for row in rows:
        if len(selected) >= count:
            break
        if row["status"] == "not_started":
            row["status"] = "claimed"
            row["batch_number"] = str(batch_number)
            selected.append(row)  # same dict object as in `rows` -- mutations above apply to both

    if not selected:
        raise RuntimeError("No not_started rows left in CONTENT_QUEUE.csv")

    _write_queue_csv(QUEUE_PATH, rows)

    OUTPUT_DIR.mkdir(exist_ok=True)
    subset_path = OUTPUT_DIR / f"daily_batch_{batch_number}.csv"
    _write_queue_csv(subset_path, selected)

    print(f"Claimed {len(selected)} rows for batch {batch_number} -> {subset_path}")
    return subset_path, batch_number, selected


def run_generation(subset_csv: Path) -> Path:
    """Runs the two existing pipeline stages as subprocesses rather than
    importing and calling their main()s directly -- neither script is
    written to be imported (both read sys.argv and call sys.exit() on
    error), and shelling out here draws the same boundary main.py's own
    admin endpoints already keep around one-off scripts."""
    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "build_batch_requests.py"), str(subset_csv)],
        check=True, cwd=str(REPO_ROOT),
    )
    requests_path = OUTPUT_DIR / f"{subset_csv.stem}_requests.jsonl"
    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "submit_realtime_fallback.py"), str(requests_path), "--concurrency", "10"],
        check=True, cwd=str(REPO_ROOT), env=os.environ.copy(),
    )
    return OUTPUT_DIR / f"{subset_csv.stem}_results.jsonl"


# Mirrors seed_templates.py's own _TITLE_DEDUP_STOPWORDS/_stem_for_dedup/
# _normalize_title_for_dedup exactly (see that module's docstrings for the
# 2026-09-19 audit that found 108 confirmed duplicate-topic clusters, most
# missed by the original narrow version of this list, plus the two false
# positives -- crispy-burger/burgers, fresh-cherry-pie/cherry-pie -- that
# ruled "crispy"/"fresh" out as safe stopwords) -- see
# _existing_normalized_titles' docstring for why this needs its own copy
# here rather than importing seed_templates.py.
_TITLE_DEDUP_STOPWORDS = {
    "a", "an", "the", "of", "to", "for", "how", "what", "s", "vs", "versus",
    "and", "or", "in", "on", "at", "with", "difference",
    "classic", "homemade", "traditional", "authentic", "basic", "easy",
    "simple", "quick", "best", "whole", "style",
    "make", "making", "made", "cook", "cooking", "cooked",
    "still", "good", "delicious", "perfect", "ultimate",
}
_EXISTING_TITLE_RE = re.compile(r'"template_type":\s*"([^"]+)",\s*\n\s*"title":\s*"([^"]*)"')


def _stem_for_dedup(word: str) -> str:
    if len(word) > 4 and word.endswith("es") and not word.endswith(("ss", "us")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _normalize_title_for_dedup(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    words = [_stem_for_dedup(w) for w in words if w not in _TITLE_DEDUP_STOPWORDS]
    return " ".join(sorted(words))


def _existing_normalized_titles() -> dict[tuple[str, str], str]:
    """(template_type, normalized-word-bag) -> one real existing title that
    produced it, for every page already in seed_templates.py. A second,
    independent regex pass over the same file rather than importing
    seed_templates.py's own _normalize_title_for_dedup -- importing would
    pull in the whole backend package, the same reason
    extract_existing_pages() in build_batch_requests.py already
    regex-parses instead. Exists so validate_results (below) can catch a
    fresh title colliding with EXISTING published content -- the actual
    failure hit on this pipeline's first live run: a newly generated
    "jelly vs jam" collided with an already-published "jam-vs-jelly", not
    caught until local_verify()'s import-time guard, which crashed the
    whole batch (all 4 other, genuinely clean pages included) instead of
    just skipping the one offending title the way every other validation
    failure already does."""
    seen: dict[tuple[str, str], str] = {}
    for template_type, title in _EXISTING_TITLE_RE.findall(SEED_TEMPLATES_PATH.read_text()):
        seen[(template_type, _normalize_title_for_dedup(title))] = title
    return seen


def validate_results(subset_csv: Path, results_path: Path, id_to_row: dict) -> tuple[list[str], list[str]]:
    """The same validation validate_batch_results.py's main() runs
    (schema, type, depth-check, and title-convention checks via
    validate_content()) -- called directly here instead of shelling out
    to that script, since this needs the actual clean/bad custom_id lists
    back as data to drive integration and CONTENT_QUEUE.csv's status
    update, not a printed report a human would otherwise read and act on
    by hand. Also checks each candidate's title against both existing
    published content and every other title already accepted in this same
    batch (see _existing_normalized_titles) -- the same duplicate-title
    collision seed_templates.py's own import-time guard checks, just
    applied per-candidate here so one bad title is skipped like any other
    validation failure instead of surfacing only at local_verify() and
    taking the whole batch down with it. Returns (clean_ids, bad_ids)."""
    existing_slugs, collections, techniques, hubs = extract_existing_pages()
    collection_slugs = {c["slug"] for c in collections}
    technique_slugs = {t["slug"] for t in techniques}
    hub_slugs = {h["slug"] for h in hubs}
    existing_titles = _existing_normalized_titles()
    batch_titles: dict[tuple[str, str], str] = {}

    with results_path.open() as f:
        results = [json.loads(line) for line in f]

    clean_ids: list[str] = []
    bad_ids: list[str] = []
    for r in results:
        custom_id = r["custom_id"]
        if r["result"]["type"] != "succeeded":
            print(f"  [{custom_id}] request-level error: {r['result']}")
            bad_ids.append(custom_id)
            continue
        row = id_to_row.get(custom_id)
        if row is None:
            print(f"  [{custom_id}] no matching CSV row -- treating as bad")
            bad_ids.append(custom_id)
            continue
        try:
            content = extract_content(r["result"]["message"])
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  [{custom_id}] couldn't extract content: {e}")
            bad_ids.append(custom_id)
            continue
        issues = validate_content(custom_id, row["template_type"], content, collection_slugs, technique_slugs, hub_slugs)

        if not issues:
            new_title = content.get("title") or ""
            key = (row["template_type"], _normalize_title_for_dedup(new_title))
            dupe_of = existing_titles.get(key) or batch_titles.get(key)
            if dupe_of:
                issues = [f"[{custom_id}] title {new_title!r} duplicates {dupe_of!r} (same template_type, same normalized words)"]
            else:
                batch_titles[key] = new_title

        if issues:
            for issue in issues:
                print(f"  {issue}")
            bad_ids.append(custom_id)
        else:
            clean_ids.append(custom_id)

    print(f"Validation: {len(clean_ids)} clean, {len(bad_ids)} bad (of {len(results)} total)")
    return clean_ids, bad_ids


def run_integration(subset_csv: Path, results_path: Path, bad_ids: list[str]) -> None:
    args = [sys.executable, str(SCRIPTS_DIR / "integrate_batch_results.py"), str(subset_csv), str(results_path)]
    if bad_ids:
        args += ["--skip", *bad_ids]
    subprocess.run(args, check=True, cwd=str(REPO_ROOT))


# Real incident (2026-09-14): a companion recipe generated for beets-recipes'
# "Quick Pickled Beets" card duplicated the already-published "Pickled Beets
# Recipe" (pickled-beets) -- same dish, different wording, so the strict
# word-bag-equality dedup guard used elsewhere (_TITLE_DEDUP_STOPWORDS,
# matching seed_templates.py's own import-time check) correctly did NOT
# flag it as an exact duplicate, but it very much was one. A qualifier word
# ("quick") plus "Recipe" was the entire difference between the two titles.
# Stripped here on top of the normal stopwords, specifically for this
# generation-time "does a matching recipe already exist" check -- not
# folded into _TITLE_DEDUP_STOPWORDS itself, which guards every template
# type site-wide and needs to stay conservative (stripping "classic" or
# "homemade" globally would risk collapsing two genuinely different
# comparison/definition pages that happen to share a qualifier word).
_NEAR_DUP_QUALIFIERS = {
    "quick", "easy", "simple", "classic", "homemade", "best", "perfect",
    "traditional", "authentic", "ultimate", "basic", "real", "recipe",
}


def _normalize_for_near_dup(title: str) -> frozenset[str]:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return frozenset(w for w in words if w not in _TITLE_DEDUP_STOPWORDS and w not in _NEAR_DUP_QUALIFIERS)


def _published_recipe_titles_and_slugs() -> list[tuple[str, str]]:
    """(title, slug) for every PUBLISHED recipe_or_dish page -- unlike
    _existing_normalized_titles (which intentionally includes unpublished
    pages too, since a taken slug/title stays taken either way), a card
    linked by run_companion_recipes below has to resolve to a real, live
    page: main.py's own /pages/{slug} 404s outright on an
    unpublished one (see its own comment -- indistinguishable from a slug
    that was never seeded), so linking a card to one would just trade an
    unclickable card for a clickable-but-broken one."""
    text = SEED_TEMPLATES_PATH.read_text()
    matches = list(_PAGE_HEADER_RE.finditer(text))
    # _PAGE_HEADER_RE matches every template_type, not just recipe_or_dish --
    # re-derive template_type per match to filter, same source text so the
    # block boundaries below (next match's start, or EOF) line up correctly
    # regardless of what's interleaved between recipe_or_dish pages.
    type_re = re.compile(r'"template_type":\s*"([^"]+)"')
    published: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        block_start = m.end()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        header_and_block = text[m.start():block_end]
        type_m = type_re.search(header_and_block)
        if not type_m or type_m.group(1) != "recipe_or_dish":
            continue
        block = text[block_start:block_end]
        if '"unpublished": True' in block:
            continue
        title_m = re.search(r'"title":\s*"((?:[^"\\]|\\.)*)"', header_and_block)
        if title_m:
            published.append((title_m.group(1), m.group(1)))
    return published


def _link_cards_to_existing_recipes(collection_slugs: list[str]) -> None:
    """For every still-unlinked card on each collection, checks whether a
    published recipe_or_dish page already covers essentially the same dish
    (see _normalize_for_near_dup) and, if so, hand-sets that card's slug
    directly to the existing page rather than letting a companion recipe
    get generated for it -- the fix for the real duplicate this run once
    produced (see the module comment above _NEAR_DUP_QUALIFIERS). Mutates
    seed_templates.py in place; run_companion_recipes' later call to
    generate_companion_recipes.py re-scans the file itself and naturally
    skips any card this already linked (find_unlinked_cards only matches
    a literal `"slug": None`)."""
    published = _published_recipe_titles_and_slugs()
    by_norm: dict[frozenset[str], tuple[str, str]] = {}
    for title, slug in published:
        by_norm.setdefault(_normalize_for_near_dup(title), (title, slug))

    for collection_slug in collection_slugs:
        _, cards = find_unlinked_cards(collection_slug)
        for card in cards:
            match = by_norm.get(_normalize_for_near_dup(card["title"]))
            if match is None:
                continue
            existing_title, existing_slug = match
            text = SEED_TEMPLATES_PATH.read_text()
            old = f'"title": "{card["title"]}",\n                    "slug": None,'
            new = f'"title": "{card["title"]}",\n                    "slug": "{existing_slug}",'
            if old not in text:
                print(f"  WARNING: expected unlinked-card text not found for "
                      f"{card['title']!r} on {collection_slug!r} -- skipping the link, "
                      f"leaving it for generation instead")
                continue
            SEED_TEMPLATES_PATH.write_text(text.replace(old, new, 1))
            print(f"  {collection_slug!r}: linked card {card['title']!r} directly to "
                  f"existing {existing_slug!r} ({existing_title!r}) instead of generating a duplicate")


def run_companion_recipes(collection_slugs: list[str], batch_number: int) -> int:
    """For every category_roundup page in `collection_slugs`, generates
    real recipe_or_dish pages for its still-unlinked recipe_cards (see
    generate_companion_recipes.py's own docstring for how a card becomes
    clickable once its matching recipe exists) and integrates them under
    the SAME batch_number as their parent collection -- so a reviewer sees
    the collection and its recipes together in one review-queue batch, and
    approving that batch for prod promotes both in the same click, rather
    than a collection going live with clickless cards and its recipes
    trickling in separately. No-ops (returns 0) if `collection_slugs` is
    empty, the normal case for the vast majority of batches, which don't
    include a category_roundup row at all.

    Reuses validate_results() as-is for the schema/depth/duplicate-title
    checks -- its `subset_csv` param is never read in the function body,
    only `results_path` and `id_to_row`, so a companion results file (no
    CSV row behind it at all) fits without any change there.

    Before generating anything, links any card that already matches a
    published recipe directly to it instead (see
    _link_cards_to_existing_recipes) -- the fix for the real duplicate
    this once produced (beets-recipes' "Quick Pickled Beets" card got its
    own new page generated despite pickled-beets, "Pickled Beets Recipe",
    already covering the same dish)."""
    if not collection_slugs:
        return 0

    _link_cards_to_existing_recipes(collection_slugs)

    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "generate_companion_recipes.py"), *collection_slugs],
        check=True, cwd=str(REPO_ROOT), env=os.environ.copy(),
    )

    total_integrated = 0
    for slug in collection_slugs:
        results_path = OUTPUT_DIR / f"companion_{slug}.jsonl"
        if not results_path.exists():
            print(f"  {slug}: generate_companion_recipes.py wrote no output file -- skipping")
            continue
        with results_path.open() as f:
            results = [json.loads(line) for line in f]
        if not results:
            print(f"  {slug}: 0 unlinked cards, nothing to generate")
            continue

        id_to_row = {r["custom_id"]: {"template_type": "recipe_or_dish"} for r in results}
        clean_ids, bad_ids = validate_results(results_path, results_path, id_to_row)
        if not clean_ids:
            print(f"  {slug}: all {len(bad_ids)} companion recipe(s) failed validation -- nothing integrated")
            continue

        args = [
            sys.executable, str(SCRIPTS_DIR / "integrate_batch_results.py"),
            "--template-type", "recipe_or_dish", "--batch-number", str(batch_number),
            str(results_path),
        ]
        if bad_ids:
            args += ["--skip", *bad_ids]
        subprocess.run(args, check=True, cwd=str(REPO_ROOT))
        total_integrated += len(clean_ids)

    return total_integrated


def finalize_queue_status(selected: list[dict], id_to_row: dict, clean_ids: list[str], bad_ids: list[str]) -> None:
    """Rewrites CONTENT_QUEUE.csv one more time: clean/integrated rows go
    to 'published' (the CSV's own existing status vocabulary), bad/
    skipped rows go back to 'not_started' so they're eligible again on a
    future run instead of sitting 'claimed' forever. Matched by title --
    the join key this whole pipeline already uses throughout, since
    there's no id shared between a raw CSV row and its generated result
    other than the custom_id derived from that title at request-build
    time."""
    with QUEUE_PATH.open(newline="") as f:
        all_rows = list(csv.DictReader(f))

    clean_titles = {id_to_row[cid]["title"] for cid in clean_ids if cid in id_to_row}
    bad_titles = {id_to_row[cid]["title"] for cid in bad_ids if cid in id_to_row}
    selected_titles = {row["title"] for row in selected}

    for row in all_rows:
        if row["title"] not in selected_titles:
            continue
        if row["title"] in clean_titles:
            row["status"] = "published"
        elif row["title"] in bad_titles:
            row["status"] = "not_started"
        # else left 'claimed' -- shouldn't happen (every selected row's
        # custom_id should land in exactly one of clean_ids/bad_ids), but
        # a visible, investigable state beats silently guessing either way.

    _write_queue_csv(QUEUE_PATH, all_rows)


def local_verify() -> None:
    """The same verification done by hand for every content commit this
    whole project: a syntax check, then a real seed()/resync_content()
    round trip against a throwaway sqlite DB (importing app.models before
    Base.metadata.create_all is required or the table silently doesn't
    exist -- a real gotcha hit earlier this session). Raises on any
    failure, which aborts the run before anything gets pushed -- a broken
    insertion needs to fail here, not surface as a crash on the next real
    deploy."""
    ast.parse(SEED_TEMPLATES_PATH.read_text())

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "verify.db"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path}"
        env["ADMIN_TASK_TOKEN"] = "verify"
        script = (
            "from app import models\n"
            "from app.database import Base, engine, SessionLocal\n"
            "Base.metadata.create_all(bind=engine)\n"
            "from app.seed_templates import seed, resync_content\n"
            "db = SessionLocal()\n"
            "seed(db)\n"
            "resync_content(db)\n"
            "db.close()\n"
            "print('verify OK')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(REPO_ROOT / "backend"), env=env, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Local verification failed:\n{result.stdout}\n{result.stderr}")
        print(result.stdout.strip())


def git_commit_and_push(batch_number: int, new_page_count: int) -> None:
    """Commits seed_templates.py + CONTENT_QUEUE.csv to staging only --
    never main, see this module's own docstring -- and stamps the commit
    message with a "Tulo-Batch-Number: <N>" trailer, the exact convention
    merge-approved-batch.yml's cherry-pick lookup depends on to find this
    commit later (see that workflow's own comment: this repo's push
    credentials can create branches, not tag refs, so a trailer does the
    job a git tag would have)."""
    def run(*args: str) -> None:
        subprocess.run(args, cwd=str(REPO_ROOT), check=True)

    run("git", "config", "user.name", "tulo-content-bot")
    run("git", "config", "user.email", "content-bot@users.noreply.github.com")
    run("git", "add", str(SEED_TEMPLATES_PATH), str(QUEUE_PATH))
    message = (
        f"Daily batch {batch_number}: {new_page_count} new pages\n\n"
        f"Generated by content/scripts/daily_batch.py, staging only -- see "
        f"/admin/review-queue for review before this goes to prod.\n\n"
        f"Tulo-Batch-Number: {batch_number}\n"
    )
    run("git", "commit", "-m", message)
    run("git", "push", "origin", "HEAD:staging")


def wait_for_deploy(sample_slug: str, timeout_seconds: int = 15 * 60) -> None:
    """Polls the staging backend for one of this batch's new pages to
    actually exist before anything tries to fetch images for it -- new
    content only becomes real once Render's next deploy runs
    resync_content() against it, which doesn't happen the instant this
    script pushes. Polling the real signal (the page existing) adapts to
    however long that deploy actually takes instead of guessing with a
    blind sleep."""
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            r = requests.get(f"{base}/pages/{sample_slug}", timeout=10)
            if r.status_code == 200:
                print(f"Staging has picked up the new batch (found {sample_slug}).")
                return
        except requests.RequestException:
            pass
        time.sleep(20)
    raise RuntimeError(f"Staging never picked up {sample_slug} within {timeout_seconds}s")



# Real, live incident (2026-09-14): the first-ever 100-slug batch (batch 8,
# Monday's post-canary run) sent every slug to /admin/fetch-images in one
# request. fetch_images() downloads and relevance-checks each image (real
# bytes, not just a URL check) with CONCURRENCY=6 workers sustained for the
# whole call -- fine for the 2- and 5-slug runs this pipeline had only ever
# done before, but sustaining that for 100 slugs in one long-lived request
# on the same process serving live site traffic exceeded staging's memory
# limit and forced a Render auto-restart (a real, confirmed 504 for
# whoever hit the site during the restart). Chunking bounds how much of
# the batch is ever mid-flight in a single request, and the pause between
# chunks gives the process a chance to actually give memory back rather
# than staying elevated for the whole 100-slug run.
_IMAGE_FETCH_CHUNK_SIZE = 20
_IMAGE_FETCH_CHUNK_PAUSE_SECONDS = 15


def fetch_images_for_batch(new_slugs: list[str]) -> tuple[int, int]:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    token = os.environ["ADMIN_TASK_TOKEN"]
    total_pages_updated = 0
    total_images_written = 0
    chunks = [
        new_slugs[i : i + _IMAGE_FETCH_CHUNK_SIZE]
        for i in range(0, len(new_slugs), _IMAGE_FETCH_CHUNK_SIZE)
    ]
    for i, chunk in enumerate(chunks):
        r = requests.get(
            f"{base}/admin/fetch-images",
            params={"token": token, "slugs": ",".join(chunk)},
            timeout=1800,
        )
        r.raise_for_status()
        result = r.json()
        total_pages_updated += result["pages_updated"]
        total_images_written += result["images_written"]
        print(
            f"Images (chunk {i + 1}/{len(chunks)}, {len(chunk)} slugs): "
            f"{result['pages_updated']} pages updated, {result['images_written']} images written."
        )
        if i < len(chunks) - 1:
            time.sleep(_IMAGE_FETCH_CHUNK_PAUSE_SECONDS)
    print(f"Images: {total_pages_updated} pages updated, {total_images_written} images written.")
    return total_pages_updated, total_images_written


def bake_batch_images(new_slugs: list[str], batch_number: int) -> int:
    """Bakes this batch's own just-fetched images (see fetch_images_for_batch,
    called right before this everywhere it's used) into seed_templates.py as
    literal data, then commits that under the SAME batch_number trailer --
    so a future "approve batch N for prod" cherry-picks this commit right
    alongside the batch's own content, with no changes needed in
    merge-approved-batch.yml at all.

    Closes a real gap found live (2026-09-14): batch 8 was approved and
    merged to main with none of its images baked in (see
    bake_images_from_staging.py's own docstring for why image_url never
    reaches git on its own). Production re-fetched every one of those
    images independently, blind to whatever staging's review queue had
    already confirmed was correct, producing visible mismatches (a
    collection thumbnail showing the wrong dish entirely). Baking
    automatically, right here, right after the fetch that populates the
    data this needs, means that gap can't recur for any future batch.
    Passing category_roundup slugs (if any are in new_slugs) is harmless --
    bake()/export-images already skip those gracefully, they have no
    page-level image_url of their own to export.

    Safe to no-op: if nothing actually changed (e.g. a re-run, or every
    slug already matched what was baked), no commit is made."""
    bake(os.environ["BACKEND_BASE_URL"], os.environ["ADMIN_TASK_TOKEN"], new_slugs)

    status = subprocess.run(
        ["git", "status", "--porcelain", str(SEED_TEMPLATES_PATH)],
        cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
    )
    if not status.stdout.strip():
        print("Bake: no changes (nothing to bake, or already up to date).")
        return 0

    def run(*args: str) -> None:
        subprocess.run(args, cwd=str(REPO_ROOT), check=True)

    run("git", "config", "user.name", "tulo-content-bot")
    run("git", "config", "user.email", "content-bot@users.noreply.github.com")
    run("git", "add", str(SEED_TEMPLATES_PATH))
    message = (
        f"Bake batch {batch_number}'s fetched images into seed_templates.py\n\n"
        f"image_url only ever lives in the runtime database until baked -- "
        f"see bake_images_from_staging.py's own docstring. Automatic as of "
        f"this run, so this batch's photos survive the merge to prod instead "
        f"of production re-fetching them blind.\n\n"
        f"Tulo-Batch-Number: {batch_number}\n"
    )
    run("git", "commit", "-m", message)
    run("git", "push", "origin", "HEAD:staging")
    print(f"Baked and committed batch {batch_number}'s images.")
    return 1


def write_job_summary(batch_number: int, page_count: int, images_written: int) -> None:
    """Writes the review-queue link and batch stats to GitHub Actions'
    own job summary (the GITHUB_STEP_SUMMARY file, rendered on the
    workflow run's page) -- this, plus GitHub's own workflow-run
    notification email, is what makes a separate Gmail notification
    optional rather than required: the notification says a run finished,
    and clicking into it lands directly on this summary with the actual
    link to click, one step further than a bespoke email but with zero
    extra credentials to set up. A no-op with a stdout note when not
    running inside GitHub Actions (GITHUB_STEP_SUMMARY unset), so this is
    always safe to call."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    base = os.environ.get("BACKEND_BASE_URL", "").rstrip("/")
    token = os.environ.get("ADMIN_TASK_TOKEN", "")
    review_url = f"{base}/admin/review-queue?token={token}&batch={batch_number}"

    summary = (
        f"## Batch {batch_number} ready for review\n\n"
        f"- **{page_count}** new pages\n"
        f"- **{images_written}** photos fetched\n\n"
        f"[Open the review queue]({review_url})\n\n"
        f"Flag anything wrong with an image and a fresh candidate photo fetches "
        f"automatically, or paste an exact photo URL directly on the card. Once "
        f"everything's approved, click **Approve batch {batch_number} for prod** "
        f"at the top of that page -- it merges within seconds.\n"
    )
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(summary)
    else:
        print(summary)


def send_notification_email(batch_number: int, page_count: int, images_written: int) -> None:
    """Gmail SMTP + an App Password, not the account's real password --
    Google requires an App Password for SMTP once 2-Step Verification is
    on, and it's independently revocable if it ever needs to be rotated.
    See this module's own docstring for the exact env vars and how to
    generate one (Google Account -> Security -> 2-Step Verification ->
    App passwords)."""
    user = os.environ["GMAIL_SMTP_USER"]
    app_password = os.environ["GMAIL_SMTP_APP_PASSWORD"]
    to_addr = os.environ.get("NOTIFY_EMAIL_TO", "ljtavgac@gmail.com")
    base = os.environ.get("BACKEND_BASE_URL", "").rstrip("/")
    token = os.environ.get("ADMIN_TASK_TOKEN", "")

    review_url = f"{base}/admin/review-queue?token={token}&batch={batch_number}"
    body = (
        f"Batch {batch_number} is ready for review: {page_count} new pages, "
        f"{images_written} photos fetched.\n\n"
        f"Review it here:\n{review_url}\n\n"
        f"Flag anything wrong with an image and a fresh candidate photo "
        f"fetches automatically -- or paste an exact photo URL directly on "
        f"the card if you already know the right one. Once everything's "
        f"approved, click \"Approve batch {batch_number} for prod\" at the "
        f"top of the page -- it merges to prod within seconds, no need to "
        f"reply here.\n"
    )
    msg = MIMEText(body)
    msg["Subject"] = f"Tulo: batch {batch_number} ready for review ({page_count} pages)"
    msg["From"] = user
    msg["To"] = to_addr

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(user, app_password)
        smtp.send_message(msg)
    print(f"Sent notification email to {to_addr}")


def run_companions_only(collection_slug: str) -> None:
    """One-off repair mode for a collection whose companion recipes never
    got generated (e.g. any batch pushed before run_companion_recipes()
    existed -- beets-recipes, batch 8, the live case this was built for).
    Not part of the normal daily flow; invoked via --companions-for.

    Finds the collection's own batch_number from its already-published
    seed_templates.py entry (not a freshly claimed one -- this collection
    is already live) and integrates its new companion recipes under that
    SAME batch_number, so they land in the review queue alongside the
    collection they belong to instead of a fresh batch of their own.

    Fetches images ONLY for the slugs this call actually adds, not
    _slugs_for_batch(batch_number)'s full membership -- that batch may
    already contain dozens of other, already-reviewed pages with real
    photos, and fetch_images() force-refetches every slug it's given
    explicitly (see fetch_stock_images.py's only_slugs), so passing the
    whole batch here would silently re-roll every one of those good
    photos for no reason."""
    if not os.environ.get("PIPELINE_ANTHROPIC_API_KEY"):
        raise RuntimeError("PIPELINE_ANTHROPIC_API_KEY is not set.")

    text = SEED_TEMPLATES_PATH.read_text()
    matches = {m.group(1): int(m.group(2)) for m in _CATEGORY_ROUNDUP_HEADER_RE.finditer(text)}
    if collection_slug not in matches:
        raise RuntimeError(f"{collection_slug!r} is not a category_roundup page (or not found) in seed_templates.py")
    batch_number = matches[collection_slug]

    print(f"Backfilling companion recipes for {collection_slug!r} (batch {batch_number})...")
    before = set(_slugs_for_batch(batch_number))
    added = run_companion_recipes([collection_slug], batch_number)
    if added == 0:
        print("Nothing to do -- 0 companion recipes generated/integrated.")
        return

    local_verify()
    git_commit_and_push(batch_number, added)

    after = set(_slugs_for_batch(batch_number))
    new_slugs = sorted(after - before)
    if not new_slugs:
        raise RuntimeError("run_companion_recipes reported pages added, but no new slugs found under this batch_number -- aborting before image fetch")

    wait_for_deploy(new_slugs[0])
    _, images_written = fetch_images_for_batch(new_slugs)
    bake_batch_images(new_slugs, batch_number)
    print(f"\nDone: {added} companion recipe(s) for {collection_slug!r}, {images_written} images.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--dry-run", action="store_true", help="Stop after local verification -- no push, fetch, or email.")
    parser.add_argument(
        "--companions-for", metavar="COLLECTION_SLUG",
        help="One-off repair: backfill companion recipes for an already-published category_roundup "
             "page whose cards never got them (see run_companions_only). Skips the normal batch flow "
             "entirely -- no CONTENT_QUEUE.csv rows are claimed.",
    )
    args = parser.parse_args()

    if args.companions_for:
        run_companions_only(args.companions_for)
        return

    # Fails fast, before claiming a single CONTENT_QUEUE.csv row, rather
    # than letting every one of `count` requests dial out and fail on a
    # missing/empty key -- a real thing that happened on this pipeline's
    # first live run (GitHub sets a referenced secret to an empty string,
    # not an absent env var, when it isn't configured yet).
    if not os.environ.get("PIPELINE_ANTHROPIC_API_KEY"):
        raise RuntimeError("PIPELINE_ANTHROPIC_API_KEY is not set -- nothing claimed, nothing generated.")

    subset_csv, batch_number, selected = select_next_batch(args.count)

    results_path = run_generation(subset_csv)
    manifest_path = OUTPUT_DIR / f"{subset_csv.stem}_manifest.json"
    id_to_row = load_id_to_row_from_manifest(subset_csv, manifest_path)
    clean_ids, bad_ids = validate_results(subset_csv, results_path, id_to_row)
    run_integration(subset_csv, results_path, bad_ids)
    finalize_queue_status(selected, id_to_row, clean_ids, bad_ids)

    # Any category_roundup page this run just published gets real recipes
    # generated for its still-unlinked cards, integrated under this SAME
    # batch_number -- see run_companion_recipes' own docstring. Before
    # local_verify() so a broken companion insertion fails the run here,
    # not on the next real deploy.
    roundup_slugs = _category_roundup_slugs_for_batch(batch_number)
    companions_added = 0
    if roundup_slugs:
        print(f"Batch {batch_number} includes {len(roundup_slugs)} category_roundup page(s) {roundup_slugs} "
              "-- generating companion recipes for their cards...")
        companions_added = run_companion_recipes(roundup_slugs, batch_number)
        print(f"Added {companions_added} companion recipe page(s).")

    local_verify()

    total_new_pages = len(clean_ids) + companions_added

    if args.dry_run:
        print(f"--dry-run: stopping here. {total_new_pages} pages would have been pushed as batch {batch_number}.")
        return

    if not clean_ids:
        # Nothing to push -- the CONTENT_QUEUE.csv claim/finalize above
        # never left this machine's disk (nothing was committed), so the
        # same rows are simply available again on the next run rather
        # than stuck 'claimed'. Still a real failure worth a loud, clear
        # message (every request in the batch failed validation, most
        # likely a bad API key or an API-side issue) rather than
        # continuing on to push an empty commit and then crash later at
        # the image-fetch step -- exactly what happened on this
        # pipeline's first live run.
        raise RuntimeError(
            f"All {len(bad_ids)} result(s) failed validation -- 0 clean pages, nothing pushed. "
            "Check PIPELINE_ANTHROPIC_API_KEY and the validation output above."
        )

    git_commit_and_push(batch_number, total_new_pages)

    new_slugs = _slugs_for_batch(batch_number)
    if not new_slugs:
        raise RuntimeError(f"No pages found under batch_number {batch_number} after integration -- aborting before image fetch/email")

    wait_for_deploy(new_slugs[0])
    _, images_written = fetch_images_for_batch(new_slugs)
    bake_batch_images(new_slugs, batch_number)

    write_job_summary(batch_number, total_new_pages, images_written)
    if os.environ.get("GMAIL_SMTP_USER") and os.environ.get("GMAIL_SMTP_APP_PASSWORD"):
        send_notification_email(batch_number, total_new_pages, images_written)
    else:
        print("GMAIL_SMTP_USER/GMAIL_SMTP_APP_PASSWORD not set -- skipping email, "
              "relying on GitHub's own workflow-run notification + the job summary above.")

    print(f"\nDone: batch {batch_number}, {total_new_pages} pages, {images_written} images.")


if __name__ == "__main__":
    main()
