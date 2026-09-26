"""Roundup-inclusion outreach sourcing: finds real "best chicken recipes" /
"best kitchen tools" style roundup posts on other sites and pitches for
Tulo's own matching recipe or tool page to be ADDED to that specific post
-- a fundamentally different, higher-intent ask than daily_outreach_
sourcing.py's generic "check out our tool" cold pitch, since it references
a real, already-published post the target site chose to write.

Discovery uses Claude's own bounded web_search tool (one search per query
template below, max_uses=1 each) to find real roundup post URLs -- this is
NOT the "search API for candidate discovery" daily_outreach_sourcing.py's
docstring rules out (that policy is about not letting SEO-gamed rankings
bias which blogs get targeted broadly); here the search is narrowly
scoped to finding actual roundup posts by topic, a one-time bounded
lookup, not a ranking signal used to rank/select among many candidates.

Lands as pitch_type="content_pitch" (not tool_pitch) since the ask is
"please add this specific Tulo page to your existing post," not a cold
tool mention.

Shares the same daily queue quota as every other automated outbound
sourcing script -- see _remaining_daily_quota.

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    PIPELINE_ANTHROPIC_API_KEY=... \
    python3 content/scripts/roundup_inclusion_outreach.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from outreach_fetch import extract_mailto_emails as _extract_mailto_emails
from outreach_fetch import fetch as _shared_fetch
from outreach_fetch import fetch_working_page as _shared_fetch_working_page

# One real web_search per template, so keep this list short and deliberate
# -- each entry costs one Claude call plus one web_search use. Mixes
# recipe-roundup queries (topics Tulo actually has recipe content for)
# with tool/calculator-roundup queries (for the 3 fixed tools).
ROUNDUP_QUERY_TEMPLATES = [
    "best chicken dinner recipes roundup blog post",
    "best easy weeknight dinner recipes roundup",
    "best cookie recipes roundup blog post",
    "best pasta recipes roundup blog post",
    "best kitchen conversion calculators and tools for bakers",
    "best cooking temperature and doneness charts for home cooks",
    # Added 2026-09-20: 3 more recipe-roundup topics Tulo has real content
    # for, to widen the candidate pool beyond the original 6 templates.
    "best breakfast recipes roundup blog post",
    "best baking recipes roundup blog post",
    "best slow cooker recipes roundup blog post",
]

EXCLUDED_DOMAIN_SUFFIXES = {
    "wordpress.com", "wordpress.org", "blogspot.com", "blogger.com",
    "pinterest.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "youtu.be", "amazon.com", "amzn.to", "wikipedia.org",
    "medium.com", "tumblr.com", "reddit.com", "quora.com", "linkedin.com",
    "tiktok.com", "threads.net", "google.com", "goo.gl", "bit.ly",
    "apple.com", "feedburner.com", "mailchimp.com", "bloglovin.com",
    "feedspot.com", "similarweb.com", "semrush.com", "ahrefs.com", "moz.com",
    "tulo.io", "pinterest.co.uk",
}

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
DAILY_QUEUE_CAP = 50  # shared across every automated outbound sourcing script

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

DISCOVERY_WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 1,
}

# Static (candidate-independent) system prompt + two-step vet/draft
# protocol + usage tracking -- see daily_outreach_sourcing.py's identical
# comment (2026-09-26) for the full rationale.
_TOOLS_BLOCK = "\n".join(f"- {t['name']}: {t['description']} ({t['url']})" for t in TULO_TOOLS)
SYSTEM_PROMPT_TEXT = (
    "You vet content-inclusion outreach candidates for Tulo, a free food/recipe website. Each "
    "candidate site published a real roundup/list post (given in the user message below) that "
    "looks like the kind of post that adds reader-recommended items over time. Judge the site's "
    "overall credibility from the homepage/contact text below: a genuine author voice, evidence of "
    "a real audience, original writing that reads as human-written, a real About/Contact section -- "
    "reject generic aggregators, thin affiliate-only sites, or anything not genuinely about "
    "food/cooking.\n\n"
    "Tulo has three fixed, always-real tools:\n"
    f"{_TOOLS_BLOCK}\n\n"
    "Tulo also has thousands of individual content pages -- recipes, ingredient guides, cooking "
    "how-tos. Use the search_tulo_content tool to find ONE real Tulo page that would genuinely fit "
    "being added to the specific roundup post named in the user message (infer its likely topic "
    "from the URL/title context you're given) -- never guess or invent a slug/URL, only the search "
    "tool's real results or the three fixed tools are safe to use. The pitch must ask them to "
    "consider adding this ONE specific page to their existing post, referencing the post by URL -- "
    "this is a 'please add us to what you already published' ask, not a generic cold pitch.\n\n"
    "Contact email: the text you're given often doesn't contain a real email. A verified address "
    "found directly in that domain's own page markup is sometimes already given to you in the user "
    "message below -- when it is, use it as contact_email directly and skip searching for another. "
    "Otherwise, if you don't see one, use the web_search tool (up to 3 searches) ONLY to look for "
    "that domain's own published contact email. If found, report contact_email AND "
    "contact_email_source_url (the exact page URL) together. If you can't find one either way, set "
    "both to null; this never affects the credible verdict.\n\n"
    "This happens in two steps, so a pitch is never drafted for a candidate that turns out to have "
    "no way to actually reach them:\n\n"
    "Step 1 (this turn): respond with ONLY a JSON object (no prose, no markdown fences, no further "
    "tool calls) with exactly these keys: credible (boolean), reason (one sentence), contact_email "
    "(else null), contact_email_source_url (else null). Do NOT draft a pitch in this step, even when "
    "credible is true -- a human reviewer decides afterward whether a real way to reach this contact "
    "(a verified email, or a contact form) actually exists, and only then asks you to draft it in a "
    "follow-up turn.\n\n"
    "Step 2 (only if a later turn asks you to): respond with ONLY a JSON object with exactly these "
    "keys: subject, body (a short, specific, non-generic 3-5 sentence pitch that names the roundup "
    "post and asks them to consider adding exactly one real URL - from the fixed tools list or a "
    "search_tulo_content result, never invented; use a single hyphen with spaces around it for a "
    "dash, never an em dash)."
)
SYSTEM_PROMPT = [{"type": "text", "text": SYSTEM_PROMPT_TEXT, "cache_control": {"type": "ephemeral"}}]


class _UsageTotals:
    """See daily_outreach_sourcing.py's identical class."""

    def __init__(self) -> None:
        self.api_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_input_tokens = 0
        self.cache_creation_input_tokens = 0
        self.web_search_requests = 0

    def add(self, usage) -> None:
        self.api_calls += 1
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.cache_read_input_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.cache_creation_input_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
        server_tool_use = getattr(usage, "server_tool_use", None)
        if server_tool_use is not None:
            self.web_search_requests += getattr(server_tool_use, "web_search_requests", 0) or 0

    def estimated_cost_usd(self) -> float:
        return (
            self.input_tokens * 2.00 / 1_000_000
            + self.output_tokens * 10.00 / 1_000_000
            + self.cache_read_input_tokens * 0.20 / 1_000_000
            + self.cache_creation_input_tokens * 2.50 / 1_000_000
            + self.web_search_requests * 10.00 / 1_000
        )

    def summary(self) -> str:
        return (
            f"${self.estimated_cost_usd():.4f} estimated ({self.api_calls} API call(s), "
            f"{self.input_tokens} input tok, {self.output_tokens} output tok, "
            f"{self.cache_read_input_tokens} cache-read tok, {self.cache_creation_input_tokens} cache-write tok, "
            f"{self.web_search_requests} web_search use(s))"
        )


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


