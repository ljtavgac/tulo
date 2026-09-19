"""Throwaway: final end-of-session sanity check that the live staging
backend actually deployed today's last commit and the outreach portal
loads without error (the new _retry_stale_batch_approvals call runs on
every outreach_queue()/review_queue() page load, so this also proves
it doesn't crash the page). Deleted after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/health", timeout=30)
    print(f"/health: {r.status_code} {r.text[:300]}")

    r = requests.get(f"{base}/admin/outreach-queue?show=all", auth=auth, timeout=30)
    print(f"/admin/outreach-queue?show=all: {r.status_code}, {len(r.text)} bytes")
    r.raise_for_status()

    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=30)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    for target_id in (117, 118, 119, 120, 121, 122, 123, 124):
        row = next((row for row in rows if row["id"] == target_id), None)
        if row:
            print(f"id={target_id}: status={row['status']!r} target_slug={row.get('target_slug')!r}")
        else:
            print(f"id={target_id}: not found")


if __name__ == "__main__":
    main()
