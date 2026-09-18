"""Throwaway: replaces id=72's subject/body with the improved draft from
the retest (id=75, produced by the now-fixed many-sub-question prompt),
then rejects id=75 as the superseded duplicate. Keeps the single
prospect id the user has already been reviewing. Deleted after use."""

from __future__ import annotations

import os

import requests

NEW_SUBJECT = "[Manual submission -- no email, submit via outlet's platform] Source material for your at-home latte mistakes piece"
NEW_BODY = (
    "Happy to point you toward a couple of Tulo resources that speak directly to several of your "
    "questions. For the biggest mistake, the three rules for consistency, troubleshooting a watery "
    "latte, the order of adding espresso/milk/sweetener, and what properly steamed vs. frothed milk "
    "should look and feel like, our How to Prepare a Latte guide walks through the technique end to "
    "end: https://tulo.io/food/how-to/how-to-prepare-a-latte. For the questions about store-bought "
    "espresso tasting bitter, burnt, sour, or acidic, our What Is Espresso? page breaks down "
    "extraction basics that explain why those off-flavors happen: "
    "https://tulo.io/food/what-is/what-is-espresso. We don't currently have dedicated pages on "
    "grind-setting effects, plant-based milk comparisons for lattes, sub-$20 barista tools, or "
    "grocery-store bean selection, so I can't point you to something specific on Tulo for those "
    "particular sub-questions, but the two guides above should cover the technique-heavy parts of "
    "your piece well."
)


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r1 = requests.post(
        f"{base}/admin/outreach-queue/update-content",
        auth=auth,
        data={"prospect_id": 72, "subject": NEW_SUBJECT, "body": NEW_BODY, "show": "queued"},
        timeout=60,
        allow_redirects=False,
    )
    print(f"update id=72 status={r1.status_code}")

    r2 = requests.get(
        f"{base}/admin/outreach-queue/decide",
        params={"prospect_id": 75, "status": "rejected"},
        auth=auth,
        timeout=60,
        allow_redirects=False,
    )
    print(f"reject id=75 status={r2.status_code}")


if __name__ == "__main__":
    main()
