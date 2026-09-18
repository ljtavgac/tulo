"""Throwaway diagnostic: replays one specific HARO query (the "best way
to cook bacon" query from 2026-09-18's digest, which produced no action
item in the outreach portal) through the real /admin/outreach-queue/
ingest-email endpoint on staging, using the real ANTHROPIC_API_KEY that
deployment has configured -- so this exercises the actual
_draft_haro_replies triage logic, not a guess about what it would do.
Prints the raw JSON response. Deleted after use, not part of the
pipeline.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_bacon_query.py
"""

from __future__ import annotations

import os

import requests

QUERY_TEXT = """Summary: Looking of professional chefs to weigh in on the best way to cook bacon

Name: Jeanine Edwards

Category: Lifestyle and Entertainment

Email: reply+7d2fe06a-4343-416b-87d2-23d3c409b378@helpareporter.com

HARO Journalist Profile URL: https://www.helpareporter.com/journalist/jeanine-edwards

Media Outlet: Yahoo (https://www.yahoo.com)

Deadline: 5:42 PM ET - 20 September

No AI Pitches Considered

Query:
I'm looking for US-based professional/trained chefs to comment on the best ways to cook bacon. Looking for pros and cons of cooking bacon in the microwave, in the oven, on a flat top and in a frying pan.
"""


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    payload = {
        "FromFull": {"Email": "diag-test@helpareporter.com"},
        "Subject": "_diag_bacon_query replay",
        "TextBody": QUERY_TEXT,
    }
    r = requests.post(f"{base}/admin/outreach-queue/ingest-email", auth=auth, json=payload, timeout=60)
    print("status:", r.status_code)
    print(r.text)


if __name__ == "__main__":
    main()
