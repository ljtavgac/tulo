"""Throwaway one-time correction: id=123's article (the wooden cutting
board how-to) went live and got resolved into a separate standalone
follow-up email by the OLD _resolve_pending_articles behavior (before
this session's "fold into the sibling reply instead of duplicating"
fix was deployed) -- exactly the duplicate-reply bug the fix addresses,
just already-materialized data from before the fix landed.

Retroactively does what the new code now does automatically:
1. Patches the real URL into reply #122's [URL placeholder -- pending:
   "How to Care for and Restore a Wooden Cutting Board"] tag.
2. Rejects the now-superseded standalone follow-up (#123) with a clear
   note explaining why, so it never gets sent as a second email.

Deleted after use."""

from __future__ import annotations

import os

import requests

REPLY_ID = 122
DUPLICATE_ID = 123
PLACEHOLDER_TAG = '[URL placeholder -- pending: "How to Care for and Restore a Wooden Cutting Board"]'
REAL_URL = "https://tulo.io/food/how-to/how-to-care-for-and-restore-a-wooden-cutting-board"


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    by_id = {row["id"]: row for row in rows}

    reply = by_id.get(REPLY_ID)
    if not reply:
        print(f"id={REPLY_ID} not found -- aborting")
        return
    if PLACEHOLDER_TAG not in reply["body_preview"]:
        print(f"id={REPLY_ID} no longer has the placeholder tag -- already resolved, nothing to do")
    else:
        new_body = reply["body_preview"].replace(PLACEHOLDER_TAG, REAL_URL)
        resp = requests.post(
            f"{base}/admin/outreach-queue/update-content",
            data={"prospect_id": REPLY_ID, "subject": reply["subject"], "body": new_body, "show": "all"},
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        print(f"id={REPLY_ID}: patched placeholder tag with real URL")

    dup = by_id.get(DUPLICATE_ID)
    if not dup:
        print(f"id={DUPLICATE_ID} not found -- aborting")
        return
    if dup["status"] != "queued":
        print(f"id={DUPLICATE_ID} status is {dup['status']!r}, not 'queued' -- leaving as-is")
        return

    note_subject = f"[Superseded -- folded into reply #{REPLY_ID}] {dup.get('proposed_title') or dup['subject']}"
    note_body = (
        f"Superseded: this article's URL was folded directly into reply #{REPLY_ID}'s numbered list "
        f"instead of being sent as a separate follow-up email. See {REAL_URL}."
    )
    resp = requests.post(
        f"{base}/admin/outreach-queue/update-content",
        data={"prospect_id": DUPLICATE_ID, "subject": note_subject, "body": note_body, "show": "all"},
        auth=auth,
        timeout=30,
    )
    resp.raise_for_status()
    resp = requests.get(
        f"{base}/admin/outreach-queue/decide",
        params={"prospect_id": DUPLICATE_ID, "status": "rejected", "show": "all"},
        auth=auth,
        timeout=30,
    )
    resp.raise_for_status()
    print(f"id={DUPLICATE_ID}: marked superseded and rejected")


if __name__ == "__main__":
    main()
