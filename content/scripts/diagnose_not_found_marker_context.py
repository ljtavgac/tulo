"""One-off diagnostic: for a few domains the new contact-form check
flagged via a matched "page not found" marker (same URL, not a
redirect), dump the actual surrounding text so it's possible to tell a
genuine dead/soft-404 page apart from the marker phrase showing up as
unrelated page furniture (a hidden search-no-results widget, a "how to
fix a 404" blog post link in a sidebar, etc.) before trusting the
rejection as correct.

Usage:
    python3 content/scripts/diagnose_not_found_marker_context.py
"""

from __future__ import annotations

import re

import requests

from outreach_fetch import HEADERS, NOT_FOUND_MARKERS

DOMAINS = [
    "foodnetwork.com",
    "ambitiouskitchen.com",
    "tasteofhome.com",
    "diethood.com",
    "kalynskitchen.com",
    "joythebaker.com",
]


def _plain_text(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def main() -> None:
    for domain in DOMAINS:
        url = f"https://{domain}/contact"
        print(f"--- {domain} ---")
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
        except requests.RequestException as e:
            print(f"  ERROR: {e}\n")
            continue
        print(f"  status: {r.status_code}, final url: {r.url}")
        low = r.text.lower()
        text = _plain_text(r.text)
        low_text = text.lower()
        for marker in NOT_FOUND_MARKERS:
            if marker in low:
                idx = low_text.find(marker)
                if idx == -1:
                    # marker was inside a tag/attribute, not visible text
                    print(f"  matched {marker!r} but NOT in visible text (likely a class name, alt text, or hidden element)")
                    continue
                start = max(0, idx - 150)
                end = min(len(text), idx + len(marker) + 150)
                print(f"  matched {marker!r} -- context: ...{text[start:end]}...")
        # Also print the <title> for a quick sanity read
        m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.IGNORECASE | re.DOTALL)
        print(f"  <title>: {m.group(1).strip() if m else '(none)'}")
        print()


if __name__ == "__main__":
    main()
