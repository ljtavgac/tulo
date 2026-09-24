"""One-off: checks whether HARO email ingestion is actually broken, per the
user's report. Lists recent OutreachProspect rows (all statuses) sorted by
id/created_at, and searches for any row referencing the "ultra-processed
foods" / Nancy Schimelpfening / Healthline query the user pasted (deadline
11:00 AM ET - 25 September) to see if this specific digest was ever ingested
at all, or was ingested and something went wrong.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/diagnose_haro_ingestion_status.py
"""

from __future__ import annotations

import os

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])


def main() -> None:
    all_rows = []
    for status in [
        "article_pending", "article_requested", "article_pending_review",
        "queued", "approved", "rejected", "folded_into_reply", "article_failed",
    ]:
        r = requests.get(
            f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
            params={"status": status},
            auth=AUTH, timeout=30,
        )
        r.raise_for_status()
        rows = r.json()
        print(f"status={status}: {len(rows)} rows")
        all_rows.extend(rows)

    all_rows.sort(key=lambda r: r.get("id", 0), reverse=True)
    print(f"\ntotal rows: {len(all_rows)}")
    print("\n--- most recent 15 rows (any status) ---")
    for row in all_rows[:15]:
        print(
            f"id={row['id']} status={row['status']} created_at={row.get('created_at')} "
            f"contact_email={row.get('contact_email')!r} target_domain={row.get('target_domain')!r} "
            f"subject={row.get('subject', '')[:70]!r}"
        )

    print("\n--- searching for 'ultra-processed' / 'Schimelpfening' / 'Healthline' / 'ac600c43' ---")
    needles = ["ultra-processed", "ultra processed", "schimelpfening", "healthline", "ac600c43"]
    hits = []
    for row in all_rows:
        haystack = " ".join(
            str(row.get(k, "")) for k in
            ("subject", "source_query", "contact_email", "contact_name", "target_domain", "rationale", "body_preview")
        ).lower()
        if any(n in haystack for n in needles):
            hits.append(row)

    print(f"{len(hits)} matching rows found")
    for row in hits:
        print(
            f"\nid={row['id']} status={row['status']} created_at={row.get('created_at')}\n"
            f"  contact_email={row.get('contact_email')!r}\n"
            f"  contact_name={row.get('contact_name')!r}\n"
            f"  target_domain={row.get('target_domain')!r}\n"
            f"  subject={row.get('subject')!r}\n"
            f"  source_query={str(row.get('source_query'))[:300]!r}"
        )


if __name__ == "__main__":
    main()
