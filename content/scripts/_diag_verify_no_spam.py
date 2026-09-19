"""Throwaway: confirms the retry-window bound fix is deployed and that
hitting the outreach portal page (which runs _retry_stale_batch_approvals
on every load) no longer re-fires a dispatch for the ancient,
abandoned batch 9999 approval. Deleted after use."""

from __future__ import annotations

import os
import time

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/health", timeout=15)
    print(f"/health: {r.status_code} {r.text[:200]}")

    for i in range(3):
        r = requests.get(f"{base}/admin/outreach-queue?show=all", auth=auth, timeout=30)
        print(f"portal load {i + 1}: {r.status_code}")
        r.raise_for_status()
        time.sleep(2)

    print("Done -- check GitHub Actions run list separately to confirm no new merge-approved-batch.yml runs fired.")


if __name__ == "__main__":
    main()
