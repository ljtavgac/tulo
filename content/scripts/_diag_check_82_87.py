"""Throwaway: dumps full records for prospects 82-87, the latte query's
clean re-draft under the fixed pipeline (max_tokens=8192 + code-fence
stripping), to verify the many-sub-question format, content_opportunity
spinoffs, and linked-items grouping all worked correctly before folding
into the live queue. Deleted after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    for target_id in range(82, 88):
        print(f"\n--- id={target_id} ---")
        found = False
        for row in rows:
            if row.get("id") == target_id:
                found = True
                for k, v in row.items():
                    print(f"{k}: {v!r}")
        if not found:
            print(f"id={target_id} not found")


if __name__ == "__main__":
    main()
