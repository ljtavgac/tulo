"""Throwaway: investigates whether haro_reply prospects with
contact_email=None are genuinely platform-only (no printed reply
address anywhere in the query text) or whether a real, capturable
address exists in the source_query text that the current
_draft_haro_replies extraction is failing to pick up. Dumps every
non-example haro_reply row with contact_email=None, its source_platform,
and its full source_query text, plus a naive '@' scan to flag any row
that DOES contain an email-shaped string despite contact_email being
null (a real signal something's being missed). Deleted after use."""

from __future__ import annotations

import os
import re

import requests

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _auth() -> tuple[str, str]:
    return (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=_auth(), timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []

    candidates = [
        row for row in rows
        if row.get("pitch_type") == "haro_reply"
        and not row.get("contact_email")
        and not row.get("is_example")
    ]
    print(f"{len(candidates)} haro_reply row(s) with contact_email=None (non-example):\n")
    for row in candidates:
        query = row.get("source_query") or ""
        found = EMAIL_RE.findall(query)
        # Filter out our own domain / obvious platform noreply addresses
        # to reduce noise.
        found = [e for e in found if "tulo.io" not in e.lower()]
        flag = f"  !!! POSSIBLE MISSED EMAIL(S): {found}" if found else ""
        print(f"--- id={row['id']} platform={row.get('source_platform')!r} status={row.get('status')!r} ---{flag}")
        print(f"query: {query[:500]!r}")
        print()


if __name__ == "__main__":
    main()
