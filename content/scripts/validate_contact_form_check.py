"""One-off validation: pulls every already-queued prospect with a
contact_form_url set and checks it against the new
outreach_fetch.fetch_working_page() -- the real, direct test of whether
this fix would have caught the broken contact-us links the user reported
(a silent redirect to the homepage, or a soft 404 -- 200 status with a
"page not found" body) rather than a guess.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/validate_contact_form_check.py
"""

from __future__ import annotations

import os

import requests

from outreach_fetch import close, fetch_working_page

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "all"},
        auth=AUTH,
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json()

    with_form = [row for row in rows if row.get("contact_form_url")]
    print(f"Total rows in queue: {len(rows)}")
    print(f"Rows with a contact_form_url set: {len(with_form)}\n")

    working = 0
    broken = 0
    for row in with_form:
        url = row["contact_form_url"]
        ok = fetch_working_page(url, timeout=15)
        status = "WORKING" if ok else "*** BROKEN ***"
        print(f"id={row['id']} {row.get('target_domain')!r}: {url} -> {status}")
        if ok:
            working += 1
        else:
            broken += 1

    close()
    print(f"\n=== {len(with_form)} checked: {working} working, {broken} would be rejected by the new check ===")


if __name__ == "__main__":
    main()
