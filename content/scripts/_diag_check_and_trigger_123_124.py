"""Throwaway: checks status of the two Southern Living content_
opportunity rows the user already clicked Create Article on (123, 124)
before the immediate-dispatch fix was live -- if still stuck at
article_requested with generation never actually triggered, dispatches
generate-haro-article.yml for both directly via the GitHub API so they
run now instead of making the user re-click. Deleted after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    by_id = {row["id"]: row for row in rows}

    for target_id in (123, 124):
        row = by_id.get(target_id)
        if row:
            print(f"id={target_id}: status={row['status']!r} title={row.get('proposed_title')!r} target_slug={row.get('target_slug')!r}")
        else:
            print(f"id={target_id}: not found")


if __name__ == "__main__":
    main()
