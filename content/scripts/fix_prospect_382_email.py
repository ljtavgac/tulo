"""One-off: backfills the real reporter contact info onto prospect #382
and rewrites it from a "no email, submit manually" placeholder into a
real, directly-sendable reply.

Root cause (see diagnose_haro_ingestion_status.py and the
_MAX_INGESTED_QUERY_CHARS fix in backend/app/main.py): the HARO digest
that produced prospects #382/383/384 was truncated at the old 8000-char
ingestion limit right before item #14's "Email:" line, so
_draft_haro_replies never saw the real reply address for this query and
correctly (per its own rules) left reporter_email null, which routed
#382 into "no email, submit via outlet's platform" instead of a normal
emailable reply. The user then pasted the raw digest excerpt for item
#14, which does contain the real per-query address:

    Name: Nancy Schimelpfening
    Email: reply+ac600c43-5e2c-4cd6-b345-881b9d98e570@helpareporter.com
    Media Outlet: Healthline

#383 (folded into #382's reply) and #384 (rejected duplicate) are both
already terminal and don't need this -- only #382 is still actionable
(status=queued, not yet approved/sent).

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/fix_prospect_382_email.py
"""

from __future__ import annotations

import os

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
PROSPECT_ID = 382

REPORTER_EMAIL = "reply+ac600c43-5e2c-4cd6-b345-881b9d98e570@helpareporter.com"
REPORTER_NAME = "Nancy Schimelpfening"

NEW_SUBJECT = "Source for your ultra-processed foods meta-analysis piece"
NEW_BODY = (
    "Hi Nancy,\n\n"
    "I saw the call for commentary on the new meta-analysis tying ultra-processed food "
    "intake to higher disease risk and wanted to send over what we can offer on each "
    "point below.\n\n"
    "1. What are ultra-processed foods?\n"
    "https://tulo.io/food/what-is/what-are-ultra-processed-foods\n\n"
    "2. How much is too much?\n"
    "https://tulo.io/food/how-to/how-to-reduce-ultra-processed-foods-in-your-diet "
    "(covered in the same piece as point 3 below, which includes specific intake "
    "thresholds from the research)\n\n"
    "3. What practical steps can people take to reduce their consumption?\n"
    "https://tulo.io/food/how-to/how-to-reduce-ultra-processed-foods-in-your-diet\n\n"
    "Let me know if you have any questions or if there's anything else I can help "
    "clarify.\n\n"
    "Thanks for your time,\nTulo Team"
)


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/update-contact",
        params={
            "prospect_id": PROSPECT_ID,
            "contact_email": REPORTER_EMAIL,
            "contact_name": REPORTER_NAME,
            "show": "queued",
        },
        auth=AUTH, timeout=30, allow_redirects=False,
    )
    print(f"update-contact -> HTTP {r.status_code}")
    r.raise_for_status()

    r = requests.post(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/update-content",
        data={
            "prospect_id": PROSPECT_ID,
            "subject": NEW_SUBJECT,
            "body": NEW_BODY,
            "show": "queued",
        },
        auth=AUTH, timeout=30, allow_redirects=False,
    )
    print(f"update-content -> HTTP {r.status_code}")
    r.raise_for_status()

    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "queued"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    row = next((row for row in r.json() if row["id"] == PROSPECT_ID), None)
    if row is None:
        raise RuntimeError(f"Prospect {PROSPECT_ID} not found at status=queued after update")

    assert row["contact_email"] == REPORTER_EMAIL, row["contact_email"]
    assert row["contact_name"] == REPORTER_NAME, row["contact_name"]
    assert row["subject"] == NEW_SUBJECT, row["subject"]
    assert row["body_preview"] == NEW_BODY, row["body_preview"]
    print("*** CONFIRMED: prospect 382 now has a real contact_email/contact_name "
          "and a normal (non-manual-submission) subject/body. ***")


if __name__ == "__main__":
    main()
