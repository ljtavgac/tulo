"""One-off validation: confirms the new Playwright bot-block fallback in
outreach_fetch.fetch() actually recovers the real domains that today's
daily-link-building.yml run marked "homepage fetch failed" (per
diagnose_homepage_fetch_failures.py's 2026-09-24 run). For each domain,
reports what the OLD plain-requests-only behavior would have returned
(None = would have been silently skipped) next to what fetch() with the
new fallback actually returns now, so the recovery rate is real evidence,
not a guess.

Usage:
    python3 content/scripts/validate_outreach_fetch_fallback.py
"""

from __future__ import annotations

import time

import requests

from outreach_fetch import HEADERS, close, fetch

# The exact domains confirmed bot-blocked (not genuinely down) by
# diagnose_homepage_fetch_failures.py's 2026-09-24 run, plus a known-good
# control (a domain that returned a clean 200 in that same run) to confirm
# the fallback doesn't change behavior for sites that were never a problem.
DOMAINS = [
    "foodnetwork.com",
    "food52.com",
    "damndelicious.net",
    "thewoksoflife.com",
    "diethood.com",
    "rasamalaysia.com",
    "shugarysweets.com",
    "drizzleanddip.com",
    "ambitiouskitchen.com",  # control: was already a clean 200
]


def old_behavior(domain: str) -> bool:
    """Replicates the pre-fix _fetch(): plain request, non-200 -> None."""
    try:
        r = requests.get(f"https://{domain}/", headers=HEADERS, timeout=20)
        return r.status_code == 200
    except requests.RequestException:
        return False


def main() -> None:
    results = []
    for domain in DOMAINS:
        url = f"https://{domain}/"
        old_ok = old_behavior(domain)
        start = time.monotonic()
        html = fetch(url, timeout=20)
        elapsed = time.monotonic() - start
        new_ok = html is not None
        results.append((domain, old_ok, new_ok, elapsed, len(html) if html else 0))
        recovered = " *** RECOVERED ***" if (new_ok and not old_ok) else ""
        still_blocked = " *** STILL BLOCKED ***" if (not new_ok and not old_ok) else ""
        print(
            f"{domain}: old={'OK' if old_ok else 'FAIL'} new={'OK' if new_ok else 'FAIL'} "
            f"({elapsed:.1f}s, {len(html) if html else 0} bytes){recovered}{still_blocked}"
        )

    close()

    total = len(results)
    old_failures = sum(1 for _, old_ok, _, _, _ in results if not old_ok)
    recovered = sum(1 for _, old_ok, new_ok, _, _ in results if not old_ok and new_ok)
    still_blocked = old_failures - recovered
    print()
    print(f"=== {total} domains tested, {old_failures} were bot-blocked under the old behavior ===")
    print(f"    Recovered by the Playwright fallback: {recovered}")
    print(f"    Still blocked even with the fallback: {still_blocked}")


if __name__ == "__main__":
    main()
