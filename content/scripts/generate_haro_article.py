"""Generates one real Tulo page for a HARO content-opportunity outreach
prospect (status="article_requested") and pushes it to staging -- the
external step outreach_queue_create_article() in backend/app/main.py
can't do itself (no push credentials, and generation can run past a
request timeout). See OutreachProspect's status docstring in
backend/app/models.py for the full lifecycle this is one step of:
_draft_haro_replies flags a "content_opportunity" -> a human clicks
Create Article (status -> "article_requested") -> this script generates
the page, pushes it to staging, and calls
POST /admin/outreach-queue/link-article (status -> "article_pending_review")
-> once the page is live on prod (through the normal human content-review
step), outreach_queue()'s own _resolve_pending_articles drafts the real,
sendable reply and flips status -> "queued".

Usage:
    PIPELINE_ANTHROPIC_API_KEY=... \
    BACKEND_BASE_URL=https://your-staging-backend \
    ADMIN_TASK_TOKEN=... \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/generate_haro_article.py --prospect-id 123

Reuses the exact same generation/validation/integration building blocks
as content/scripts/daily_batch.py (build_request_params, the real-time
Messages API via submit_realtime_fallback.call_one,
validate_content/normalize_for_storage, format_page_entry) for a single
page instead of a batch of them -- see that module's own docstring for
why each piece exists and works the way it does.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import extract_existing_pages  # noqa: E402
from daily_batch import (  # noqa: E402
    _existing_normalized_titles,
    _next_batch_number,
    _normalize_title_for_dedup,
    fetch_images_for_batch,
    local_verify,
    wait_for_deploy,
)
from integrate_batch_results import format_page_entry, slugify_for_page  # noqa: E402
from prompt_templates import build_request_params  # noqa: E402
from submit_realtime_fallback import call_one  # noqa: E402
from validation import extract_content, normalize_for_storage, validate_content  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_TEMPLATES_PATH = REPO_ROOT / "backend" / "app" / "seed_templates.py"


def _outreach_auth() -> tuple[str, str]:
    return (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])


def _fetch_prospect(prospect_id: int) -> dict:
    """Reads the prospect via the outreach portal's own JSON listing
    rather than hitting the database directly -- this script has no DB
    credentials, only the same admin HTTP surface a human already uses."""
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    r = requests.get(
        f"{base}/admin/outreach-queue/list.json",
        params={"status": "article_requested"},
        auth=_outreach_auth(), timeout=30,
    )
    r.raise_for_status()
    matches = [row for row in r.json() if row["id"] == prospect_id]
    if not matches:
        raise RuntimeError(
            f"No status=article_requested prospect with id={prospect_id} found -- "
            "already generated, rejected, or Create Article was never clicked?"
        )
    prospect = matches[0]
    if not prospect.get("proposed_title") or not prospect.get("proposed_template_type"):
        raise RuntimeError(f"Prospect {prospect_id} is missing proposed_title/proposed_template_type")
    return prospect


def _link_article(prospect_id: int, slug: str) -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    r = requests.post(
        f"{base}/admin/outreach-queue/link-article",
        json={"prospect_id": prospect_id, "slug": slug},
        auth=_outreach_auth(), timeout=30,
    )
    r.raise_for_status()
    print(f"Linked prospect {prospect_id} -> slug {slug!r}: {r.json()}")


def _mark_failed(prospect_id: int, reason: str) -> None:
    """Reports a generation failure back to the portal so the row shows
    a reviewable "can't produce this" card instead of sitting at
    "article_requested" forever, indistinguishable from one still
    waiting on the next pipeline run -- see article_failed's own
    docstring on OutreachProspect. Best-effort: if even this call fails
    (network blip, backend down), the caller still re-raises the
    original error so the CI job shows red either way."""
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    try:
        r = requests.post(
            f"{base}/admin/outreach-queue/mark-article-failed",
            json={"prospect_id": prospect_id, "reason": reason},
            auth=_outreach_auth(), timeout=30,
        )
        r.raise_for_status()
        print(f"Marked prospect {prospect_id} as article_failed: {reason}")
    except Exception as e:  # noqa: BLE001 -- never let this mask the real failure below
        print(f"  (also failed to report article_failed status for prospect {prospect_id}: {e})")


def git_commit_and_push(slug: str, prospect_id: int, batch_number: int) -> None:
    """Staging only, same convention as daily_batch.py's own
    git_commit_and_push -- never main; promotion to prod is still the
    normal human content-review step. Does stamp a Tulo-Batch-Number
    trailer (a real, confirmed miss in an earlier version of this
    function, which assumed nothing downstream looked for one on a
    HARO-generated page -- wrong: merge-approved-batch.yml's cherry-pick
    step looks up a batch's commit by this trailer unconditionally,
    daily-batch or not, and a HARO article's own "Approve for prod"
    click in the outreach portal dispatches that exact workflow. Without
    it, that workflow fails outright with "No commit on staging carries
    Tulo-Batch-Number: <N>" and the approval silently goes nowhere)."""
    def run(*args: str) -> None:
        subprocess.run(args, cwd=str(REPO_ROOT), check=True)

    run("git", "config", "user.name", "tulo-content-bot")
    run("git", "config", "user.email", "content-bot@users.noreply.github.com")
    run("git", "add", str(SEED_TEMPLATES_PATH))
    message = (
        f"HARO content opportunity: add {slug}\n\n"
        f"Generated by content/scripts/generate_haro_article.py for outreach "
        f"prospect #{prospect_id} -- staging only, still needs the normal "
        f"human content review before it's live on prod.\n\n"
        f"Tulo-Batch-Number: {batch_number}\n"
    )
    run("git", "commit", "-m", message)
    run("git", "push", "origin", "HEAD:staging")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prospect-id", type=int, required=True)
    args = parser.parse_args()

    # Fails fast, before making a real API call, same reasoning as
    # daily_batch.py's own equivalent check.
    if not os.environ.get("PIPELINE_ANTHROPIC_API_KEY"):
        raise RuntimeError("PIPELINE_ANTHROPIC_API_KEY is not set -- nothing generated.")

    prospect = _fetch_prospect(args.prospect_id)
    template_type = prospect["proposed_template_type"]
    proposed_title = prospect["proposed_title"]
    print(f"Generating a {template_type!r} page for prospect #{args.prospect_id}: {proposed_title!r}")

    try:
        _generate_and_publish(args.prospect_id, template_type, proposed_title, prospect)
    except Exception as e:
        _mark_failed(args.prospect_id, f"{type(e).__name__}: {e}")
        raise


def _generate_and_publish(prospect_id: int, template_type: str, proposed_title: str, prospect: dict) -> None:
    existing_slugs, collections, techniques, hubs = extract_existing_pages()

    # Real, reported gap (2026-09-19 duplicate-content audit): unlike
    # daily_batch.py's validate_results, this script had NO title-dedup
    # check at all before daily_batch.py's own import-time
    # _check_no_duplicate_titles guard (triggered later, inside
    # local_verify()) -- meaning a duplicate proposal here paid for a full
    # real generation API call before ever being caught, only to fail the
    # whole run at local_verify() with nothing to show for it. Checking
    # the *proposed* title against every currently-published title (same
    # normalization the guard itself uses, so this can never be stricter
    # or looser than what would actually get caught downstream) up front
    # catches the common case for free, before spending anything on
    # generation.
    existing_titles = _existing_normalized_titles()
    proposed_key = (template_type, _normalize_title_for_dedup(proposed_title))
    if proposed_key in existing_titles:
        raise ValueError(
            f"Proposed title {proposed_title!r} duplicates existing page "
            f"{existing_titles[proposed_key]!r} (same template_type, same "
            f"normalized words) -- not generating."
        )

    # A synthetic CONTENT_QUEUE.csv-shaped row -- build_request_params only
    # ever reads title/template_type/category/page_purpose off it (see its
    # own docstring), all of which this prospect already carries.
    row = {
        "template_type": template_type,
        "title": proposed_title,
        "category": None,
        "page_purpose": prospect.get("source_query") or "",
    }
    params = build_request_params(row, collections, techniques)
    entry = {"custom_id": f"haro-prospect-{prospect_id}", "params": params}

    # Unlike daily_batch.py's own validate_results (which tolerates a bad
    # result by just skipping that one item out of a whole batch), this
    # script generates exactly one page -- so a single malformed/truncated
    # attempt (call_one itself only retries on request-level errors, not
    # on a 200 response with bad JSON content) would kill the entire run
    # for nothing. Retries the full generation call a few times before
    # giving up for real.
    MAX_GENERATION_ATTEMPTS = 3
    content = None
    issues: list[str] = []
    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        result = call_one(entry, os.environ["PIPELINE_ANTHROPIC_API_KEY"])
        if result["result"]["type"] != "succeeded":
            print(f"  attempt {attempt}/{MAX_GENERATION_ATTEMPTS}: generation failed: {result['result']}")
            continue
        try:
            candidate = extract_content(result["result"]["message"])
        except ValueError as e:
            print(f"  attempt {attempt}/{MAX_GENERATION_ATTEMPTS}: couldn't extract content: {e}")
            continue
        issues = validate_content(
            entry["custom_id"], template_type, candidate,
            {c["slug"] for c in collections}, {t["slug"] for t in techniques}, {h["slug"] for h in hubs},
        )
        # The model's own generated title can differ from proposed_title
        # (already checked above) -- re-checking the actual title the
        # model returned is the authoritative check, since that's what
        # would actually get published. Treated as one more validation
        # issue so a colliding attempt retries like any other bad
        # generation, rather than as a separate failure path.
        candidate_title = candidate.get("title") or ""
        candidate_key = (template_type, _normalize_title_for_dedup(candidate_title))
        if candidate_key in existing_titles:
            issues = list(issues) + [
                f"[{entry['custom_id']}] generated title {candidate_title!r} duplicates existing page "
                f"{existing_titles[candidate_key]!r} (same template_type, same normalized words)"
            ]
        if issues:
            print(f"  attempt {attempt}/{MAX_GENERATION_ATTEMPTS}: validation issues:\n" + "\n".join(issues))
            continue
        content = candidate
        break

    if content is None:
        raise RuntimeError(f"Generation failed after {MAX_GENERATION_ATTEMPTS} attempts. Last issues:\n" + "\n".join(issues))

    content = normalize_for_storage(template_type, content)
    generated_title = content.pop("title")
    slug = slugify_for_page(generated_title, template_type)
    base_slug = slug
    n = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{n}"
        n += 1

    batch_number = _next_batch_number()
    entry_text = format_page_entry(slug, template_type, generated_title, batch_number, content)

    text = SEED_TEMPLATES_PATH.read_text()
    # Same insertion anchor integrate_batch_results.py uses -- see that
    # module's own comment for why a naive "]\n" search is wrong here.
    anchor = "\n]\n\n\ndef _find_double_dashes"
    if anchor not in text:
        raise ValueError("Expected SEED_PAGES closing-bracket anchor not found -- file structure changed")
    closing_bracket = text.index(anchor) + 1
    header = (
        f"\n    # --- HARO content opportunity (outreach prospect #{prospect_id}), generated via\n"
        "    # content/scripts/generate_haro_article.py.\n"
    )
    new_text = text[:closing_bracket] + header + entry_text + text[closing_bracket:]
    SEED_TEMPLATES_PATH.write_text(new_text)
    print(f"Inserted {slug!r} (batch_number {batch_number}) into {SEED_TEMPLATES_PATH}")

    local_verify()

    git_commit_and_push(slug, prospect_id, batch_number)

    wait_for_deploy(slug)
    fetch_images_for_batch([slug])

    _link_article(prospect_id, slug)

    print(f"\nDone: prospect #{prospect_id} -> {slug} (pushed to staging), pending human content review.")


if __name__ == "__main__":
    main()
