"""One-off: validates outreach_fetch.extract_mailto_emails() against real
live pages before trusting the fix wired into all six outreach-sourcing
scripts today (2026-09-25) -- see diagnose_mailto_extraction_gap_20260925.py
for the original hypothesis test and content/scripts/outreach_fetch.py's
docstring for the full rationale.

Checks:
1. The two domains confirmed live on 2026-09-25 to have a real mailto:
   address invisible to get_text() (brooklynsupper.com, thefullhelping.com)
   are recovered correctly.
2. A domain confirmed to have NO mailto: link (bakingbites.com) correctly
   returns an empty list, not a false positive.
3. The junk-address filter drops obvious placeholders.

Usage:
    python3 content/scripts/validate_mailto_extraction_fix_20260925.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "content/scripts")
import outreach_fetch  # noqa: E402


def main() -> None:
    failures = []

    html = outreach_fetch.fetch("https://brooklynsupper.com/about")
    assert html is not None, "brooklynsupper.com/about fetch failed"
    found = outreach_fetch.extract_mailto_emails(html)
    print(f"brooklynsupper.com/about -> {found}")
    if "brooklynsupper@gmail.com" not in found:
        failures.append("brooklynsupper.com: expected address not recovered")

    html = outreach_fetch.fetch("https://thefullhelping.com/")
    assert html is not None, "thefullhelping.com/ fetch failed"
    found = outreach_fetch.extract_mailto_emails(html)
    print(f"thefullhelping.com/ -> {found}")
    if "gena@thefullhelping.com" not in found:
        failures.append("thefullhelping.com: expected address not recovered")

    html = outreach_fetch.fetch("https://bakingbites.com/")
    assert html is not None, "bakingbites.com/ fetch failed"
    found = outreach_fetch.extract_mailto_emails(html)
    print(f"bakingbites.com/ -> {found}")
    if found:
        failures.append(f"bakingbites.com: expected no mailto, got {found}")

    junk_html = '<a href="mailto:email@example.com">Email</a> <a href="mailto:real@site.com">Real</a>'
    found = outreach_fetch.extract_mailto_emails(junk_html)
    print(f"junk-filter test -> {found}")
    if found != ["real@site.com"]:
        failures.append(f"junk filter: expected ['real@site.com'], got {found}")

    outreach_fetch.close()

    print()
    if failures:
        print(f"*** {len(failures)} FAILURE(S) ***")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)
    print("*** ALL CHECKS PASSED ***")


if __name__ == "__main__":
    main()
