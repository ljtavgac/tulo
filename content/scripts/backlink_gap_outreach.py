"""Backlink-gap outreach sourcing: finds real domains that already link to
one of Tulo's direct competitors (see COMPETITOR_DOMAINS below) but do not
already link to tulo.io, then runs them through the same credibility
vetting, contact-email discovery, and pitch-drafting pipeline as
daily_outreach_sourcing.py. This is a much better-qualified candidate pool
than daily_outreach_sourcing.py's blind "best food blogs" directory crawl:
every candidate here has already demonstrated, by actually linking to a
comparable competitor, that it's the kind of site that links out to
food/cooking resources -- not just any domain that happened to appear on a
roundup page.

CURRENTLY NOT WIRED INTO daily-link-building.yml: this script needs its
own SEMRUSH_API_KEY as a GitHub Actions secret to make the classic
Semrush Analytics REST calls below, and none is configured. Update as of
2026-09-20: the account DOES now have working Semrush access (confirmed
live via the account's Semrush MCP connector -- real backlink data
returned for tulo.io and several competitors) -- the missing piece is
specifically a raw API key usable from an unattended CI runner, which is
a separate credential from that connector and can't be extracted from
it. Add a SEMRUSH_API_KEY secret (from the same Semrush account/plan the
MCP connector uses) and re-add this as daily-link-building.yml's first
step (see that workflow's own comment) to turn it back on; it was
designed to run first since it should be the best-qualified candidate
pool of the six once real data is flowing.

Discovery mechanism: Semrush's Backlink Analytics API (backlinks_refdomains
report) -- the one part of this script that could not be verified against
Semrush's live API documentation before shipping (this sandbox's network
egress to developer.semrush.com is blocked, and no test API key was
available here). Confirmed live so far: a request with no valid key
returns a plain HTTP 400 (caught fine by the existing requests.
RequestException handling below) rather than a 200-with-"ERROR"-text
response -- but the actual response *shape* on a genuinely successful
call (column names, delimiter) is still unverified, since that requires a
real key. _fetch_referring_domains() below is written from the
well-established classic Semrush Analytics API shape (semicolon-delimited
CSV response, "ERROR ..." line on failure) -- but if Semrush has since
changed that shape, this function will raise loudly with the raw response
body rather than silently returning zero candidates every day. Treat this
script's first real run as a live verification, not just a dry-run.

Shares the SAME daily queue quota as every other automated outbound
sourcing script (see DAILY_QUEUE_CAP / _remaining_daily_quota below) --
running this alongside daily_outreach_sourcing.py and the other new
discovery scripts does not multiply the daily total, it divides it,
priority-first.

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    PIPELINE_ANTHROPIC_API_KEY=... SEMRUSH_API_KEY=... \
    python3 content/scripts/backlink_gap_outreach.py [--dry-run]

--dry-run prints what would be queued without ever calling
/admin/outreach-queue/create.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from outreach_fetch import extract_mailto_emails as _extract_mailto_emails
from outreach_fetch import fetch as _shared_fetch
from outreach_fetch import fetch_working_page as _shared_fetch_working_page

# Real, direct competitors in the recipe/food-content space -- domains
# whose own backlink profile is a genuine signal of "sites that link to
# food/cooking resources like Tulo's," unlike a generic directory crawl.
# Add more here as real competitors are identified; each one costs one
# extra Semrush API call per run.
COMPETITOR_DOMAINS = [
    "allrecipes.com",
    "browneyedbaker.com",
    "simplyrecipes.com",
    "seriouseats.com",
    "thekitchn.com",
    "food52.com",
]

TULO_DOMAIN = "tulo.io"

# Confirmed live via the Semrush MCP connector (2026-09-20, ahead of this
# script's first real automated run): sorting a competitor's referring
# domains by authority score descending -- exactly what `candidates` below
# does -- surfaces almost nothing but mega-publishers and aggregators
# (cnn.com, nytimes.com, wikipedia.org, huffpost.com, bing.com, ...) all
# the way down past the top few hundred rows for a site with a backlink
# profile as large as allrecipes.com's. None of those are realistic cold-
# outreach targets for a small tools link -- a real editor there would
# never respond, and Tulo isn't going to appear in a publication of that
# size's contact-page-listed inbox. Without this ceiling, evaluating in
# score-descending order means every run spends its earliest, most-
# competitor-corroborated evaluation slots on exactly the domains least
# likely to convert, crowding out the genuine small/mid-tier blogs this
# source exists to find. No floor is applied -- the existing credibility
# check already screens out spam/PBN-tier sites regardless of score.
MAX_AUTHORITY_SCORE = 65

# Same generic-platform exclusion list as daily_outreach_sourcing.py --
# duplicated on purpose (see that script's own note on why these scripts
# don't share a package).
EXCLUDED_DOMAIN_SUFFIXES = {
    "wordpress.com", "wordpress.org", "blogspot.com", "blogger.com",
    "pinterest.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "youtu.be", "amazon.com", "amzn.to", "wikipedia.org",
    "medium.com", "tumblr.com", "reddit.com", "quora.com", "linkedin.com",
    "tiktok.com", "threads.net", "google.com", "goo.gl", "bit.ly",
    "apple.com", "feedburner.com", "mailchimp.com", "bloglovin.com",
    "feedspot.com", "similarweb.com", "semrush.com", "ahrefs.com", "moz.com",
    "tulo.io",
}
EXCLUDED_DOMAIN_SUFFIXES.update(COMPETITOR_DOMAINS)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TULO_TOOLS = [
    {
        "name": "Kitchen Conversion Calculator",
        "url": "https://tulo.io/food/tools/conversion-calculator",
        "description": "Converts cups, tablespoons, grams, ounces, and oven temperatures between US and metric.",
    },
    {
        "name": "Cooking Time & Temperature Guide",
        "url": "https://tulo.io/food/tools/time-temperature-guide",
        "description": "Cook times and temps by protein/method (oven, air fryer, grill), plus USDA safe minimum internal temperatures.",
    },
    {
        "name": "Custom Recipe Generator",
        "url": "https://tulo.io/food/tools/recipe-generator",
        "description": "Generates a recipe idea from whatever ingredients a reader already has in their kitchen.",
    },
]

MODEL = "claude-sonnet-5"
MAX_TOOL_TURNS = 12
DAILY_QUEUE_CAP = 50  # shared across every automated outbound sourcing script -- see module docstring

SEARCH_TULO_CONTENT_TOOL = {
    "name": "search_tulo_content",
    "description": (
        "Searches Tulo's real, live content pages -- recipes, ingredient guides, cooking how-tos, "
        "definitions, comparisons, substitute guides, collections -- by title keyword. Returns real "
        "{slug, title, template_type, url} matches (up to 6), or an empty list if nothing matches. "
        "This is the ONLY way to find or verify a page beyond the three fixed tools already given: "
        "never recommend a URL that wasn't returned by this tool or listed among the fixed tools."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Title keywords to search for, e.g. 'chicken' or 'baking soda'"},
        },
        "required": ["query"],
    },
}

WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 3,
}


def _root_domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc.split(":")[0]


# Known company rebrand/legacy-domain aliases -- domain-string dedup can't
# tell these are the same real organization as their current domain, so a
# candidate found under an old domain slips past seen_domains untouched.
# Real incident (2026-09-23): kingarthurflour.com's blog got queued as a
# "new" candidate three days after kingarthurbaking.com -- the company's
# current domain -- was already contacted (a 2020 rebrand, both domains
# still live). Only added reactively, when a real collision like this is
# found -- not meant to be a general solution to every possible rebrand.
KNOWN_DOMAIN_ALIASES = {
    "kingarthurflour.com": "kingarthurbaking.com",
}


def _canonical_domain(domain: str) -> str:
    for alias, canonical in KNOWN_DOMAIN_ALIASES.items():
        if domain == alias or domain.endswith("." + alias):
            return canonical
    return domain


def _extract_json_object(raw: str) -> dict | None:
    """The system prompt says respond with ONLY a JSON object, but a raw-
    output diagnostic (2026-09-20, against real live failures) found the
    model sometimes prepends a closing thought first -- e.g. "Found the
    email on the \'Work with Me\' page..." then the JSON, occasionally
    still wrapped in a fence -- rather than ever truncating (every real
    failure had stop_reason == "end_turn" well under the token budget).
    The old fence-strip only handled a fence anchored at position 0, so
    any leading prose defeated it outright. Tries, in order: the raw
    string as-is, a fenced block found ANYWHERE in the string, then the
    first-\'{\'-to-last-\'}\' slice -- the JSON object is always the last
    thing emitted in every observed failure."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _is_excluded(domain: str) -> bool:
    return any(domain == suf or domain.endswith("." + suf) for suf in EXCLUDED_DOMAIN_SUFFIXES)


