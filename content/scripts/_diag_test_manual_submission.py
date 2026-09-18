"""Throwaway: a purpose-built synthetic digest with one genuinely on-topic
food/cooking query that has NO printed reply email (platform-link only) --
to directly prove the manual-submission drafting path (contact_email=null,
subject prefixed "[Manual submission -- ...]") actually fires end to end,
since no real forwarded digest so far has happened to combine "good topic
fit" with "no email" at the same time. Clearly marked as a test so it's
obvious to reject in the portal after confirming it worked. Deleted after
use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_test_manual_submission.py
"""

from __future__ import annotations

import os

import requests

TEST_DIGEST = """\
[TEST DIGEST -- synthetic, for verifying manual-submission drafting only]

Opportunity Alerts

TestOutlet Kitchen Digest
I'm a recipe editor putting together an evergreen guide on common home-cooking
mistakes: over-salting soup, under-seasoning pasta water, and the right way to
rest meat after cooking before slicing it. Looking for practical, home-cook-
friendly tips and any resources that explain these clearly.
Respond via our submission form: https://example-testoutlet.invalid/pitch
(No reply email address is given -- submissions only go through the form above.)
"""


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    payload = {
        "envelope": {"to": "9fa2d6374492693ffdda@cloudmailin.net", "from": "noreply@example-testoutlet.invalid"},
        "headers": {"subject": "[TEST] Manual-submission drafting verification"},
        "plain": TEST_DIGEST,
        "html": "",
    }
    r = requests.post(f"{base}/admin/outreach-queue/ingest-email", auth=auth, json=payload, timeout=120)
    print(f"status={r.status_code} body={r.text[:500]}")


if __name__ == "__main__":
    main()
