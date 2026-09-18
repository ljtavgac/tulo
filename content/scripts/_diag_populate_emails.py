"""Throwaway: populates contact_email (and contact_name where known) for
the 11 queued tool_pitch prospects a deeper web search found real,
site-published addresses for. Deleted after use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_populate_emails.py
"""

from __future__ import annotations

import os

import requests

# (prospect_id, contact_email, contact_name, source note)
UPDATES = [
    (56, "lindsay@loveandoliveoil.com", "Lindsay Landis", "loveandoliveoil.com/contact-us"),
    (54, "howsweeteats@gmail.com", "Jessica Merchant", "howsweeteats.com/privacy/"),
    (51, "hello@gimmesomeoven.com", "Ali Martin", "gimmesomeoven.com/privacy-policy/"),
    (50, "giangi@giangiskitchen.com", "Giangi Townsend", "giangiskitchen.com/contact/"),
    (49, "lisab@downshiftology.com", "Lisa Bryan", "downshiftology.com/privacy-policy/"),
    (46, "cookingclassy@yahoo.com", "Jaclyn Bell", "cookingclassy.com/contact/ (moderate confidence)"),
    (45, "info@chefspencil.com", "", "chefspencil.com/contact-us/"),
    (44, "support@budgetbytes.com", "Beth Moncel", "budgetbytes.com/contact/"),
    (43, "michelle@browneyedbaker.com", "Michelle", "browneyedbaker.com/contact/"),
    (41, "alexandra@alexandracooks.com", "Alexandra Stafford", "alexandracooks.com/contact/"),
    (40, "email@acouplecooks.com", "Alex & Sonja Overhiser", "acouplecooks.com/contact-us/"),
]


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    for prospect_id, email, name, source in UPDATES:
        resp = requests.get(
            f"{base}/admin/outreach-queue/update-contact",
            auth=auth,
            params={"prospect_id": prospect_id, "contact_email": email, "contact_name": name, "show": "queued"},
            timeout=30,
            allow_redirects=False,
        )
        ok = resp.status_code == 303
        print(f"  id={prospect_id} {'OK' if ok else f'FAILED ({resp.status_code})'} email={email} ({source})")


if __name__ == "__main__":
    main()
