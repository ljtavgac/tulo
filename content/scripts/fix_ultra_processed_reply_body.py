"""One-off: patches outreach prospect #382's body (the combined 3-point
Healthline reply) to fill in question 2's placeholder with prospect
#384's real URL -- that article now directly answers "how much is too
much" (see update_ultra_processed_source_query.py), but nothing links
it back to point 2's dead [can't produce a URL for this] tag
automatically. Verifies the exact current body before touching it, so
this never overwrites a further edit made since the last check.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/fix_ultra_processed_reply_body.py
"""

from __future__ import annotations

import os

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
PROSPECT_ID = 382

OLD_POINT_2 = "2. How much is too much?\n[can't produce a URL for this]"
NEW_POINT_2 = (
    "2. How much is too much?\n"
    "https://tulo.io/food/how-to/how-to-reduce-ultra-processed-foods-in-your-diet "
    "(covered in the same piece as point 3 below, which includes specific intake thresholds from the research)"
)


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "queued"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    row = next((row for row in r.json() if row["id"] == PROSPECT_ID), None)
    if row is None:
        raise RuntimeError(f"Prospect {PROSPECT_ID} not found at status=queued -- already changed?")

    body = row["body_preview"]
    if OLD_POINT_2 not in body:
        raise RuntimeError(f"Expected placeholder text not found in current body -- refusing to touch it.\nCurrent body:\n{body}")

    new_body = body.replace(OLD_POINT_2, NEW_POINT_2)
    print(f"Current body:\n{body}\n")
    print(f"New body:\n{new_body}\n")

    r = requests.post(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/update-content",
        data={"prospect_id": PROSPECT_ID, "subject": row["subject"], "body": new_body, "show": "queued"},
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
    after = next((row for row in r.json() if row["id"] == PROSPECT_ID), None)
    if after and after["body_preview"] == new_body:
        print("*** CONFIRMED: body updated correctly. ***")
    else:
        raise RuntimeError(f"Body after update doesn't match what was sent.\nGot:\n{after['body_preview'] if after else None}")


if __name__ == "__main__":
    main()
