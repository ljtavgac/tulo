"""One-off diagnostic: investigating Search Console's new "Alternate page
with proper canonical tag" status. That status specifically means Google
fetched a page (200 OK) whose <link rel="canonical"> points to a DIFFERENT
URL, and deferred to it -- it is NOT the same thing as "Page with redirect"
(a 3xx response), which is what the duplicate-cleanup's redirect_to
mechanism actually produces (see backend/app/main.py's GET /redirects and
frontend/next.config.mjs). This script gets real evidence to tell the two
apart, against the live production site, rather than guessing from code
alone:

1. Pulls the live GET /redirects list (the real, current redirect_to count,
   cross-referenced against the reported ~110/83/27 figures).
2. For a sample of those redirect sources, fetches the PRODUCTION FRONTEND
   URL directly with redirects disabled, to confirm the real HTTP status
   code and Location header (expect 308, not 200).
3. For a sample of ordinary (non-redirect_to) published pages, fetches the
   real rendered HTML and extracts the <link rel="canonical"> tag, to
   confirm it self-references (and check the domain/protocol used).
4. Probes one page with a query-string variant and one with a trailing
   slash, to check for the other, more mundane explanations Search
   Console's status commonly covers (tracking-parameter or slash
   normalization) -- both benign/expected if that's what's happening.

Usage:
    BACKEND_BASE_URL=https://your-prod-backend \
    FRONTEND_BASE_URL=https://tulo.io \
    python3 content/scripts/diagnose_canonical_tags.py
"""

from __future__ import annotations

import os
import re

import requests

BACKEND_BASE_URL = os.environ["BACKEND_BASE_URL"].rstrip("/")
FRONTEND_BASE_URL = os.environ["FRONTEND_BASE_URL"].rstrip("/")

CANONICAL_RE = re.compile(r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"[^>]*/?>', re.IGNORECASE)


def _get_redirects() -> list[dict]:
    r = requests.get(f"{BACKEND_BASE_URL}/redirects", timeout=30)
    r.raise_for_status()
    return r.json()


def _check_redirect_source(path: str) -> None:
    url = f"{FRONTEND_BASE_URL}{path}"
    try:
        r = requests.get(url, timeout=20, allow_redirects=False)
    except requests.RequestException as e:
        print(f"    ERROR fetching {url}: {e}")
        return
    location = r.headers.get("Location", "")
    print(f"    GET {path} -> HTTP {r.status_code}, Location: {location!r}")
    if r.status_code == 200:
        m = CANONICAL_RE.search(r.text)
        canon = m.group(1) if m else "(none found)"
        print(f"      *** 200 OK, not a redirect -- canonical tag: {canon!r} ***")


def _check_ordinary_page(path: str) -> None:
    url = f"{FRONTEND_BASE_URL}{path}"
    try:
        r = requests.get(url, timeout=20, allow_redirects=False)
    except requests.RequestException as e:
        print(f"    ERROR fetching {url}: {e}")
        return
    m = CANONICAL_RE.search(r.text) if r.status_code == 200 else None
    canon = m.group(1) if m else None
    # Compare against the clean (no query string, no trailing slash) self
    # URL -- a canonical correctly pointing to that clean form on a
    # query-param or trailing-slash variant request is the expected,
    # benign case Search Console's status commonly covers, not a bug.
    clean_self_url = f"{FRONTEND_BASE_URL}{path.split('?')[0].rstrip('/') or '/'}"
    if canon is None:
        note = "NO CANONICAL FOUND"
    elif canon == clean_self_url:
        note = "matches clean self URL (expected/benign if this was a variant request)"
    elif canon == url:
        note = "exact self-match"
    else:
        note = "*** POINTS SOMEWHERE ELSE -- NOT the clean self URL ***"
    print(f"    GET {path} -> HTTP {r.status_code}, canonical: {canon!r} [{note}]")


def main() -> None:
    print(f"Backend:  {BACKEND_BASE_URL}")
    print(f"Frontend: {FRONTEND_BASE_URL}\n")

    redirects = _get_redirects()
    print(f"=== GET /redirects: {len(redirects)} active redirect_to pair(s) (live, right now) ===")
    for pair in redirects[:10]:
        print(f"  {pair['source']} -> {pair['destination']}")
    if len(redirects) > 10:
        print(f"  ... and {len(redirects) - 10} more")
    print()

    print("=== Sampling 5 redirect sources against the live frontend (redirects disabled) ===")
    for pair in redirects[:5]:
        _check_redirect_source(pair["source"])
    print()

    print("=== Sampling a few ordinary published pages for canonical self-reference ===")
    ordinary_paths = ["/", "/food/recipes", "/food/ingredients"]
    for path in ordinary_paths:
        _check_ordinary_page(path)
    print()

    if redirects:
        # Use a real, currently-published destination page (not a
        # redirect_to source) as the query-param/trailing-slash probe target.
        probe_path = redirects[0]["destination"]
        print(f"=== Probing {probe_path} for query-param and trailing-slash canonicalization ===")
        _check_ordinary_page(probe_path)
        _check_ordinary_page(f"{probe_path}?utm_source=diagnostic_test")
        _check_ordinary_page(f"{probe_path}/")


if __name__ == "__main__":
    main()
