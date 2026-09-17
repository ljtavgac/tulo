"""One-off: sets contact_email on the seeded haro_reply example
("Source for your ingredient-substitution piece"), which predates the
drafting pipeline and was seeded with contact_email=None. Editing
_seed_outreach_examples() in main.py only affects a brand-new empty
database, not this already-existing row -- this script is the one-time
fix for the row that's actually live right now.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/fix_haro_example_contact.py
"""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/admin/outreach-queue/list.json", auth=auth, params={"status": "all"}, timeout=30)
    r.raise_for_status()
    rows = [
        row
        for row in r.json()
        if row["is_example"] and row["target_domain"] == "example-journalist-outlet.test" and not row["contact_email"]
    ]

    print(f"{len(rows)} row(s) to fix.")
    for row in rows:
        resp = requests.get(
            f"{base}/admin/outreach-queue/update-contact",
            auth=auth,
            params={
                "prospect_id": row["id"],
                "contact_email": "reporter@example-journalist-outlet.test",
                "show": row["status"],
            },
            timeout=30,
            allow_redirects=False,
        )
        ok = resp.status_code == 303
        print(f"  {'fixed' if ok else f'FAILED ({resp.status_code})'}  id={row['id']}")


if __name__ == "__main__":
    main()
