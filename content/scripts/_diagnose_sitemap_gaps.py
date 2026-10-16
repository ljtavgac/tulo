"""One-off: checks the live tulo.io sitemap.xml and homepage canonical tag
for evidence of whether /, /about, /privacy are present, before changing
anything in sitemap.ts.

Usage: python3 content/scripts/_diagnose_sitemap_gaps.py
"""

import re
import sys
import urllib.request

SITEMAP_URL = "https://tulo.io/sitemap.xml"
HOMEPAGE_URL = "https://tulo.io/"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (sitemap-diagnostic)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main() -> None:
    print(f"=== Fetching {SITEMAP_URL} ===")
    sitemap_xml = fetch(SITEMAP_URL)
    urls = re.findall(r"<loc>(.*?)</loc>", sitemap_xml)
    print(f"Total <url> entries: {len(urls)}")

    print("\n--- Checking for homepage / about / privacy ---")
    bare_home = [u for u in urls if u in ("https://tulo.io", "https://tulo.io/")]
    about = [u for u in urls if u.rstrip("/").endswith("/about")]
    privacy = [u for u in urls if u.rstrip("/").endswith("/privacy")]

    print(f"Homepage-like entries found: {bare_home!r}")
    print(f"About-like entries found: {about!r}")
    print(f"Privacy-like entries found: {privacy!r}")

    print("\n--- First 5 and last 5 <loc> entries (for sanity) ---")
    for u in urls[:5]:
        print(f"  {u}")
    print("  ...")
    for u in urls[-5:]:
        print(f"  {u}")

    print(f"\n=== Fetching {HOMEPAGE_URL} ===")
    html = fetch(HOMEPAGE_URL)
    canonical_matches = re.findall(r'<link[^>]*rel=["\']canonical["\'][^>]*>', html)
    print(f"canonical <link> tag(s) found: {canonical_matches}")

    # Also check /about and /privacy respond at all (even though sitemap
    # excludes them by design per sitemap.ts's own comment) -- confirms
    # they're real live routes, not 404s, before we decide whether adding
    # them to the sitemap makes sense.
    for path in ("/about", "/privacy"):
        try:
            code_html = fetch(f"https://tulo.io{path}")
            print(f"\nhttps://tulo.io{path} -- fetched OK, {len(code_html)} bytes")
        except Exception as e:
            print(f"\nhttps://tulo.io{path} -- ERROR: {e}")


if __name__ == "__main__":
    main()
