"""One-off: confirms the Anthropic API key rotated on 2026-10-02 (the
"tulo" key, which was expiring 2026-10-09) actually works in both places
it's configured:

1. GitHub Actions secret PIPELINE_ANTHROPIC_API_KEY -- tested with one
   minimal, real Claude call (max_tokens=5) so this script's own run
   proves the exact credential every outreach-sourcing workflow uses is
   live, not just that *a* key works somewhere.

2. The staging backend's ANTHROPIC_API_KEY env var -- tested by POSTing a
   synthetic, CloudMailin-shaped inbound-email payload to
   /admin/outreach-queue/ingest-email whose body deliberately contains no
   real journalist query. See outreach_queue_ingest_email's own code in
   backend/app/main.py: when _draft_haro_replies runs successfully but
   finds nothing relevant, it returns an empty list (not None), so the
   endpoint responds {"created_prospect_ids": [], "relevant_queries_found": 0}
   -- zero rows ever written, no queue cleanup needed. If the key were
   missing or invalid instead, _draft_haro_replies would raise, and the
   endpoint would silently fall back to queuing one raw placeholder row
   with "auto_drafting_skipped_reason" explaining why -- that fallback
   path is itself the failure signal this diagnostic checks for.

No cost beyond one 5-output-token Claude call plus whatever
_draft_haro_replies' own real triage call costs (same as any live HARO
digest) -- a few cents at most.

Usage:
    PIPELINE_ANTHROPIC_API_KEY=... OUTREACH_ADMIN_USER=... \\
    OUTREACH_ADMIN_PASSWORD=... BACKEND_BASE_URL=https://tulo-backend-staging.onrender.com \\
    python3 content/scripts/diagnose_api_key_rotation_20261002.py
"""

from __future__ import annotations

import os
import sys

import requests


def check_github_secret() -> bool:
    print("--- 1. GitHub Actions secret: PIPELINE_ANTHROPIC_API_KEY ---")
    key = os.environ.get("PIPELINE_ANTHROPIC_API_KEY")
    if not key:
        print("  PIPELINE_ANTHROPIC_API_KEY is not set in this environment at all.")
        return False
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=key)
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=5,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        print(f"  Live call succeeded. Model replied: {text!r}")
        return True
    except Exception as e:  # noqa: BLE001 -- this is the failure signal itself
        print(f"  Live call failed: {type(e).__name__}: {e}")
        return False


def check_render_staging_backend() -> bool:
    print("\n--- 2. Render staging backend: ANTHROPIC_API_KEY ---")
    base = os.environ.get("BACKEND_BASE_URL", "https://tulo-backend-staging.onrender.com").rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    payload = {
        "envelope": {"from": "diagnostic-test@example.com"},
        "headers": {"subject": "[diagnostic] API key rotation check -- not a real query"},
        "plain": (
            "This is an automated diagnostic payload sent by "
            "diagnose_api_key_rotation_20261002.py to confirm the backend's "
            "ANTHROPIC_API_KEY env var works after rotation. There is no "
            "real journalist query in this message -- please disregard."
        ),
    }
    r = requests.post(
        f"{base}/admin/outreach-queue/ingest-email",
        auth=auth,
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    result = r.json()
    print(f"  Response: {result}")
    if "relevant_queries_found" in result:
        print("  _draft_haro_replies ran successfully (found 0 relevant queries, as expected for this payload).")
        print("  No rows created -- ANTHROPIC_API_KEY is working on this backend.")
        return True
    skipped_reason = result.get("auto_drafting_skipped_reason")
    print(f"  Drafting did NOT run -- fell back to a placeholder row (id {result.get('created_prospect_id')}).")
    print(f"  Reason: {skipped_reason!r}")
    print("  ANTHROPIC_API_KEY is missing or invalid on this backend -- a placeholder row was left in the queue;")
    print("  reject it from the portal once this is resolved.")
    return False


def main() -> None:
    gh_ok = check_github_secret()
    render_ok = check_render_staging_backend()
    print(f"\nSummary: GitHub secret {'OK' if gh_ok else 'FAILED'}, Render staging backend {'OK' if render_ok else 'FAILED'}")
    if not (gh_ok and render_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
