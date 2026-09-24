"""One-off diagnostic: today's daily-link-building run marked several
major, definitely-live food blogs (foodnetwork.com, food52.com,
damndelicious.net, thewoksoflife.com, diethood.com, rasamalaysia.com,
shugarysweets.com, and others) as "homepage fetch failed" and skipped
them. daily_outreach_sourcing.py's _fetch() treats ANY non-200 response
(or any request exception) as a silent skip, with no distinction between
a genuine outage and e.g. a Cloudflare/bot-protection 403 or challenge
page -- this script reproduces the exact same request (same HEADERS,
same timeout) against each candidate and reports the real status code,
a couple of bot-protection tells (Server/cf-ray/cf-mitigated headers,
"Just a moment", "Attention Required", "captcha" in the body), and the
first bytes of the response, to tell real failures apart from blocking.

Usage:
    python3 content/scripts/diagnose_homepage_fetch_failures.py
"""

from __future__ import annotations

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

DOMAINS = [
    "foodnetwork.com",
    "food52.com",
    "damndelicious.net",
    "thewoksoflife.com",
    "diethood.com",
    "rasamalaysia.com",
    "shugarysweets.com",
    "drizzleanddip.com",
    "ambitiouskitchen.com",  # for contrast: this one was "credible but no
                              # verifiable contact", not "fetch failed" --
                              # a working baseline
]

BOT_BLOCK_MARKERS = [
    "just a moment", "attention required", "captcha", "cloudflare",
    "access denied", "are you a human", "enable javascript and cookies",
    "please verify you are a human", "checking your browser",
]


def check(domain: str) -> None:
    url = f"https://{domain}/"
    print(f"--- {domain} ---")
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")
        print()
        return

    print(f"  status: {r.status_code}")
    server = r.headers.get("Server", "")
    cf_ray = r.headers.get("cf-ray", "")
    cf_mitigated = r.headers.get("cf-mitigated", "")
    print(f"  Server: {server!r}  cf-ray: {cf_ray!r}  cf-mitigated: {cf_mitigated!r}")

    body_lower = r.text.lower() if r.status_code != 204 else ""
    hits = [m for m in BOT_BLOCK_MARKERS if m in body_lower]
    if hits:
        print(f"  *** bot-block markers in body: {hits} ***")

    if r.status_code != 200:
        print(f"  first 300 chars of body: {r.text[:300]!r}")
    print()


def main() -> None:
    for domain in DOMAINS:
        check(domain)


if __name__ == "__main__":
    main()