def _find_roundup_urls(client, query: str, max_results: int = 5) -> list[str]:
    """One bounded web_search call per query template. Reads .url directly
    off each web_search_result block -- unlike page-content snippets
    (encrypted_content, only usable by the model itself), the result URL
    and title are plain fields we can read on our side."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        tools=[DISCOVERY_WEB_SEARCH_TOOL],
        messages=[{"role": "user", "content": f"Use the web_search tool once to search for: {query}"}],
    )
    urls: list[str] = []
    for block in response.content:
        if block.type != "web_search_tool_result":
            continue
        content = block.content
        if not isinstance(content, list):
            continue  # error object, e.g. {"error_code": "..."} -- skip
        for result in content:
            url = getattr(result, "url", None)
            if url:
                urls.append(url)
    return urls[:max_results]


def _existing_domains_and_emails(base: str, auth: tuple[str, str]) -> tuple[set[str], set[str]]:
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=30)
    r.raise_for_status()
    rows = r.json()
    domains = {_canonical_domain(row["target_domain"].lower()) for row in rows}
    emails = {row["contact_email"].strip().lower() for row in rows if (row.get("contact_email") or "").strip()}
    return domains, emails


def _remaining_daily_quota(base: str, auth: tuple[str, str], cap: int = DAILY_QUEUE_CAP) -> int:
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


def _run_tool_loop(client, messages: list[dict], base: str, allowed_urls: set[str], totals: "_UsageTotals", max_tokens: int) -> object | None:
    """See daily_outreach_sourcing.py's identical function."""
    response = None
    for _ in range(MAX_TOOL_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            tools=[SEARCH_TULO_CONTENT_TOOL, WEB_SEARCH_TOOL],
            messages=messages,
        )
        totals.add(response.usage)
        if response.stop_reason != "tool_use":
            return response
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            results = _http_search_tulo_content(base, block.input.get("query", "")) if block.name == "search_tulo_content" else []
            allowed_urls.update(r["url"] for r in results)
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(results)})
        messages.append({"role": "user", "content": tool_results})
    return None


