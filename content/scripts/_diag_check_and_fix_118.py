"""Throwaway: investigates why "How to Steam Milk for a Latte" (outreach
prospect #118) is stuck showing status=article_requested in the portal
even though its page (slug how-to-steam-milk-for-a-latte) was already
committed to staging's seed_templates.py -- generate_haro_article.py's
git_commit_and_push step must have succeeded, but wait_for_deploy/
fetch_images_for_batch or the final link-article call never completed
(no image_url on the entry, and the prospect row was never linked or
marked failed -- likely the CI job got killed/timed out mid-run rather
than raising a normal exception, since main()'s except block would
otherwise have called mark-article-failed).

Checks prospect #118's live status, and if it's genuinely stuck at
article_requested with no target_slug, calls link-article for the
already-existing slug directly (no regeneration, no duplicate page) so
the row moves into article_pending_review where the normal image
review can happen -- the review UI will then show the page has no
image yet, same as any page whose image needs a fetch/retry via the
existing "flag + re-fetch" review action.

Deleted after use."""

from __future__ import annotations

import os

import requests

TITLE = "How to Steam Milk for a Latte"
SLUG = "how-to-steam-milk-for-a-latte"


def _auth() -> tuple[str, str]:
    return (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=_auth(), timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    row = next((row for row in rows if row.get("proposed_title") == TITLE), None)
    if not row:
        print(f"No prospect found with proposed_title={TITLE!r}")
        return
    prospect_id = row["id"]
    print(f"id={prospect_id}: status={row['status']!r} target_slug={row.get('target_slug')!r}")

    if row["status"] != "article_requested":
        print("Not stuck at article_requested -- nothing to do")
        return

    resp = requests.post(
        f"{base}/admin/outreach-queue/link-article",
        json={"prospect_id": prospect_id, "slug": SLUG},
        auth=_auth(), timeout=30,
    )
    resp.raise_for_status()
    print(f"Linked prospect {prospect_id} -> slug {SLUG!r}: {resp.json()}")


if __name__ == "__main__":
    main()
