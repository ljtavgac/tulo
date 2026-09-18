"""Throwaway: backfills source_platform on existing haro_reply rows that
predate that field, using this session's own record of what sender each
one actually came from -- not a guess. Deleted after use.

id=72 ('Daily Meal', a live inbound webhook call at 2026-09-18T21:06:52
that this session didn't trigger) is deliberately left out: nothing in
this session's history says which service forwarded it."""

from __future__ import annotations

import os

import requests

# id -> platform, each backed by a specific, checkable fact from this
# session (not an inference from target_domain, which holds the
# reporter's own outlet name, not the forwarding platform):
KNOWN_SOURCES = {
    59: "HARO",  # target_domain is literally 'helpareporter.com' -- the
    # sender_domain fallback, since no outlet was returned for this one.
    69: "Connectively",  # the real Sept 18 Connectively forward's Essex
    # Foodies query, drafted earlier this session.
    71: "Featured.com",  # target_domain is literally 'featured.com' --
    # the raw-digest fallback row from the (since-fixed) isolated
    # Food Republic retest, sent as noreply@featured.com.
    73: "Featured.com",  # this session's own rerun script sent the
    # Food Republic query as noreply@featured.com.
    74: "Connectively",  # this session's own rerun script sent the
    # Southern Living query as noreply@connectively.us.
}


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    for prospect_id, platform in KNOWN_SOURCES.items():
        r = requests.get(
            f"{base}/admin/outreach-queue/update-source-platform",
            params={"prospect_id": prospect_id, "source_platform": platform},
            auth=auth,
            timeout=60,
            allow_redirects=False,
        )
        print(f"prospect_id={prospect_id} platform={platform!r} status={r.status_code}")


if __name__ == "__main__":
    main()
