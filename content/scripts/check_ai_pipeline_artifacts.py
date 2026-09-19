"""One-off diagnostic for the 3 AI-pipeline-artifact items the earlier
"0 AI-writing tells" audit did NOT cover (that audit was content_audit.py's
scan_ai_tells(), which only checks for leftover prompt/completion
boilerplate phrases -- item 1 of 4). This script covers the other three:

2. Generator meta tags -- e.g. <meta name="generator" content="...">
   naming an AI tool/model, in the real rendered HTML.
3. Debug attributes/IDs in production HTML -- data-debug-*, data-testid,
   or LLM-API-shaped IDs (chatcmpl-*, msg_*, req_*, conv_*) leaked either
   as real HTML attributes or as stray text inside page content.
4. Custom response headers identifying the generation pipeline -- prints
   every header actually served so nothing is missed by guessing names.

Fetches real, live frontend pages (not just the backend API) across a
sample of templates, since headers/meta tags are app-wide properties set
in layout.tsx/hosting config -- if they exist at all, they show up on
every page, so a small cross-template sample is representative. Item 3's
content-string half is checked separately, across the FULL corpus, by
regex against every SEED_PAGES string (same walker shape as
content_audit.py's scan_ai_tells).
"""

import json
import os
import re
import sys

import requests

FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "https://tulo.io")

SAMPLE_PAGES = [
    "/",
    "/food/recipes/smoked-haddock-chowder",
    "/food/ingredients/bbq-rub",
    "/food/how-to/how-to-cook-beets",
    "/food/recipes",
    "/about",
]

DEBUG_ID_PATTERNS = [
    ("openai_completion_id", re.compile(r"\bchatcmpl-[A-Za-z0-9]{10,}\b")),
    ("openai_msg_id", re.compile(r"\bmsg_[A-Za-z0-9]{16,}\b")),
    ("anthropic_msg_id", re.compile(r"\bmsg_[A-Za-z0-9]{20,}\b")),
    ("generic_req_id", re.compile(r"\breq_[A-Za-z0-9]{10,}\b")),
    ("generic_conv_id", re.compile(r"\bconv_[A-Za-z0-9]{10,}\b")),
    ("generic_run_id", re.compile(r"\brun_[A-Za-z0-9]{10,}\b")),
    ("uuid_looking", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)),
]

DEBUG_ATTR_RE = re.compile(
    r'\bdata-(?:debug|testid|ai[-_]?\w*|gpt\w*|model\w*|generated\w*|prompt\w*|llm\w*)\s*=\s*"[^"]*"',
    re.IGNORECASE,
)
META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def check_live_pages():
    print("=" * 70)
    print("ITEMS 2 & 4: generator meta tags + response headers (live sample)")
    print("=" * 70)
    any_suspicious = False
    for path in SAMPLE_PAGES:
        url = FRONTEND_BASE_URL.rstrip("/") + path
        print(f"\n--- {url} ---")
        try:
            r = requests.get(url, timeout=20)
        except requests.RequestException as e:
            print(f"  (request failed: {e})")
            continue
        print(f"  status: {r.status_code}")
        print("  response headers:")
        for k, v in r.headers.items():
            print(f"    {k}: {v}")
            if re.search(r"generat|pipeline|model|\bai\b|prompt|llm|gpt|claude|anthropic|openai", f"{k}: {v}", re.I):
                print(f"    ^^^ SUSPICIOUS HEADER")
                any_suspicious = True

        html = r.text
        metas = META_TAG_RE.findall(html)
        print(f"  meta tags found ({len(metas)}):")
        for m in metas:
            print(f"    {m}")
            if re.search(r"generat", m, re.I):
                print(f"    ^^^ generator meta tag present")
                any_suspicious = True

        attrs = DEBUG_ATTR_RE.findall(html)
        if attrs:
            any_suspicious = True
            print(f"  SUSPICIOUS debug-looking attributes found ({len(attrs)}):")
            for a in attrs[:20]:
                print(f"    {a}")
        else:
            print("  no debug-looking data-* attributes found")

        comments = COMMENT_RE.findall(html)
        flagged_comments = [c for c in comments if re.search(r"generat|prompt|model|ai\b|gpt|claude", c, re.I)]
        if flagged_comments:
            any_suspicious = True
            print(f"  SUSPICIOUS HTML comments found ({len(flagged_comments)}):")
            for c in flagged_comments[:10]:
                print(f"    {c[:200]}")

        for label, pattern in DEBUG_ID_PATTERNS:
            hits = pattern.findall(html)
            if hits:
                any_suspicious = True
                print(f"  SUSPICIOUS ID pattern '{label}' found: {hits[:5]}")

    print()
    return any_suspicious


def check_content_corpus():
    print("=" * 70)
    print("ITEM 3 (content half): LLM-API-shaped debug IDs leaked into page copy")
    print("=" * 70)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    from app.seed_templates import SEED_PAGES

    def walk(value, location):
        if isinstance(value, str):
            yield location, value
        elif isinstance(value, dict):
            for k, v in value.items():
                yield from walk(v, f"{location}.{k}")
        elif isinstance(value, list):
            for i, v in enumerate(value):
                yield from walk(v, f"{location}[{i}]")

    hits = []
    for page in SEED_PAGES:
        for location, text in walk(page.get("content", {}), page["slug"]):
            for label, pattern in DEBUG_ID_PATTERNS:
                if label == "uuid_looking":
                    continue  # too many legitimate false positives in prose (e.g. none expected, but skip to be safe)
                m = pattern.search(text)
                if m:
                    hits.append({"slug": page["slug"], "location": location, "pattern": label, "match": m.group(0), "excerpt": text[:160]})

    print(f"Scanned {len(SEED_PAGES)} pages in SEED_PAGES.")
    print(f"Found {len(hits)} leaked debug-ID-shaped string(s) in content.")
    for h in hits[:30]:
        print(f"  {h}")
    print()
    return hits


if __name__ == "__main__":
    suspicious_live = check_live_pages()
    content_hits = check_content_corpus()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Live-sample suspicious findings (headers/meta/attrs/comments/IDs): {'YES -- see above' if suspicious_live else 'none'}")
    print(f"Full-corpus leaked debug-ID strings in content: {len(content_hits)}")

    if suspicious_live or content_hits:
        sys.exit(1)
    sys.exit(0)
