"""One-off, throwaway script to test the new HARO content-opportunity ->
Create Article pipeline end to end on STAGING, using a reconstruction of
the real HARO query that originally surfaced this feature gap ("For Pro
Bakers: The Cons of Greasing Pans With Butter", Simply Recipes / Sara
Bir -- see the outreach portal conversation this was built from). Not a
permanent part of the pipeline -- delete after use.

Does three things:
1. POSTs a synthetic-but-realistic Postmark-shaped digest containing just
   that one query to /admin/outreach-queue/ingest-email, exercising the
   real _draft_haro_replies call.
2. Finds whichever prospect that created and prints its full row (status
   should be "article_pending" if the model judged it a genuine
   no-existing-match opportunity, same as the real digest run).
3. If it's article_pending, clicks Create Article for it (the same POST
   the portal's own button makes) and prints the resulting prospect_id --
   feed that id into generate-haro-article.yml next.

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_test_haro_article_pipeline.py
"""

from __future__ import annotations

import os

import requests

DIGEST_BODY = """Query: For Pro Bakers: The Cons of Greasing Pans With Butter

I'm working on a piece about why many professional and experienced home
bakers avoid greasing cake, bread, and muffin pans with butter, and what
they reach for instead (shortening, neutral oil, flour, parchment, or a
commercial pan spray) and why. Looking for input on the practical/science
reasons butter is often a worse choice for this specific job -- its water
content, how it browns or burns at oven temperatures, and sticking risk
compared to the alternatives. Direct quotes or a link to a solid existing
explainer are both welcome. This is for Simply Recipes.

Reporter: Sara Bir, Simply Recipes
Category: Food & Cooking
Reply to this query: reply+test-greasing-pans-9f21@helpareporter.com
"""


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.post(
        f"{base}/admin/outreach-queue/ingest-email",
        auth=auth,
        json={
            "FromFull": {"Email": "test-sender@helpareporter.com"},
            "Subject": "HARO Queries for Food & Cooking (TEST)",
            "TextBody": DIGEST_BODY,
        },
        timeout=120,
    )
    r.raise_for_status()
    ingest_result = r.json()
    print(f"ingest-email response: {ingest_result}")

    ids = ingest_result.get("created_prospect_ids")
    if not ids:
        print("No prospect created (either no created_prospect_ids key, or the fallback "
              "raw-digest path fired -- see auto_drafting_skipped_reason above).")
        return

    r = requests.get(f"{base}/admin/outreach-queue/list.json", auth=auth, params={"status": "all"}, timeout=30)
    r.raise_for_status()
    rows = {row["id"]: row for row in r.json()}

    for pid in ids:
        row = rows.get(pid)
        print(f"\nprospect id={pid}: {row}")
        if row and row["status"] == "article_pending":
            resp = requests.post(
                f"{base}/admin/outreach-queue/create-article",
                auth=auth,
                data={"prospect_id": pid, "show": "article_pending"},
                allow_redirects=False,
                timeout=30,
            )
            print(f"create-article -> {resp.status_code}")
            if resp.status_code == 303:
                print(f"\n*** prospect_id {pid} is now article_requested -- "
                      f"trigger generate-haro-article.yml with prospect_id={pid} next. ***")


if __name__ == "__main__":
    main()
