"""Throwaway: re-tests the real Food Republic item from the Featured.com
digest ALONE (not bundled with the other 3 items), to check whether
bundling with weaker items was diluting the model's judgment on this one.
Deleted after use."""

from __future__ import annotations

import os

import requests

DIGEST = """\
Featured
All-in-One - Looking for journalist requests in the recipes, food, drink...

Food Republic
Monitor HARO
I'm looking for chefs, recipe editors, food writers, and culinary experts who can provide practical insights on a range of different food topics. Subjects may include everything from food storage tips to preparation techniques to common kitchen pitfalls. The information should be accessible to the average home cook. No specific brand or product endorsements unless directly related to the article. When you respond, please share your current position and area of expertise.
Match reasoning: Requests chefs, recipe editors, and culinary experts for practical cooking and food preparation guidance -- core recipes and food journalism focus
Deadline: Dec 31, 12:00 AM EST
(No reply email in text -- respond via Featured.com platform)
"""


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    payload = {
        "envelope": {"to": "9fa2d6374492693ffdda@cloudmailin.net", "from": "noreply@featured.com"},
        "headers": {"subject": "[RETEST-ISOLATED] Food Republic only"},
        "plain": DIGEST,
        "html": "",
    }
    r = requests.post(f"{base}/admin/outreach-queue/ingest-email", auth=auth, json=payload, timeout=120)
    print(f"status={r.status_code} body={r.text[:500]}")


if __name__ == "__main__":
    main()
