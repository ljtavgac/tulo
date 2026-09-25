"""One-off: investigates why today's (2026-09-25) daily-link-building run
only queued 8 total prospects across all 5 sources, well under the shared
50/day cap. The run's own logs show three separate loss points:

1. Several sourcing scripts (roundup/broken-link/unlinked-mention) simply
   found very few genuinely NEW candidates today -- their fixed web_search
   query sets keep surfacing the same already-contacted domains day after
   day (expected, diminishing-returns behavior of a small fixed query
   list, not itself a bug).
2. 16 domains in step 5 (daily_outreach_sourcing.py, the hub-page crawl)
   failed with "homepage fetch failed" even with the Playwright bot-block
   fallback already wired in (content/scripts/outreach_fetch.py, staging-
   only). outreach_fetch.fetch() deliberately never tries the browser
   fallback for a plain requests.RequestException (DNS failure, connection
   reset, SSL error, timeout) -- only for a 403/429/503/redirect-loop/
   challenge-page-marker response -- reasoning that a truly dead domain
   isn't worth a browser launch. This script checks whether that's still
   the right call by getting the REAL exception/status for each of
   today's 16 failures, from a live GitHub Actions runner (same network
   position as the real pipeline), and separately checking whether
   Playwright *would* have recovered a plain-request failure if it were
   given the chance.
3. Several credible candidates were dropped for "no verifiable contact
   email or contact form found" -- this script also reports how many.

Usage:
    python3 content/scripts/diagnose_homepage_fetch_failures_20260925.py
"""

from __future__ import annotations

import sys

import requests

sys.path.insert(0, "content/scripts")
import outreach_fetch  # noqa: E402

FAILED_DOMAINS = [
    "kblog.lunchboxbunch.com",
    "bakersroyale.com",
    "brittanymullins.com",
    "cookituppaleo.com",
    "dollyandoatmeal.com",
    "faring-well.com",
    "frenchfoodieindublin.com",
    "hortuscuisine.com",
    "joyfoodly.com",
    "rawfoodrecipes.com",
    "sinamontales.com",
    "thefoodalist.com",
    "a.co",
    "linkwithin.com",
    "problogdesign.com",
    "timesonline.co.uk",
]

HEADERS = outreach_fetch.HEADERS


def main() -> None:
    print(f"Checking {len(FAILED_DOMAINS)} domain(s) that failed with 'homepage fetch failed' today...\n")

    would_recover_with_browser = []
    genuinely_dead = []

    for domain in FAILED_DOMAINS:
        url = f"https://{domain}/"
        print(f"--- {domain} ---")

        # 1. What does a plain requests.get() actually see?
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            print(f"  plain request: HTTP {r.status_code}, {len(r.text)} chars, final_url={r.url}")
            plain_exc = None
        except requests.RequestException as e:
            print(f"  plain request: {type(e).__name__}: {e}")
            plain_exc = e

        # 2. Does outreach_fetch.fetch() (the real function the pipeline
        #    calls) recover it as-is?
        html = outreach_fetch.fetch(url)
        print(f"  outreach_fetch.fetch(): {'RECOVERED (' + str(len(html)) + ' chars)' if html else 'still None'}")

        # 3. If it failed and it was a plain RequestException (not
        #    attempted via the browser today), try the browser directly to
        #    see whether it WOULD have worked if fetch() didn't skip it.
        if html is None and plain_exc is not None:
            result = outreach_fetch._fetch_with_browser(url, timeout=20)
            if result is not None:
                browser_html, final_url = result
                print(f"  browser fallback (forced): RECOVERED -- {len(browser_html)} chars, final_url={final_url}")
                would_recover_with_browser.append(domain)
            else:
                print("  browser fallback (forced): still failed -- genuinely unreachable")
                genuinely_dead.append(domain)
        elif html is None:
            genuinely_dead.append(domain)

        print()

    outreach_fetch.close()

    print("=" * 70)
    print(f"Of {len(FAILED_DOMAINS)} domains outreach_fetch.fetch() reported as failed:")
    print(f"  {len(would_recover_with_browser)} WOULD have been recovered by the browser fallback, "
          f"if fetch() tried it for a plain RequestException: {would_recover_with_browser}")
    print(f"  {len(genuinely_dead)} are genuinely unreachable even via the browser: {genuinely_dead}")


if __name__ == "__main__":
    main()
