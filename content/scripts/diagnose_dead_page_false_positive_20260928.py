"""One-off: theroastedroot.net/contact and /contact-us both fetched real,
substantial content (110593 and 86933 chars) but outreach_fetch.
fetch_working_page() still returned False -- pins down exactly which
check inside _is_dead_page() is firing so it can be fixed.

No Anthropic API calls.

Usage:
    python3 content/scripts/diagnose_dead_page_false_positive_20260928.py
"""

from __future__ import annotations

import sys
from urllib.parse import urlsplit

import requests

sys.path.insert(0, "content/scripts")
import outreach_fetch  # noqa: E402

URLS = ["https://theroastedroot.net/contact", "https://theroastedroot.net/contact-us"]


def main() -> None:
    for url in URLS:
        print(f"--- {url} ---")
        r = requests.get(url, headers=outreach_fetch.HEADERS, timeout=20)
        print(f"  status: {r.status_code}, final url: {r.url}, len: {len(r.text)}")

        req = urlsplit(url)
        fin = urlsplit(r.url)
        host_match = outreach_fetch._normalize_host(req.netloc) == outreach_fetch._normalize_host(fin.netloc)
        path_match = req.path.rstrip("/") == fin.path.rstrip("/")
        print(f"  host match: {host_match} ({req.netloc!r} vs {fin.netloc!r})")
        print(f"  path match: {path_match} ({req.path!r} vs {fin.path!r})")

        low = r.text.lower()
        hit_bot = [m for m in outreach_fetch.BOT_BLOCK_MARKERS if m in low]
        hit_404 = [m for m in outreach_fetch.NOT_FOUND_MARKERS if m in low]
        print(f"  bot-block markers found: {hit_bot}")
        print(f"  not-found markers found: {hit_404}")

        is_dead = outreach_fetch._is_dead_page(r.text, url, r.url)
        print(f"  _is_dead_page() -> {is_dead}")

        if hit_404:
            for marker in hit_404:
                idx = low.find(marker)
                print(f"  context around {marker!r}: ...{r.text[max(0,idx-80):idx+120]!r}...")
        print()


if __name__ == "__main__":
    main()
