"""Shared HTML fetch helper for the outreach-sourcing scripts
(daily_outreach_sourcing.py, broken_link_outreach.py,
unlinked_mention_outreach.py, resource_page_outreach.py,
roundup_inclusion_outreach.py, backlink_gap_outreach.py) -- deliberately
the one piece of logic those otherwise-standalone scripts share, since a
Playwright browser fallback is too much real logic to safely keep in sync
copy-pasted six ways (unlike the two-line requests.get() wrapper it
replaces, which each script is free to keep duplicating for everything
else).

fetch(url) tries a plain requests.get() first (cheap, works for the large
majority) and only falls back to a headless-Chromium Playwright fetch when
the response looks like a bot-management challenge -- a 403/429/503, a
redirect loop, or a known challenge-page marker in the body -- rather than
a genuine failure. That distinction is confirmed against real, live
examples via content/scripts/diagnose_homepage_fetch_failures.py's run on
2026-09-24: damndelicious.net/diethood.com/rasamalaysia.com/
shugarysweets.com (Cloudflare's "Just a moment" interstitial),
foodnetwork.com (Akamai "Access Denied"), food52.com (Vercel "Security
Checkpoint"), thewoksoflife.com (a bot-detection redirect loop) were all
live, ordinary domains that a bare requests.get() couldn't reach. A real
DNS failure, connection refused, or ordinary 404/500 skips the fallback
entirely -- no point spending a browser launch on a site that's actually
down.

Some of these blocks (particularly Cloudflare's) are known to sometimes
key off IP reputation rather than just JS execution -- a GitHub Actions
runner is a datacenter IP, so this fallback is expected to recover a real
share of today's failures, not all of them. That's a known, accepted
limitation, not a bug: see the sizing conversation this was built from.

The Playwright browser is launched lazily (only the first time a fallback
is actually needed) and reused across every fetch() call in the process,
since a fresh browser launch per domain would be needlessly slow. Each
script's own process exit runs close() via the atexit hook registered
here, so no caller needs to remember to clean up.

fetch_working_page(url) is a stricter sibling for one specific case: each
script's _contact_form_url() guesses a candidate's /contact or
/contact-us path and, until now, accepted ANY 200 response as proof a
real contact page exists there -- which is wrong two common ways,
confirmed by the user reporting queued prospects whose contact-form link
actually 404s or shows a "page doesn't exist" message: (1) a silent
redirect to the homepage (or anywhere else) when the guessed path
doesn't exist -- requests follows redirects by default, so the response
is a real 200, just not of the page that was asked for; (2) a "soft
404" -- 200 status with a body that says "Page Not Found" (extremely
common on page-builder/SPA sites with no real server-side 404 handling,
or a themed 404 template served without the matching status code).
fetch_working_page() returns None for either case, so a human is never
handed a dead link to paste a pitch into.

extract_mailto_emails(html) closes a real gap confirmed live on
2026-09-25 (see content/scripts/diagnose_mailto_extraction_gap_20260925.py):
every script's _page_text() strips a page down to visible text via
BeautifulSoup's get_text(), which drops every HTML attribute -- including
a <a href="mailto:x@y.com"> link's actual address when the visible anchor
text is just "Contact us" or an icon. The vetting model is only ever given
that stripped text, so a real address sitting in a mailto href is
invisible to it; if it reports an address anyway (a plausible guess, or
general knowledge), the existing "claimed contact_email not verified
against fetched page text" check correctly rejects it -- confirmed live:
2 of 10 sampled "claimed but unverified" candidates from the same run
(brooklynsupper.com, thefullhelping.com) had a real mailto: address
sitting in the raw HTML of a page already fetched for that same
candidate the whole time. Extracting it directly from the markup, rather
than asking the model to find or repeat it, needs no separate
verification step at all -- the address came from the target domain's
own page source, which is the strongest evidence this pipeline accepts
anywhere.
"""

from __future__ import annotations

import atexit
import re
from urllib.parse import urlsplit

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

BOT_BLOCK_STATUS_CODES = {403, 429, 503}

# Confirmed against real challenge pages (see module docstring) rather than
# guessed -- covers Cloudflare's interstitial, Akamai's block page, and
# Vercel's checkpoint.
BOT_BLOCK_MARKERS = [
    "just a moment",
    "attention required",
    "captcha",
    "cloudflare",
    "access denied",
    "are you a human",
    "enable javascript and cookies",
    "please verify you are a human",
    "checking your browser",
    "security checkpoint",
]

# Common soft-404 phrasing -- a real page-not-found message rendered with
# an HTTP 200 rather than a real 404 status. Deliberately phrase-level
# (not just "404", which shows up in plenty of real page furniture like
# CSS class names or a phone number) and deliberately not exhaustive --
# this only needs to catch the common cases, since fetch_working_page()'s
# other check (a guessed path that silently redirects elsewhere) covers
# the single biggest share of dead contact-form links on its own.
NOT_FOUND_MARKERS = [
    "page not found",
    "404 error",
    "404 not found",
    "this page doesn't exist",
    "this page does not exist",
    "we can't find that page",
    "we can't seem to find",
    "can't find the page",
    "couldn't find that page",
    "could not find that page",
    "the page you are looking for",
    "the page you're looking for",
    "content not found",
    "nothing found",
    "page cannot be found",
    "page can't be found",
    "oops! that page",
    "sorry, but the page",
    "sorry, that page",
]

_browser = None
_playwright_ctx = None