def _fetch(url: str, timeout: int = 20) -> str | None:
    """Delegates to outreach_fetch.fetch(): plain request first, falls back
    to a headless-browser fetch only when the response looks like a bot-
    management challenge rather than a genuine failure -- see that
    module's docstring for the real examples this was built from."""
    return _shared_fetch(url, timeout=timeout)


def _page_text(html: str, max_chars: int = 6000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text[:max_chars]


CONTACT_PAGE_PATHS = [
    "/contact", "/contact-us", "/about", "/about-us", "/privacy-policy",
    "/privacy", "/media-kit", "/press", "/advertise", "/work-with-me",
    "/write-for-us",
]
MAX_CONTACT_PAGES_FETCHED = 4


def _contact_page_text(domain: str, max_chars_per_page: int = 1500) -> tuple[str, list[str]]:
    """Also returns any mailto: addresses found in the raw HTML of these
    pages (see outreach_fetch.extract_mailto_emails) -- real addresses a
    vetting model given only stripped page text could never see for
    itself."""
    found = []
    mailtos: list[str] = []
    for path in CONTACT_PAGE_PATHS:
        if len(found) >= MAX_CONTACT_PAGES_FETCHED:
            break
        html = _fetch(f"https://{domain}{path}", timeout=10)
        if html is not None:
            found.append(f"--- {path} ---\n{_page_text(html, max_chars_per_page)}")
            for email in _extract_mailto_emails(html):
                if email not in mailtos:
                    mailtos.append(email)
    return "\n\n".join(found), mailtos


CONTACT_FORM_PATHS = ["/contact", "/contact-us"]


def _contact_form_url(domain: str) -> str | None:
    """Only checked when a credible candidate has no findable email (see
    the no-email branch in main()) -- tries just the two paths that are
    actually likely to be a submission form, unlike the broader
    about/privacy/media-kit pages _contact_page_text also checks (those
    are for finding an email in prose, not a form to fill out). Lets a
    human paste the drafted pitch in by hand instead of dropping an
    otherwise-credible candidate outright. Verified via
    outreach_fetch.fetch_working_page() -- not just any 200 response --
    since a guessed path silently redirecting to the homepage, or a soft
    404 (200 status, "page not found" body), used to slip through as if
    it were a real contact page."""
    for path in CONTACT_FORM_PATHS:
        url = f"https://{domain}{path}"
        if _shared_fetch_working_page(url, timeout=10):
            return url
    return None


def _fetch_referring_domains(target: str, api_key: str, display_limit: int = 300) -> dict[str, float]:
    """Classic Semrush Analytics API, backlinks_refdomains report: every
    referring domain pointing to `target`, with its Semrush domain
    Authority Score. Returns {domain: authority_score}. Raises RuntimeError
    with the raw response body on anything that doesn't parse as the
    expected semicolon-delimited CSV -- see the module docstring on why
    this is the one part of the script that needs a live first-run check."""
    resp = requests.get(
        "https://api.semrush.com/analytics/v1/",
        params={
            "key": api_key,
            "type": "backlinks_refdomains",
            "target": target,
            "target_type": "root_domain",
            "export_columns": "domain,ascore",
            "display_limit": display_limit,
        },
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.text.strip()
    if not text or text.startswith("ERROR"):
        raise RuntimeError(f"Semrush backlinks_refdomains({target}) failed: {text[:300]}")

    lines = text.splitlines()
    header = [h.strip().lower() for h in lines[0].split(";")]
    if "domain" not in header:
        raise RuntimeError(f"Semrush backlinks_refdomains({target}) unexpected response shape: {text[:300]}")
    domain_idx = header.index("domain")
    score_idx = header.index("ascore") if "ascore" in header else None

    out: dict[str, float] = {}
    for line in lines[1:]:
        cols = line.split(";")
        if len(cols) <= domain_idx:
            continue
        domain = cols[domain_idx].strip().lower()
        if not domain:
            continue
        score = 0.0
        if score_idx is not None and len(cols) > score_idx:
            try:
                score = float(cols[score_idx].strip())
            except ValueError:
                score = 0.0
        out[domain] = score
    return out


def _existing_domains_and_emails(base: str, auth: tuple[str, str]) -> tuple[set[str], set[str]]:
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=30)
    r.raise_for_status()
    rows = r.json()
    domains = {_canonical_domain(row["target_domain"].lower()) for row in rows}
    emails = {row["contact_email"].strip().lower() for row in rows if (row.get("contact_email") or "").strip()}
    return domains, emails


def _remaining_daily_quota(base: str, auth: tuple[str, str], cap: int = DAILY_QUEUE_CAP) -> int:
    """Every automated outbound sourcing script (this one, the hub-page
    crawl, roundup targeting, broken-link, unlinked-mention, resource-page)
    draws from one shared daily budget of `cap` newly-queued prospects, not
    `cap` each. Counts today's (UTC) already-created tool_pitch/
    content_pitch rows -- haro_reply is a separate, inbound-triggered
    pipeline, not part of this outbound daily budget -- and returns what's
    left for this run to use."""
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=30)
    r.raise_for_status()
    today = datetime.now(timezone.utc).date()
    created_today = 0
    for row in r.json():
        if row.get("pitch_type") not in ("tool_pitch", "content_pitch"):
            continue
        created_at = row.get("created_at")
        if not created_at:
            continue
        try:
            if datetime.fromisoformat(created_at).date() == today:
                created_today += 1
        except ValueError:
            continue
    return max(0, cap - created_today)


