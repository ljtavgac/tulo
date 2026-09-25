"""One-off: tests a hypothesis for why so many otherwise-credible outreach
candidates lose their claimed contact_email during verification (12 of
today's 2026-09-25 daily-link-building run's credible candidates hit
"claimed contact_email not verified against fetched page text, dropping
email only").

_page_text() (daily_outreach_sourcing.py / resource_page_outreach.py /
etc.) extracts page text via BeautifulSoup's soup.get_text(), which drops
every HTML tag and attribute -- including a <a href="mailto:x@y.com">
link's actual address when the visible anchor text is something like
"Contact us" or an icon with no alt text. The model is only ever given
this stripped text, so it can never see a mailto-only address as
"printed" in what it's shown -- if it still reports an email (from
general knowledge of the site, or a plausible guess like info@domain.com
or hello@domain.com), the current verification correctly rejects it as
unconfirmed, exactly as designed. But if the REAL address is sitting
right there in a mailto: href the whole time, that's a solvable gap, not
just the model being wrong: extracting mailto hrefs directly from the
raw HTML (never trusting model output, same invariant as everywhere
else) would recover a real, already-page-verified address without
needing the model to find or repeat it at all.

This script re-fetches a sample of today's "claimed but unverified"
domains and checks their raw HTML for any mailto: link, to see how often
a real address was sitting in the markup the extraction pipeline
currently never looks at.

Usage:
    python3 content/scripts/diagnose_mailto_extraction_gap_20260925.py
"""

from __future__ import annotations

import re
import sys

sys.path.insert(0, "content/scripts")
import outreach_fetch  # noqa: E402

DOMAINS = [
    "bakingbites.com",
    "brooklynsupper.com",
    "theroastedroot.net",
    "thefullhelping.com",
    "yeprecipes.com",
    "chocolateandmarrow.com",
    "withfoodandlove.com",
    "culinarynutrition.com",
    "nutritioneducationstore.com",
    "traditionaloven.com",
]

MAILTO_RE = re.compile(r'href=["\']mailto:([^"\'?]+)', re.IGNORECASE)


def main() -> None:
    found_mailto = {}
    for domain in DOMAINS:
        print(f"--- {domain} ---")
        pages_with_mailto = []
        for path in ["/", "/contact", "/contact-us", "/about", "/about-us", "/privacy-policy"]:
            html = outreach_fetch.fetch(f"https://{domain}{path}")
            if html is None:
                continue
            matches = MAILTO_RE.findall(html)
            if matches:
                emails = sorted(set(m.strip().lower() for m in matches))
                pages_with_mailto.append((path, emails))
                print(f"  {path}: mailto found -> {emails}")
        if pages_with_mailto:
            found_mailto[domain] = pages_with_mailto
        else:
            print("  no mailto: link found on any checked page")
        print()

    outreach_fetch.close()

    print("=" * 70)
    print(f"{len(found_mailto)}/{len(DOMAINS)} domain(s) have a real mailto: address on at least one "
          "checked page, invisible to the current get_text()-based extraction:")
    for domain, pages in found_mailto.items():
        print(f"  {domain}: {pages}")


if __name__ == "__main__":
    main()
