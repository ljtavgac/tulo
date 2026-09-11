"""Fully automated daily content pipeline: selects the next N titles from
CONTENT_QUEUE.csv, generates + validates + integrates them into
seed_templates.py, pushes to staging, fetches images, and emails a "new
batch ready for review" notification. This is the whole loop
build_batch_requests.py / submit_realtime_fallback.py /
validate_batch_results.py / integrate_batch_results.py were each built to
handle one step of, by hand, during the pilot -- glued here into one
unattended run instead of a person stepping through each script in turn.

Usage:
    PIPELINE_ANTHROPIC_API_KEY=... \
    BACKEND_BASE_URL=https://your-staging-backend \
    ADMIN_TASK_TOKEN=... \
    GMAIL_SMTP_USER=you@gmail.com GMAIL_SMTP_APP_PASSWORD=... [NOTIFY_EMAIL_TO=...] \
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
    GMAIL_SMTP_APP_PASSWORD     A Gmail address and an App Password for it
                                (Google Account -> Security -> 2-Step
                                Verification -> App passwords -- a regular
                                account password won't work for SMTP once
                                2FA is on). Not needed with --dry-run.
    NOTIFY_EMAIL_TO             Defaults to ljtavgac@gmail.com if unset.

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
from build_batch_requests import extract_existing_pages, load_id_to_row_from_manifest  # noqa: E402
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

    with QUEUE_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=QUEUE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    OUTPUT_DIR.mkdir(exist_ok=True)
    subset_path = OUTPUT_DIR / f"daily_batch_{batch_number}.csv"
    with subset_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=QUEUE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(selected)

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


def validate_results(subset_csv: Path, results_path: Path, id_to_row: dict) -> tuple[list[str], list[str]]:
    """The same validation validate_batch_results.py's main() runs
    (schema, type, depth-check, and title-convention checks via
    validate_content()) -- called directly here instead of shelling out
    to that script, since this needs the actual clean/bad custom_id lists
    back as data to drive integration and CONTENT_QUEUE.csv's status
    update, not a printed report a human would otherwise read and act on
    by hand. Returns (clean_ids, bad_ids)."""
    existing_slugs, collections, techniques, hubs = extract_existing_pages()
    collection_slugs = {c["slug"] for c in collections}
    technique_slugs = {t["slug"] for t in techniques}
    hub_slugs = {h["slug"] for h in hubs}

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

    with QUEUE_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=QUEUE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)


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


def fetch_images_for_batch(new_slugs: list[str]) -> tuple[int, int]:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    token = os.environ["ADMIN_TASK_TOKEN"]
    r = requests.get(
        f"{base}/admin/fetch-images",
        params={"token": token, "slugs": ",".join(new_slugs)},
        timeout=1800,
    )
    r.raise_for_status()
    result = r.json()
    print(f"Images: {result['pages_updated']} pages updated, {result['images_written']} images written.")
    return result["pages_updated"], result["images_written"]


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--dry-run", action="store_true", help="Stop after local verification -- no push, fetch, or email.")
    args = parser.parse_args()

    subset_csv, batch_number, selected = select_next_batch(args.count)

    results_path = run_generation(subset_csv)
    manifest_path = OUTPUT_DIR / f"{subset_csv.stem}_manifest.json"
    id_to_row = load_id_to_row_from_manifest(subset_csv, manifest_path)
    clean_ids, bad_ids = validate_results(subset_csv, results_path, id_to_row)
    run_integration(subset_csv, results_path, bad_ids)
    finalize_queue_status(selected, id_to_row, clean_ids, bad_ids)
    local_verify()

    if args.dry_run:
        print(f"--dry-run: stopping here. {len(clean_ids)} pages would have been pushed as batch {batch_number}.")
        return

    git_commit_and_push(batch_number, len(clean_ids))

    new_slugs = _slugs_for_batch(batch_number)
    if not new_slugs:
        raise RuntimeError(f"No pages found under batch_number {batch_number} after integration -- aborting before image fetch/email")

    wait_for_deploy(new_slugs[0])
    _, images_written = fetch_images_for_batch(new_slugs)
    send_notification_email(batch_number, len(clean_ids), images_written)

    print(f"\nDone: batch {batch_number}, {len(clean_ids)} pages, {images_written} images.")


if __name__ == "__main__":
    main()
