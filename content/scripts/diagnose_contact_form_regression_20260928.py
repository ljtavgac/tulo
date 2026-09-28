"""One-off: investigates why "needing manual form outreach" has been 0 in
every single daily-link-building script, on both 2026-09-27 and
2026-09-28 (the two live runs since the two-phase vet/draft rewrite),
when the same check found real contact forms before that rewrite
(2026-09-25: 2 in one script, 2 in another). The rewrite never touched
_contact_form_url() or outreach_fetch.fetch_working_page() -- this
re-runs that exact, unmodified check directly against real domains from
those two runs' own "credible but no verifiable contact email or contact
form found" logs, to see whether it's a real regression in that
unchanged code path or a genuine site-population change.

No Anthropic API calls -- this is pure HTTP/Playwright, costs nothing
but GitHub Actions minutes.

Usage:
    python3 content/scripts/diagnose_contact_form_regression_20260928.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "content/scripts")
import outreach_fetch  # noqa: E402

DOMAINS = [
    "traditionaloven.com",
    "doh.wa.gov",
    "nutritioneducationstore.com",
    "tastingtable.com",
    "culinarynutrition.com",
    "44steaks.com",
    "yeprecipes.com",
    "bakingbites.com",
    "chocolateandmarrow.com",
    "withfoodandlove.com",
    "theroastedroot.net",
    "isbe.net",
]

CONTACT_FORM_PATHS = ["/contact", "/contact-us"]


def _contact_form_url(domain: str) -> str | None:
    """Exact copy of the unmodified function from daily_outreach_sourcing.py."""
    for path in CONTACT_FORM_PATHS:
        url = f"https://{domain}{path}"
        if outreach_fetch.fetch_working_page(url, timeout=10):
            return url
    return None


def main() -> None:
    found = 0
    for domain in DOMAINS:
        print(f"--- {domain} ---")
        for path in CONTACT_FORM_PATHS:
            url = f"https://{domain}{path}"
            html = outreach_fetch.fetch(url)
            if html is None:
                print(f"  {path}: fetch() returned None (genuinely unreachable or bot-blocked past the fallback)")
                continue
            working = outreach_fetch.fetch_working_page(url, timeout=10)
            print(f"  {path}: fetch() got {len(html)} chars; fetch_working_page() -> {working}")
        result = _contact_form_url(domain)
        print(f"  _contact_form_url(domain) -> {result!r}")
        if result:
            found += 1
        print()

    outreach_fetch.close()
    print(f"{found}/{len(DOMAINS)} domain(s) found a real working contact form.")


if __name__ == "__main__":
    main()
