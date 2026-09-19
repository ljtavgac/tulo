"""Throwaway: retries article generation for the "Why Espresso Tastes
Bitter, Sour, or Burnt" content_opportunity, which failed with the same
git-push-race error as prospects 120/121 (collateral damage from an
earlier burst of concurrent generate-haro-article.yml dispatches).
Finds its id by title, then retries via the same create-article POST
the portal's own Retry button uses. Deleted after use."""

from __future__ import annotations

import os

import requests

TITLE = "Why Espresso Tastes Bitter, Sour, or Burnt"


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
    print(f"id={row['id']}: status={row['status']!r}")
    if row["status"] != "article_failed":
        print("Not in article_failed state -- not retrying")
        return
    resp = requests.post(
        f"{base}/admin/outreach-queue/create-article",
        data={"prospect_id": row["id"], "show": "all"},
        auth=_auth(), timeout=30, allow_redirects=False,
    )
    print(f"id={row['id']}: create-article POST -> {resp.status_code}")


if __name__ == "__main__":
    main()
