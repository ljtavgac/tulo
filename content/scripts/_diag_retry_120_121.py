"""Throwaway: retries article generation for outreach prospects 120 and
121 (both latte content_opportunities), which were wrongly marked
article_failed as collateral damage from a burst of concurrent
generate-haro-article.yml dispatches racing to push to staging at the
same time. Real fix for the race itself is "don't dispatch concurrently"
-- this script does exactly that: retries 120 via the same
create-article POST the portal's own Retry button uses (flips status
article_failed -> article_requested and triggers generation), waits for
it to leave article_requested (success or failure), then does the same
for 121 only after 120 is done. Deleted after use."""

from __future__ import annotations

import os
import time

import requests


def _auth() -> tuple[str, str]:
    return (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])


def _status(base: str, prospect_id: int) -> str | None:
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=_auth(), timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    row = next((row for row in rows if row["id"] == prospect_id), None)
    return row["status"] if row else None


def _retry_and_wait(base: str, prospect_id: int, timeout_s: int = 240) -> None:
    current = _status(base, prospect_id)
    if current != "article_failed":
        print(f"id={prospect_id}: status is {current!r}, not 'article_failed' -- skipping retry")
        return
    r = requests.post(
        f"{base}/admin/outreach-queue/create-article",
        data={"prospect_id": prospect_id, "show": "all"},
        auth=_auth(), timeout=30, allow_redirects=False,
    )
    print(f"id={prospect_id}: create-article POST -> {r.status_code}")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(10)
        s = _status(base, prospect_id)
        if s != "article_requested":
            print(f"id={prospect_id}: resolved to status={s!r}")
            return
    print(f"id={prospect_id}: still 'article_requested' after {timeout_s}s -- generation may still be running")


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    _retry_and_wait(base, 120)
    _retry_and_wait(base, 121)


if __name__ == "__main__":
    main()
