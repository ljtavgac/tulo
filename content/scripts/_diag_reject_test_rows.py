"""Throwaway: rejects the two test-artifact rows created while diagnosing
the manual-submission drafting path -- id 70 (synthetic test digest) and
id 71 (the raw-digest fallback row created when the first isolated Food
Republic retest hit the since-fixed JSON-parse bug). Neither is a real
opportunity. Deleted after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    for prospect_id in (70, 71):
        r = requests.get(
            f"{base}/admin/outreach-queue/decide",
            params={"prospect_id": prospect_id, "status": "rejected"},
            auth=auth,
            timeout=60,
            allow_redirects=False,
        )
        print(f"prospect_id={prospect_id} status={r.status_code}")


if __name__ == "__main__":
    main()