def _http_search_tulo_content(base: str, query: str, limit: int = 6) -> list[dict]:
    if not query.strip():
        return []
    r = requests.get(
        f"{base}/pages",
        params={"q": query.strip(), "paged": "true", "limit": limit},
        timeout=30,
    )
    if not r.ok:
        return []
    routes = {
        "recipe_or_dish": "recipes", "ingredient_hub": "ingredients", "howto_technique": "how-to",
        "definition": "what-is", "comparison": "comparisons", "substitute": "substitutes",
        "category_roundup": "collections",
    }
    results = []
    for item in r.json().get("items", []):
        template_type = item["template_type"]
        if template_type not in routes:
            continue
        results.append(
            {
                "slug": item["slug"],
                "title": item["title"],
                "template_type": template_type,
                "url": f"https://tulo.io/food/{routes[template_type]}/{item['slug']}",
            }
        )
    return results


def _vet_and_draft(client, base: str, domain: str, homepage_text: str, competitors: list[str]) -> dict | None:
    """Same vetting/drafting/invariant-enforcement shape as
    daily_outreach_sourcing.py's _vet_and_draft -- duplicated rather than
    imported, per this project's standalone-script convention."""
    from anthropic import Anthropic  # noqa: F401

    tools_block = "\n".join(f"- {t['name']}: {t['description']} ({t['url']})" for t in TULO_TOOLS)
    system_prompt = (
        "You vet cold-outreach candidates for Tulo, a free food/recipe website building genuine, "
        "editorial backlinks -- never a link farm or PBN itself, and only interested in linking from "
        "real ones either.\n\n"
        f"This candidate was found because it already links to {', '.join(competitors)} -- a real "
        "competitor of Tulo's -- which is a strong signal it's a genuine food/cooking site that links "
        "out to resources like this, but you must still independently judge it from the page text "
        "below: a genuine author voice or byline, evidence of a real audience, original writing that "
        "reads as human-written, a real About/Contact section. Reject generic content aggregators, "
        "thin affiliate-only sites, obviously auto-generated text, or anything that isn't actually "
        "about food/cooking/recipes -- linking to a competitor doesn't excuse a bad site.\n\n"
        "Tulo has three fixed, always-real tools:\n"
        f"{tools_block}\n\n"
        "Tulo also has thousands of individual content pages -- recipes, ingredient guides, cooking "
        "how-tos, definitions, comparisons, substitute guides. Use the search_tulo_content tool to "
        "check for one genuinely relevant to this specific site's focus before recommending it; never "
        "guess or invent a slug/URL for one of these, only the search tool's real results are safe to "
        "use. If nothing specific fits, use one of the three fixed tools instead.\n\n"
        "Contact email: the text you're given (homepage plus any Contact/About/privacy/media-kit pages "
        "that were reachable) often doesn't contain a real email, even for a genuinely credible site. "
        "If you don't see one, use the web_search tool (up to 3 searches) ONLY to look for that same "
        "domain's own published contact email. If you find one, report it as contact_email AND set "
        "contact_email_source_url to the exact page URL where you found it -- both required together. "
        "If you can't find a genuine address either way, set both to null; this never affects the "
        "credible verdict.\n\n"
        "Once decided, respond with ONLY a JSON object (no prose, no markdown fences, no further tool "
        "calls) with exactly these keys: credible (boolean), reason (one sentence), contact_email "
        "(per the rules above, else null), contact_email_source_url (else null), subject, body (a "
        "short, specific, non-generic 3-5 sentence pitch mentioning something concrete from this "
        "specific site plus exactly one real URL - from the fixed tools list or a search_tulo_content "
        "result, never invented; use a single hyphen with spaces around it for a dash, never an em "
        "dash). If credible is false, subject/body/contact_email/contact_email_source_url may be null."
    )

    allowed_urls = {t["url"] for t in TULO_TOOLS}
    messages: list[dict] = [{"role": "user", "content": f"Candidate domain: {domain}\n\nHomepage text:\n{homepage_text}"}]
    response = None
    for _ in range(MAX_TOOL_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system_prompt,
            tools=[SEARCH_TULO_CONTENT_TOOL, WEB_SEARCH_TOOL],
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            break
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            results = _http_search_tulo_content(base, block.input.get("query", "")) if block.name == "search_tulo_content" else []
            allowed_urls.update(r["url"] for r in results)
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(results)})
        messages.append({"role": "user", "content": tool_results})
    else:
        print(f"  {domain}: exceeded {MAX_TOOL_TURNS} tool-use turns, skipping")
        return None

    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    item = _extract_json_object(raw)
    if item is None:
        print(f"  {domain}: model response wasn't valid JSON, skipping (raw: {raw[:200]!r})")
        return None

    if not item.get("credible"):
        print(f"  {domain}: rejected -- {item.get('reason', 'no reason given')}")
        return None

    body = item.get("body") or ""
    if not any(url in body for url in allowed_urls):
        print(f"  {domain}: dropped -- credible but no real Tulo URL in drafted body")
        return None

    contact_email = (item.get("contact_email") or "").strip() or None
    source_url = (item.get("contact_email_source_url") or "").strip() or None
    if contact_email:
        verified = contact_email in homepage_text
        if not verified and source_url:
            source_domain = _root_domain(source_url)
            if source_domain == domain or source_domain.endswith("." + domain):
                source_html = _fetch(source_url, timeout=10)
                if source_html is not None:
                    verified = contact_email in _page_text(source_html, max_chars=4000)
        if not verified:
            print(f"  {domain}: claimed contact_email not verified against fetched page text, dropping email only")
            contact_email = None

    return {
        "target_domain": domain,
        "contact_email": contact_email,
        "subject": item.get("subject") or "",
        "body_preview": body,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--count", type=int, default=None,
        help="Cap how many to queue this run (default: use the full shared daily quota remaining)",
    )
    args = parser.parse_args()

    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    semrush_key = os.environ["SEMRUSH_API_KEY"]

    remaining = _remaining_daily_quota(base, auth)
    if args.count is not None:
        remaining = min(remaining, args.count)
    print(f"Shared daily quota: {remaining} slot(s) remaining today.")
    if remaining <= 0:
        print("Daily quota already reached by an earlier sourcing step today -- nothing to do.")
        return

    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["PIPELINE_ANTHROPIC_API_KEY"])

    print(f"\nPulling referring domains for {len(COMPETITOR_DOMAINS)} competitor(s) via Semrush...")
    overlap: dict[str, set[str]] = {}
    scores: dict[str, float] = {}
    for competitor in COMPETITOR_DOMAINS:
        try:
            refdomains = _fetch_referring_domains(competitor, semrush_key)
        except (requests.RequestException, RuntimeError) as exc:
            print(f"  {competitor}: Semrush lookup failed, skipping this competitor -- {exc}")
            continue
        print(f"  {competitor}: {len(refdomains)} referring domain(s)")
        for domain, score in refdomains.items():
            overlap.setdefault(domain, set()).add(competitor)
            scores[domain] = max(scores.get(domain, 0.0), score)

    if not overlap:
        print("\nNo referring-domain data retrieved from Semrush this run -- nothing to evaluate.")
        return

    print(f"\nPulling tulo.io's own referring domains (to exclude domains that already link to us)...")
    try:
        tulo_refdomains = set(_fetch_referring_domains(TULO_DOMAIN, semrush_key).keys())
    except (requests.RequestException, RuntimeError) as exc:
        print(f"  tulo.io lookup failed -- proceeding without this exclusion ({exc})")
        tulo_refdomains = set()

    print("\nFetching already-contacted domains and contact emails...")
    seen_domains, seen_emails = _existing_domains_and_emails(base, auth)

    candidates = sorted(
        (
            d for d in overlap
            if not _is_excluded(d) and d not in tulo_refdomains and _canonical_domain(d) not in seen_domains
            and scores.get(d, 0.0) <= MAX_AUTHORITY_SCORE
        ),
        key=lambda d: (-len(overlap[d]), -scores.get(d, 0.0)),
    )
    print(f"\n{len(candidates)} gap candidate(s) to evaluate (linking to a competitor, not to Tulo, not already queued, authority <= {MAX_AUTHORITY_SCORE}).")

    queued: list[dict] = []
    evaluated = 0
    skipped_no_email = 0
    skipped_duplicate_email = 0
    queued_manual_form = 0
    for domain in candidates:
        if len(queued) >= remaining:
            break
        evaluated += 1
        html = _fetch(f"https://{domain}/")
        if html is None:
            print(f"  {domain}: homepage fetch failed, skipping")
            continue
        text = _page_text(html)
        if len(text) < 200:
            print(f"  {domain}: homepage text too thin to judge, skipping")
            continue
        page_mailtos = list(_extract_mailto_emails(html))
        contact_text, contact_mailtos = _contact_page_text(domain)
        for email in contact_mailtos:
            if email not in page_mailtos:
                page_mailtos.append(email)
        if contact_text:
            text = f"{text}\n\n--- Contact/About/privacy/media-kit pages ---\n{contact_text}"
        competitors_hit = sorted(overlap[domain])
        result = _vet_and_draft(client, base, domain, text, competitors_hit)
        if result is None:
            continue
        if not result["contact_email"] and page_mailtos:
            # A real mailto: address was sitting in this domain's own page
            # markup, invisible to the model -- already verified by
            # construction, see outreach_fetch.extract_mailto_emails.
            result["contact_email"] = page_mailtos[0]
            print(f"  {domain}: recovered {page_mailtos[0]!r} from a mailto: link the model's page text couldn't show it")
        if not result["contact_email"]:
            result["contact_form_url"] = _contact_form_url(domain)
            if not result["contact_form_url"]:
                skipped_no_email += 1
                print(f"  {domain}: credible but no verifiable contact email or contact form found, skipping")
                continue
            queued_manual_form += 1
            print(f"  {domain}: credible but no email -- queuing for manual outreach via {result['contact_form_url']}")
        else:
            email_key = result["contact_email"].strip().lower()
            if email_key in seen_emails:
                skipped_duplicate_email += 1
                print(f"  {domain}: credible with a real email, but that email is already in the queue, skipping")
                continue
            seen_emails.add(email_key)
            result["contact_form_url"] = None
        result["source_query"] = f"backlink_gap:{','.join(competitors_hit)}"
        queued.append(result)
        contact_display = result["contact_email"] or f"form only: {result['contact_form_url']}"
        print(f"  {domain}: ACCEPTED (linked to {', '.join(competitors_hit)}; contact: {contact_display})")

    print(
        f"\n{len(queued)} candidate(s) queued out of {evaluated} evaluated "
        f"({queued_manual_form} needing manual form outreach, {skipped_no_email} credible-but-unreachable, "
        f"{skipped_duplicate_email} duplicate-contact skipped)."
    )

    if args.dry_run:
        print("\n--dry-run: not creating any prospects. Would have queued:")
        for p in queued:
            print(json.dumps(p, indent=2))
        return

    for p in queued:
        r = requests.post(
            f"{base}/admin/outreach-queue/create",
            auth=auth,
            json={
                "pitch_type": "tool_pitch",
                "target_domain": p["target_domain"],
                "contact_email": p["contact_email"],
                "subject": p["subject"],
                "body_preview": p["body_preview"],
                "source_query": p["source_query"],
                "contact_form_url": p.get("contact_form_url"),
            },
            timeout=30,
        )
        if r.status_code == 200:
            print(f"{p['target_domain']}: queued (id {r.json()['created_prospect_id']})")
        else:
            print(f"{p['target_domain']}: FAILED ({r.status_code}) {r.text[:200]}")


if __name__ == "__main__":
    main()