def _looks_like_bot_block(status_code: int | None, body: str | None) -> bool:
    if status_code is not None and status_code in BOT_BLOCK_STATUS_CODES:
        return True
    if body:
        low = body.lower()
        if any(marker in low for marker in BOT_BLOCK_MARKERS):
            return True
    return False


def _get_browser():
    global _browser, _playwright_ctx
    if _browser is None:
        from playwright.sync_api import sync_playwright

        _playwright_ctx = sync_playwright().start()
        _browser = _playwright_ctx.chromium.launch()
    return _browser


def _fetch_with_browser(url: str, timeout: int) -> tuple[str, str] | None:
    """Returns (html, final_url) -- final_url matters to callers that care
    whether the page silently redirected elsewhere (see
    fetch_working_page())."""
    try:
        browser = _get_browser()
    except Exception:
        # Playwright/Chromium not installed in this environment -- fail
        # closed exactly like the old behavior rather than crashing the
        # whole script over a fallback path.
        return None
    page = None
    try:
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
        # Cloudflare's lightweight "Just a moment" interstitial typically
        # clears itself client-side within a few seconds -- give it a beat
        # rather than waiting on a fixed challenge-page selector that could
        # change at any time.
        page.wait_for_timeout(4000)
        return page.content(), page.url
    except Exception:
        return None
    finally:
        if page is not None:
            page.close()


def fetch(url: str, timeout: int = 20) -> str | None:
    """Fetch url's HTML. Tries a plain request first; falls back to a
    headless-browser fetch only when the response looks like a bot-
    management challenge rather than a genuine failure. Returns None if
    the site is genuinely unreachable, or if both attempts fail."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
    except requests.TooManyRedirects:
        # A redirect loop is itself one of the bot-block signatures seen in
        # practice (thewoksoflife.com) -- worth the browser retry rather
        # than a hard failure.
        result = _fetch_with_browser(url, timeout=timeout)
        return result[0] if result else None
    except requests.RequestException:
        return None

    if r.status_code == 200:
        return r.text
    if _looks_like_bot_block(r.status_code, r.text):
        result = _fetch_with_browser(url, timeout=timeout)
        return result[0] if result else None
    return None


def _normalize_host(host: str) -> str:
    # A bare-domain <-> www. redirect is near-universal (HTTPS
    # canonicalization, not a sign the guessed path doesn't exist) and must
    # not itself count as "redirected elsewhere".
    return host.lower().removeprefix("www.")


def _is_dead_page(html: str, requested_url: str, final_url: str) -> bool:
    # A silent redirect to the homepage (or anywhere else) means the
    # guessed path doesn't actually exist on this site -- but a plain
    # scheme/www canonicalization redirect to the SAME path is normal and
    # must not be flagged. Compares host (www-normalized) and path
    # (trailing-slash-tolerant) separately; query/fragment never matter.
    req = urlsplit(requested_url)
    fin = urlsplit(final_url)
    if _normalize_host(req.netloc) != _normalize_host(fin.netloc):
        return True
    if req.path.rstrip("/") != fin.path.rstrip("/"):
        return True
    low = html.lower()
    return any(marker in low for marker in NOT_FOUND_MARKERS)


def fetch_working_page(url: str, timeout: int = 10) -> bool:
    """True only if url resolves to a real, reachable page at that exact
    path -- not a silent redirect elsewhere and not a soft-404 body. Bot-
    block detection and the headless-browser fallback still apply
    underneath (a genuinely bot-blocked contact page gets the same retry
    as any other fetch()), but a challenge page that never actually
    cleared is itself treated as not-working via the same NOT_FOUND/
    BOT_BLOCK marker check, since a human would see the same "just a
    moment" screen forever."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
    except requests.TooManyRedirects:
        result = _fetch_with_browser(url, timeout=timeout)
        if result is None:
            return False
        html, final_url = result
        return not _is_dead_page(html, url, final_url) and not _looks_like_bot_block(None, html)
    except requests.RequestException:
        return False

    if r.status_code == 200:
        return not _is_dead_page(r.text, url, r.url)
    if _looks_like_bot_block(r.status_code, r.text):
        result = _fetch_with_browser(url, timeout=timeout)
        if result is None:
            return False
        html, final_url = result
        return not _is_dead_page(html, url, final_url) and not _looks_like_bot_block(None, html)
    return False


# Junk addresses that technically match href="mailto:..." but are never a
# real contact -- a placeholder left in a theme/template, not a real
# person or inbox at the candidate's own domain.
_MAILTO_JUNK = {"email@example.com", "your@email.com", "name@example.com", "example@example.com"}

_MAILTO_RE = re.compile(r'href=["\']mailto:([^"\'?]+)', re.IGNORECASE)


def extract_mailto_emails(html: str) -> list[str]:
    """Pulls every real mailto: address out of a page's raw HTML -- see
    the module docstring for why this exists. Must run against the raw
    HTML a fetch() call returned, before any caller strips it down to
    plain text; a stripped-text caller never had this information to
    begin with. Order-preserving, de-duplicated, case-normalized, with
    obvious placeholder addresses filtered out."""
    seen: list[str] = []
    for raw in _MAILTO_RE.findall(html):
        email = raw.strip().lower()
        if not email or email in _MAILTO_JUNK or email in seen:
            continue
        seen.append(email)
    return seen


def close() -> None:
    global _browser, _playwright_ctx
    if _browser is not None:
        try:
            _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright_ctx is not None:
        try:
            _playwright_ctx.stop()
        except Exception:
            pass
        _playwright_ctx = None


atexit.register(close)
