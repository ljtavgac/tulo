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
"""

from __future__ import annotations

import atexit

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


def _fetch_with_browser(url: str, timeout: int) -> str | None:
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
        return page.content()
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
        return _fetch_with_browser(url, timeout=timeout)
    except requests.RequestException:
        return None

    if r.status_code == 200:
        return r.text
    if _looks_like_bot_block(r.status_code, r.text):
        return _fetch_with_browser(url, timeout=timeout)
    return None


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
