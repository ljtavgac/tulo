"""Throwaway: patches the live Southern Living reply (id=122) to add a
natural one-sentence lead-in before its numbered list, matching the
now-fixed prompt guidance -- preserves the already-verified numbered/
placeholder body exactly otherwise. Deleted after use."""

from __future__ import annotations

import os

import requests

SUBJECT = "[Manual submission -- no email, submit via outlet's platform] Sources plus a few resources for your three Southern Living pieces"

BODY = """\
Sending along a quick note on each of the three topics below.

1. Why wooden cutting boards get dark and rough over time
[URL placeholder -- pending: "How to Care for and Restore a Wooden Cutting Board"]

2. What's the difference between filet mignon and tenderloin?
[URL placeholder -- pending: "Filet Mignon vs. Beef Tenderloin: What's the Difference?"]

3. Do coconut flakes need to be refrigerated to stay fresh?
https://tulo.io/food/ingredients/desiccated-coconut"""


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    r = requests.post(
        f"{base}/admin/outreach-queue/update-content",
        data={"prospect_id": 122, "subject": SUBJECT, "body": BODY, "show": "all"},
        auth=auth, timeout=30, allow_redirects=False,
    )
    print(f"patch id=122 -> status={r.status_code}")


if __name__ == "__main__":
    main()
