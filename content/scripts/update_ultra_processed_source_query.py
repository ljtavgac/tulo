"""One-off: broadens outreach prospect #384's source_query (the "How to
Reduce Ultra-Processed Foods in Your Diet" howto_technique article) so
that when it's generated, it also directly answers "how much is too
much" -- the HARO query's second sub-question, which the triage step
explicitly couldn't produce a standalone URL for (see prospect #382's
draft reply body). Calls the new
/admin/outreach-queue/update-source-query endpoint, then re-fetches the
row to confirm the write actually took before anything downstream
(Create Article / real generation) depends on it.

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/update_ultra_processed_source_query.py
"""

from __future__ import annotations

import os

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
PROSPECT_ID = 384

NEW_SOURCE_QUERY = (
    "What practical steps can people take to reduce their consumption? "
    "Also directly answer, either as a dedicated section or as one of the "
    "page's FAQ entries: how much ultra-processed food is “too much” -- "
    "i.e., what level of intake (share of daily calories, meals per day/week, "
    "etc.) research associates with meaningfully higher health risk -- so a "
    "reader gets a real answer to that question without needing a separate page."
)


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "article_pending"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    before = next((row for row in r.json() if row["id"] == PROSPECT_ID), None)
    if before is None:
        raise RuntimeError(f"Prospect {PROSPECT_ID} not found at status=article_pending -- already moved on?")
    print(f"BEFORE source_query: {before['source_query']!r}\n")

    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/update-source-query",
        params={"prospect_id": PROSPECT_ID, "source_query": NEW_SOURCE_QUERY, "show": "article_pending"},
        auth=AUTH, timeout=30, allow_redirects=False,
    )
    print(f"update-source-query -> HTTP {r.status_code}\n")
    r.raise_for_status()

    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "article_pending"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    after = next((row for row in r.json() if row["id"] == PROSPECT_ID), None)
    print(f"AFTER source_query: {after['source_query']!r}\n")

    if after["source_query"] == NEW_SOURCE_QUERY:
        print("*** CONFIRMED: source_query updated correctly. ***")
    else:
        raise RuntimeError("source_query after the update does not match what was sent -- do not proceed to Create Article.")


if __name__ == "__main__":
    main()