def _vet_candidate(client, base: str, domain: str, homepage_text: str, roundup_url: str, known_mailto: str | None, totals: "_UsageTotals"):
    """Phase 1 only -- credibility + email, never drafts. See
    daily_outreach_sourcing.py's identical function."""
    allowed_urls = {t["url"] for t in TULO_TOOLS}
    known_email_note = (
        f"Already-verified contact email for this domain (found directly in its own page markup): "
        f"{known_mailto} -- use this as contact_email directly; you do not need to search for "
        "another.\n\n"
        if known_mailto else ""
    )
    messages: list[dict] = [
        {"role": "user", "content": f"Candidate domain: {domain}\nRoundup post: {roundup_url}\n\n{known_email_note}Homepage text:\n{homepage_text}"}
    ]
    response = _run_tool_loop(client, messages, base, allowed_urls, totals, max_tokens=1024)
    if response is None:
        print(f"  {domain}: exceeded {MAX_TOOL_TURNS} tool-use turns, skipping")
        return None, messages, allowed_urls

    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    item = _extract_json_object(raw)
    if item is None:
        print(f"  {domain}: model response wasn't valid JSON, skipping (raw: {raw[:200]!r})")
        return None, messages, allowed_urls

    if not item.get("credible"):
        print(f"  {domain}: rejected -- {item.get('reason', 'no reason given')}")
        return None, messages, allowed_urls

    messages.append({"role": "assistant", "content": response.content})

    contact_email = (item.get("contact_email") or "").strip() or None
    source_url = (item.get("contact_email_source_url") or "").strip() or None
    if contact_email:
        verified = contact_email in homepage_text or (known_mailto is not None and contact_email == known_mailto)
        if not verified and source_url:
            source_domain = _root_domain(source_url)
            if source_domain == domain or source_domain.endswith("." + domain):
                source_html = _fetch(source_url, timeout=10)
                if source_html is not None:
                    verified = contact_email in _page_text(source_html, max_chars=4000)
        if not verified:
            print(f"  {domain}: claimed contact_email not verified against fetched page text, dropping email only")
            contact_email = None

    return {"contact_email": contact_email}, messages, allowed_urls


