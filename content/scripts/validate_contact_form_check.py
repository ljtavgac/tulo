"""One-off validation: pulls every already-queued prospect with a
contact_form_url set and checks it against the new
outreach_fetch.fetch_working_page() -- the real, direct test of whether
this fix would have caught the broken contact-us links the user reported
(a silent redirect to the homepage, or a soft 404 -- 200 status with a
"page not found" body) rather than a guess.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/validate_contact_form_check.py
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit

import requests

import outreach_fetch
from outreach_fetch import HEADERS, NOT_FOUND_MARKERS, close

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
AUTH = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])


def _diagnose(url: str, timeout: int = 15) -> str:
    """Like fetch_working_page(), but explains WHY a rejection happened --
    host/path mismatch (real redirect elsewhere) vs. a matched not-found
    marker vs. unreachable -- so a "BROKEN" verdict can be checked against
    the real cause instead of trusted blind."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
    except requests.RequestException as e:
        return f"unreachable ({type(e).__name__})"

    if r.status_code == 200:
        html, final_url = r.text, r.url
    elif outreach_fetch._looks_like_bot_block(r.status_code, r.text):
        result = outreach_fetch._fetch_with_browser(url, timeout=timeout)
        if result is None:
            return f"bot-blocked (status {r.status_code}), browser fallback also failed"
        html, final_url = result
    else:
        return f"HTTP {r.status_code}"

    req = urlsplit(url)
    fin = urlsplit(final_url)
    req_host, fin_host = outreach_fetch._normalize_host(req.netloc), outreach_fetch._normalize_host(fin.netloc)
    if req_host != fin_host:
        return f"redirected to different host: {final_url!r}"
    if req.path.rstrip("/") != fin.path.rstrip("/"):
        return f"redirected to different path: {final_url!r}"
    low = html.lower()
    hit = next((m for m in NOT_FOUND_MARKERS if m in low), None)
    if hit:
        return f"matched not-found marker {hit!r} (same URL, final={final_url!r})"
    return "WORKING"


def main() -> None:
    r = requests.get(
        f"{BACKEND_BASE_URL}/admin/outreach-queue/list.json",
        params={"status": "all"},
        auth=AUTH,
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json()

    with_form = [row for row in rows if row.get("contact_form_url")]
    print(f"Total rows in queue: {len(rows)}")
    print(f"Rows with a contact_form_url set: {len(with_form)}\n")

    working = 0
    broken = 0
    for row in with_form:
        url = row["contact_form_url"]
        reason = _diagnose(url)
        ok = reason == "WORKING"
        print(f"id={row['id']} {row.get('target_domain')!r}: {url} -> {reason}")
        if ok:
            working += 1
        else:
            broken += 1

    close()
    print(f"\n=== {len(with_form)} checked: {working} working, {broken} would be rejected by the new check ===")


if __name__ == "__main__":
    main()
