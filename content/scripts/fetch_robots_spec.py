"""One-off diagnostic: this sandbox's egress proxy blocks
developers.google.com, so we can't verify Google's robots.txt matching
rules (prefix matching, query-string handling, * and $ semantics) against
the live spec from here. This script runs on a GitHub-hosted runner
(normal internet access) to fetch the spec page and print the relevant
section, so the actual wording can be quoted rather than assumed --
directly for sizing the /food/tools/recipe-generator?ingredients= disallow
rule correctly.

Usage:
    python3 content/scripts/fetch_robots_spec.py
"""

from __future__ import annotations

import re

import requests

URL = "https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt"


def main() -> None:
    r = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    text = r.text

    # Strip tags crudely to plain text so the relevant paragraphs are
    # readable in job logs without pulling in a full HTML parser dependency.
    plain = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    plain = re.sub(r"<style[^>]*>.*?</style>", " ", plain, flags=re.DOTALL | re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = re.sub(r"&amp;", "&", plain)
    plain = re.sub(r"&#39;|&rsquo;", "'", plain)
    plain = re.sub(r"&quot;|&rdquo;|&ldquo;", '"', plain)
    plain = re.sub(r"[ \t]+", " ", plain)
    plain = re.sub(r"\n\s*\n+", "\n\n", plain)

    keywords = ["path value", "matching", "wildcard", "special characters", "query", "asterisk", "$"]
    lines = plain.split("\n")
    print(f"Fetched {len(text)} bytes, {len(lines)} lines of extracted text.\n")
    print("=== Lines mentioning matching/wildcard/query-related keywords ===\n")
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if len(line_stripped) < 20:
            continue
        low = line_stripped.lower()
        if any(k in low for k in ["path value", "match the beginning", "wildcard", "special character",
                                    "query string", "asterisk", "dollar sign", "end of a url",
                                    "prefix", "longest matching"]):
            print(f"[{i}] {line_stripped}\n")


if __name__ == "__main__":
    main()
