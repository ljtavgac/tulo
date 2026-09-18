"""Removes one HARO-generated page from staging's seed_templates.py -- the
external step outreach_queue_reject_article_content() in
backend/app/main.py can't do itself (no git push credentials). See
OutreachProspect's content_removal_requested/content_removed docstring in
backend/app/models.py for the full lifecycle: a human clicks Reject
Content on a card with a real target_slug (status="article_pending_review"
or "queued" alike -- this is independent of the reply/email decision) ->
content_removal_requested is set -> this script removes the page and
pushes -> calls POST /admin/outreach-queue/confirm-article-removed
(content_removed is set).

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/reject_haro_article.py --prospect-id 123
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from daily_batch import local_verify  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_TEMPLATES_PATH = REPO_ROOT / "backend" / "app" / "seed_templates.py"


def _outreach_auth() -> tuple[str, str]:
    return (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])


def _fetch_prospect(prospect_id: int) -> dict:
    """Reads the prospect via the outreach portal's own JSON listing,
    same reasoning as generate_haro_article.py's own _fetch_prospect --
    this script has no DB credentials, only the same admin HTTP surface a
    human already uses. status=all since a removal-pending prospect's own
    reply/email status is independent (could be queued, approved, or
    rejected) -- content_removal_requested is what actually matters here."""
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    r = requests.get(
        f"{base}/admin/outreach-queue/list.json",
        params={"status": "all"},
        auth=_outreach_auth(), timeout=30,
    )
    r.raise_for_status()
    matches = [row for row in r.json() if row["id"] == prospect_id]
    if not matches:
        raise RuntimeError(f"No prospect with id={prospect_id} found")
    prospect = matches[0]
    if not prospect.get("content_removal_requested"):
        raise RuntimeError(f"Prospect {prospect_id} has no pending content_removal_requested -- nothing to do")
    if prospect.get("content_removed"):
        raise RuntimeError(f"Prospect {prospect_id}'s content was already removed")
    if not prospect.get("target_slug"):
        raise RuntimeError(f"Prospect {prospect_id} has no target_slug -- nothing to remove")
    return prospect


def _confirm_removed(prospect_id: int) -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    r = requests.post(
        f"{base}/admin/outreach-queue/confirm-article-removed",
        json={"prospect_id": prospect_id},
        auth=_outreach_auth(), timeout=30,
    )
    r.raise_for_status()
    print(f"Confirmed removal for prospect {prospect_id}: {r.json()}")


def remove_page_entry(text: str, slug: str) -> str:
    """Removes one page's whole dict entry from SEED_PAGES, matched by
    slug -- the exact inverse of integrate_batch_results.py's own
    insertion. Splits on the same top-level-entry boundary
    patch_definition_comparison_links.py already established
    (`(?=    \\{\\n        "slug")`) rather than a line-range slice, so
    this is immune to exactly where in the list the entry happens to sit
    or how many lines its content spans."""
    entry_pattern = re.compile(r'(?=    \{\n        "slug")')
    parts = entry_pattern.split(text)
    header, entries = parts[0], parts[1:]

    matching = [e for e in entries if re.search(rf'"slug": "{re.escape(slug)}"', e)]
    if not matching:
        raise ValueError(f"No SEED_PAGES entry found for slug {slug!r} -- already removed, or never pushed?")
    if len(matching) > 1:
        raise ValueError(f"Multiple SEED_PAGES entries found for slug {slug!r} -- refusing to guess which one")

    remaining = [e for e in entries if e not in matching]
    return header + "".join(remaining)


def git_commit_and_push(slug: str, prospect_id: int) -> None:
    """Staging only -- the page was only ever pushed to staging (see
    generate_haro_article.py), never main, so there's nothing to remove
    from main either."""
    def run(*args: str) -> None:
        subprocess.run(args, cwd=str(REPO_ROOT), check=True)

    run("git", "config", "user.name", "tulo-content-bot")
    run("git", "config", "user.email", "content-bot@users.noreply.github.com")
    run("git", "add", str(SEED_TEMPLATES_PATH))
    message = (
        f"HARO content opportunity: remove {slug}\n\n"
        f"Rejected via the outreach portal's Reject Content action for "
        f"prospect #{prospect_id} -- staging only.\n"
    )
    run("git", "commit", "-m", message)
    run("git", "push", "origin", "HEAD:staging")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prospect-id", type=int, required=True)
    args = parser.parse_args()

    prospect = _fetch_prospect(args.prospect_id)
    slug = prospect["target_slug"]
    print(f"Removing {slug!r} (prospect #{args.prospect_id}) from {SEED_TEMPLATES_PATH}")

    text = SEED_TEMPLATES_PATH.read_text()
    new_text = remove_page_entry(text, slug)

    # Sanity check before writing anything to disk: exactly one fewer
    # top-level page, no more, no less -- same discipline
    # integrate_batch_results.py's own insertion check uses in reverse.
    top_level_pattern = re.compile(r'"slug":\s*"[^"]+",\s*\n\s*"template_type":')
    before_count = len(top_level_pattern.findall(text))
    after_count = len(top_level_pattern.findall(new_text))
    if before_count - after_count != 1:
        raise ValueError(
            f"Sanity check failed: expected exactly 1 fewer page, but top-level page count "
            f"went from {before_count} to {after_count}. Not writing -- investigate before re-running."
        )

    SEED_TEMPLATES_PATH.write_text(new_text)
    ast.parse(new_text)
    print(f"Removed {slug!r} ({before_count} -> {after_count} total pages)")

    local_verify()

    git_commit_and_push(slug, args.prospect_id)

    _confirm_removed(args.prospect_id)

    print(f"\nDone: prospect #{args.prospect_id} -> {slug} removed from staging.")


if __name__ == "__main__":
    main()