def _draft_pitch(client, base: str, domain: str, messages: list[dict], allowed_urls: set[str], via_form: bool, totals: "_UsageTotals") -> dict | None:
    """Phase 2 -- only called once main() has confirmed a real contact
    route exists. See daily_outreach_sourcing.py's identical function."""
    reason = "a contact form (no email address was found or verified)" if via_form else "the verified contact email above"
    messages.append({
        "role": "user",
        "content": (
            f"Confirmed: this candidate can actually be reached, via {reason}. Draft the pitch now. "
            "Respond with ONLY a JSON object (no prose, no markdown fences, no further tool calls) with "
            "exactly these keys: subject, body (a short, specific, non-generic 3-5 sentence pitch that "
            "names the roundup post and asks them to consider adding exactly one real URL - from the "
            "fixed tools list or a search_tulo_content result you already found, never invented; use a "
            "single hyphen with spaces around it for a dash, never an em dash)."
        ),
    })
    response = _run_tool_loop(client, messages, base, allowed_urls, totals, max_tokens=2048)
    if response is None:
        print(f"  {domain}: exceeded {MAX_TOOL_TURNS} tool-use turns while drafting, skipping")
        return None

    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    item = _extract_json_object(raw)
    if item is None:
        print(f"  {domain}: draft response wasn't valid JSON, skipping (raw: {raw[:200]!r})")
        return None

    body = item.get("body") or ""
    if not any(url in body for url in allowed_urls):
        print(f"  {domain}: dropped -- credible but no real Tulo URL in drafted body")
        return None

    return {"subject": item.get("subject") or "", "body_preview": body}


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

    remaining = _remaining_daily_quota(base, auth)
    if args.count is not None:
        remaining = min(remaining, args.count)
    print(f"Shared daily quota: {remaining} slot(s) remaining today.")
    if remaining <= 0:
        print("Daily quota already reached by an earlier sourcing step today -- nothing to do.")
        return

    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["PIPELINE_ANTHROPIC_API_KEY"])

    print("Fetching already-contacted domains and contact emails...")
    seen_domains, seen_emails = _existing_domains_and_emails(base, auth)

    print(f"\nSearching for real roundup posts across {len(ROUNDUP_QUERY_TEMPLATES)} quer(y/ies)...")
    candidates: dict[str, str] = {}  # domain -> first roundup URL found for it
    for query in ROUNDUP_QUERY_TEMPLATES:
        urls = _find_roundup_urls(client, query)
        print(f"  '{query}': {len(urls)} result(s)")
        for url in urls:
            domain = _root_domain(url)
            canon = _canonical_domain(domain)
            if not domain or _is_excluded(domain) or canon in seen_domains or domain in candidates:
                continue
            candidates[domain] = url
            seen_domains.add(canon)

    print(f"\n{len(candidates)} new candidate domain(s) to evaluate.")

    usage_totals = _UsageTotals()
    queued: list[dict] = []
    evaluated = 0
    skipped_no_email = 0
    skipped_duplicate_email = 0
    queued_manual_form = 0
    for domain, roundup_url in candidates.items():
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

        known_mailto = page_mailtos[0] if page_mailtos else None
        if known_mailto and known_mailto in seen_emails:
            skipped_duplicate_email += 1
            print(f"  {domain}: mailto {known_mailto!r} already in queue, skipping before calling the model")
            continue

        verdict, convo, allowed_urls = _vet_candidate(client, base, domain, text, roundup_url, known_mailto, usage_totals)
        if verdict is None:
            continue

        contact_email = verdict["contact_email"]
        if not contact_email and page_mailtos:
            # A real mailto: address was sitting in this domain's own page
            # markup, invisible to the model -- already verified by
            # construction, see outreach_fetch.extract_mailto_emails.
            contact_email = page_mailtos[0]
            print(f"  {domain}: recovered {contact_email!r} from a mailto: link the model's page text couldn't show it")

        if contact_email:
            email_key = contact_email.strip().lower()
            if email_key in seen_emails:
                skipped_duplicate_email += 1
                print(f"  {domain}: credible with a real email, but that email is already in the queue, skipping")
                continue
            draft = _draft_pitch(client, base, domain, convo, allowed_urls, via_form=False, totals=usage_totals)
            if draft is None:
                continue
            seen_emails.add(email_key)
            result = {**draft, "target_domain": domain, "contact_email": contact_email, "contact_form_url": None}
        else:
            contact_form_url = _contact_form_url(domain)
            if not contact_form_url:
                skipped_no_email += 1
                print(f"  {domain}: credible but no verifiable contact email or contact form found, skipping")
                continue
            draft = _draft_pitch(client, base, domain, convo, allowed_urls, via_form=True, totals=usage_totals)
            if draft is None:
                continue
            queued_manual_form += 1
            print(f"  {domain}: credible but no email -- queuing for manual outreach via {contact_form_url}")
            result = {**draft, "target_domain": domain, "contact_email": None, "contact_form_url": contact_form_url}

        result["source_query"] = f"roundup_inclusion:{roundup_url}"
        queued.append(result)
        contact_display = result["contact_email"] or f"form only: {result['contact_form_url']}"
        print(f"  {domain}: ACCEPTED (roundup: {roundup_url}; contact: {contact_display})")

    print(
        f"\n{len(queued)} candidate(s) queued out of {evaluated} evaluated "
        f"({queued_manual_form} needing manual form outreach, {skipped_no_email} credible-but-unreachable, "
        f"{skipped_duplicate_email} duplicate-contact skipped)."
    )
    print(f"API usage: {usage_totals.summary()}")

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
                "pitch_type": "content_pitch",
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
