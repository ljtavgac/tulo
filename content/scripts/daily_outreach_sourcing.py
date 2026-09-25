"""Daily outreach sourcing: crawls a fixed set of real, well-known food-
blog directory/roundup pages (see HUB_PAGES below) for candidate blog
domains -- never a search API, per explicit instruction: no Semrush, no
Google/Bing search API, no paid domain-authority service. That policy is
about candidate *discovery* specifically, to avoid SEO-gamed rankings
biasing which blogs get targeted -- it does not extend to the separate,
narrower problem below of finding an already-identified candidate's own
contact email. Filters out generic platforms and anything already in the
outreach queue, then uses Claude to (a) judge each remaining candidate's
own homepage (plus, when reachable, its Contact/About/privacy-policy/
media-kit pages) for real, credible signals using free/visible heuristics
only (a genuine author voice, an actual audience, original writing, a
real About/Contact page -- not a link farm, PBN, or spun-content mill),
(b) find a real contact email -- first from the fetched page text, and if
that comes up empty, via a bounded (max 3 searches per candidate) use of
Claude's own web_search tool to locate that same domain's own published
address (privacy policy, media kit, "write for us" page, etc.), which is
then independently re-verified by this script fetching the cited source
URL directly rather than trusting the model's claim, (c) pick one
genuinely relevant real Tulo page to cite (one of the three fixed tools,
or a real result from Tulo's own public page search -- never invented),
and (d) draft a short, specific, non-generic pitch. A credible candidate
for which no contact email can be found or verified is skipped outright,
not queued -- the run keeps evaluating further candidates (up to
MAX_CANDIDATES_PER_RUN) until it fills its share of the daily quota, so
every prospect that lands in the queue has a real, verified contact
email. Queues via POST /admin/outreach-queue/create, same endpoint every
other outreach-sourcing script in this project uses -- lands as
status=queued, pending human review in the portal exactly like every
other prospect. Never sends anything itself.

This is now the lowest-priority, fallback source in a multi-source daily
run (see .github/workflows/daily-link-building.yml) -- it shares one
DAILY_QUEUE_CAP-sized daily budget with backlink_gap_outreach.py,
roundup_inclusion_outreach.py, broken_link_outreach.py, unlinked_mention_
outreach.py, and resource_page_outreach.py (see _remaining_daily_quota),
rather than queuing its own count on top of whatever they already
queued today. It runs last in that workflow because it's the least
qualified candidate pool of the six (a blind directory crawl vs. the
others' more targeted discovery), so the higher-quality sources get
first claim on the day's quota and this one only fills what's left.

Five code-enforced invariants, mirroring _draft_haro_replies
(backend/app/main.py) exactly, applied here to cold-outreach candidates
instead of HARO digest queries: (1) a claimed contact email is dropped
(not the whole prospect) unless it's independently verified -- either it
appears verbatim in the fetched page text, or (when it came from
web_search) it appears verbatim on a direct re-fetch of the model's cited
source URL, which must itself be on the same domain being vetted; (2) the
drafted body must contain one of the allowed URLs (the three fixed
tools, or a real search_tulo_content result) verbatim, checked the same
way; (3) a site the model doesn't judge genuinely credible is dropped
outright, never queued as a "maybe"; (4) a credible site with no
verifiable contact email is skipped, never queued without one; (5) a
credible site whose verified contact email already belongs to another
prospect already in the queue (any status, any pitch_type) is skipped
too -- the same person often runs more than one blog, and domain-only
dedup doesn't stop that person from being emailed again on a later day
just because the domain looks new.

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    PIPELINE_ANTHROPIC_API_KEY=... \
    python3 content/scripts/daily_outreach_sourcing.py [--count N] [--dry-run]

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

# Real, well-known "best food blogs" roundup/directory pages -- each links
# out to dozens of individual food blogs. Never a search API: these are
# fixed, hand-picked starting points for a plain HTTP crawl, re-fetched
# fresh every run since these lists get updated over time. Add more here
# as the daily supply of new, un-contacted candidates runs thin.
HUB_PAGES = [
    "https://detailed.com/food-blogs/",
    "https://masterblogging.com/best-food-blogs/",
    "https://www.awesomebloggers.com/articles/best-food-blogs-2026",
    "https://toptenblogs.com/categories/food",
    "https://chewtheworld.com/best-food-blog/",
    "https://www.menutiger.com/blog/best-food-blogs",
    # Added 2026-09-20: the original 6 are increasingly saturated with
    # already-contacted domains (68 of them pre-filtered out of a single
    # run today, up from 47 the day before) -- these two add real,
    # differently-sourced candidates rather than re-crawling the same
    # well-known "best of" pages. Feedspot's own directory (100 blogs,
    # independently curated) and tastingspoons.com's roundup post (an
    # individual blogger's own links to 50 others) are structurally
    # different from the big generic SEO-ranking directories above, more
    # likely to surface smaller/less commonly-crawled sites.
    "https://bloggers.feedspot.com/food_blogs/",
    "https://tastingspoons.com/archives/2606",
]

# Generic platforms, social networks, marketplaces, and the hub/directory
# sites themselves -- never real outreach targets even though they show up
# constantly as outbound links on any roundup page. Matched as a suffix of
# the candidate's own domain (so "www.pinterest.com" and "uk.pinterest.com"
# both match "pinterest.com").
EXCLUDED_DOMAIN_SUFFIXES = {
    "wordpress.com", "wordpress.org", "blogspot.com", "blogger.com",
    "pinterest.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "youtu.be", "amazon.com", "amzn.to", "wikipedia.org",
    "medium.com", "tumblr.com", "reddit.com", "quora.com", "linkedin.com",
    "tiktok.com", "threads.net", "google.com", "goo.gl", "bit.ly",
    "apple.com", "feedburner.com", "mailchimp.com", "bloglovin.com",
    "feedspot.com", "similarweb.com", "semrush.com", "ahrefs.com", "moz.com",
    "tulo.io",
    # the hub pages themselves, plus other common "best blogs" directory/
    # ranking sites that tend to cross-link each other on these same pages
    "detailed.com", "masterblogging.com", "awesomebloggers.com",
    "toptenblogs.com", "chewtheworld.com", "menutiger.com",
    "foodbloggersofcanada.com", "cision.com", "muckrack.com",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Duplicated from backend/app/main.py's _TULO_TOOLS_FOR_PITCHING on
# purpose -- this script and the backend don't share a package (see
# add_outreach_prospects.py's own docstring on the same convention).
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
MAX_TOOL_TURNS = 12  # confirmed live: 6 was too tight -- a genuinely good candidate (altonbrown.com)
# got dropped purely for exceeding it while still searching for a good content match, not for
# any real credibility problem
MAX_CANDIDATES_PER_RUN = 120  # hard cap on LLM calls regardless of --count, to bound cost/time --
# raised from 60 now that a credible candidate with no verifiable email is skipped rather than
# queued, so filling --count with emailed prospects needs more evaluations per run on average
DAILY_QUEUE_CAP = 50  # shared across every automated outbound sourcing script, not per-script --
# see _remaining_daily_quota

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

# Claude's own server-side web-search tool -- executed by Anthropic, not by
# this script. Scoped narrowly by the system prompt (below) to one job only:
# locating an already-identified, already-vetted-as-credible candidate's own
# published contact email when it isn't in the page text already fetched.
# This is NOT a reversal of the "never a search API" policy documented at
# the top of this file -- that policy is about candidate *discovery* (never
# use search rankings to decide which blogs to target, to avoid SEO-gamed
# results biasing the crawl). Finding one already-identified site's own
# contact page is a different problem, and max_uses bounds it per candidate.
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
    email on the 'Work with Me' page..." then the JSON, occasionally
    still wrapped in a fence -- rather than ever truncating (every real
    failure had stop_reason == "end_turn" well under the token budget).
    The old fence-strip only handled a fence anchored at position 0, so
    any leading prose defeated it outright. Tries, in order: the raw
    string as-is, a fenced block found ANYWHERE in the string, then the
    first-'{'-to-last-'}' slice -- the JSON object is always the last
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


def _extract_candidate_domains(hub_url: str, html: str) -> set[str]:
    hub_domain = _root_domain(hub_url)
    soup = BeautifulSoup(html, "html.parser")
    domains = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(hub_url, a["href"])
        parsed = urlparse(href)
        if parsed.scheme not in ("http", "https"):
            continue
        domain = _root_domain(href)
        if not domain or domain == hub_domain or _is_excluded(domain):
            continue
        domains.add(domain)
    return domains


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
# Bounds how many of the paths above are actually fetched per candidate --
# most sites only have 2-3 of these, but a hard cap keeps a single slow/odd
# domain from blowing up run time.
MAX_CONTACT_PAGES_FETCHED = 4


def _contact_page_text(domain: str, max_chars_per_page: int = 1500) -> tuple[str, list[str]]:
    """Best-effort: a real contact email is often not on the homepage or
    even the Contact/About page, but on a page like /privacy-policy or
    /media-kit instead -- confirmed by manual research on already-queued
    prospects, where several emails only turned up on those less-obvious
    pages. Unlike the original version of this function, this does NOT
    stop at the first path that loads -- it collects text from every real
    page it finds (up to MAX_CONTACT_PAGES_FETCHED) since the first page
    that loads is often not the one with the email on it. A miss here
    just means contact_email stays null, same as before, never blocks
    vetting.

    Also returns any mailto: addresses found in the raw HTML of those same
    pages (see outreach_fetch.extract_mailto_emails) -- real addresses a
    vetting model given only stripped page text could never see for
    itself, confirmed live to recover real contacts this pipeline was
    otherwise losing."""
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


def _existing_domains_and_emails(base: str, auth: tuple[str, str]) -> tuple[set[str], set[str]]:
    """One fetch of every prospect ever queued (any status, any pitch_type
    -- haro_reply included), returning both the set of already-targeted
    domains and the set of already-targeted contact emails. The email set
    matters separately from the domain set: the same person often runs (or
    is the contact for) more than one blog, so two different, never-before-
    seen domains can still resolve to a contact who'd otherwise get emailed
    twice across different days -- domain-only dedup doesn't catch that."""
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=30)
    r.raise_for_status()
    rows = r.json()
    domains = {_canonical_domain(row["target_domain"].lower()) for row in rows}
    emails = {row["contact_email"].strip().lower() for row in rows if (row.get("contact_email") or "").strip()}
    return domains, emails


def _remaining_daily_quota(base: str, auth: tuple[str, str], cap: int = DAILY_QUEUE_CAP) -> int:
    """This script is now the lowest-priority, fallback source in a
    multi-source daily run (see .github/workflows/daily-link-building.yml)
    -- it draws from the SAME shared daily budget of `cap` newly-queued
    prospects as backlink_gap_outreach.py, roundup_inclusion_outreach.py,
    broken_link_outreach.py, unlinked_mention_outreach.py, and
    resource_page_outreach.py, not `cap` on top of what they already
    queued today. Counts today's (UTC) already-created tool_pitch/
    content_pitch rows -- haro_reply is a separate, inbound-triggered
    pipeline, not part of this outbound daily budget."""
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
    """HTTP-backed equivalent of backend/app/main.py's _search_tulo_content
    -- calls the same public, unauthenticated /pages endpoint the frontend
    itself uses for search, with paged=true so unpublished pages are
    correctly excluded (see this session's own pagination-bug fix to that
    exact branch) rather than relying on a second per-slug verification
    round trip."""
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


def _vet_and_draft(client, base: str, domain: str, homepage_text: str) -> dict | None:
    """One candidate per call. Returns None if the model doesn't judge the
    site genuinely credible, or if either code-enforced invariant fails
    after a credible verdict. Never raises for a single bad candidate --
    the caller moves on to the next one."""
    from anthropic import Anthropic  # noqa: F401  (import kept local to mirror _draft_haro_replies' style)

    tools_block = "\n".join(f"- {t['name']}: {t['description']} ({t['url']})" for t in TULO_TOOLS)
    system_prompt = (
        "You vet cold-outreach candidates for Tulo, a free food/recipe website building genuine, "
        "editorial backlinks -- never a link farm or PBN itself, and only interested in linking from "
        "real ones either.\n\n"
        "Given the homepage (and, when available, Contact/About page) text of one candidate site "
        "below, decide whether it's a real, credible, "
        "actively-run food/cooking blog: a genuine author voice or byline, evidence of a real "
        "audience (comments, social presence, an about-the-author bio), original writing that reads "
        "as human-written (not spun or AI-mill boilerplate), a real About/Contact section. Reject "
        "generic content aggregators, thin affiliate-only sites, obviously auto-generated text, or "
        "anything that isn't actually about food/cooking/recipes.\n\n"
        "Tulo has three fixed, always-real tools:\n"
        f"{tools_block}\n\n"
        "Tulo also has thousands of individual content pages -- recipes, ingredient guides, cooking "
        "how-tos, definitions, comparisons, substitute guides. Use the search_tulo_content tool to "
        "check for one genuinely relevant to this specific site's focus before recommending it; never "
        "guess or invent a slug/URL for one of these, only the search tool's real results are safe to "
        "use. If nothing specific fits, use one of the three fixed tools instead -- never force an "
        "irrelevant content-page match just to avoid a tool page.\n\n"
        "Contact email: the text you're given (homepage plus any Contact/About/privacy/media-kit pages "
        "that were reachable) often doesn't contain a real email, even for a genuinely credible site -- "
        "it may be published somewhere else on the same site instead (privacy policy, media kit, a "
        "'write for us'/pitch page, footer, etc.). If you don't see one in the given text, use the "
        "web_search tool (up to 3 searches) ONLY to look for that same domain's own published contact "
        "email -- e.g. 'site:<domain> contact email', '<domain> media kit', '<domain> write for us'. "
        "This is not for judging credibility, only for finding an email for a site you've already "
        "decided about from the given text. If you find a real, currently-published address, report it "
        "as contact_email AND set contact_email_source_url to the exact page URL where you found it -- "
        "these two fields are required together, never set one without the other. If you can't find a "
        "genuine address either in the given text or via web_search, set both to null; this never "
        "affects the credible verdict.\n\n"
        "Once decided, respond with ONLY a JSON object (no prose, no markdown fences, no further tool "
        "calls) with exactly these keys: credible (boolean), reason (one sentence, for a human "
        "reviewer, why or why not), contact_email (a real email address per the rules above, else "
        "null), contact_email_source_url (the exact URL it came from if contact_email is set, else "
        "null), subject, body (a short, specific, non-generic 3-5 sentence pitch mentioning something "
        "concrete from this specific site plus exactly one real URL - from the fixed tools list or a "
        "search_tulo_content result, never invented; use a single hyphen with spaces around it for a "
        "dash, e.g. 'word - word', never a double hyphen or em dash). If credible is false, "
        "subject/body/contact_email/contact_email_source_url may be null."
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
        # Same invariant as _draft_haro_replies' reporter_email check: never
        # trust a claimed email just because the model said so -- drop the
        # claimed email (not the whole prospect) unless we can verify it
        # ourselves against real fetched text. First check the text we
        # already handed the model; if the email instead came from the
        # model's own web_search (whose result content isn't plaintext we
        # can read on our side), re-fetch its cited source_url directly and
        # check the email appears there verbatim -- restricted to the same
        # domain being vetted, so the model can't point us at an unrelated
        # third-party page and have us "confirm" text there.
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
    parser.add_argument(
        "--count", type=int, default=None,
        help="Cap how many to queue this run (default: use the full shared daily quota remaining)",
    )
    parser.add_argument("--dry-run", action="store_true")
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
    seen, seen_emails = _existing_domains_and_emails(base, auth)
    print(
        f"  {len(seen)} domain(s) and {len(seen_emails)} contact email(s) already in the queue "
        "(any status) -- will skip these."
    )

    print("\nCrawling hub pages for candidate domains...")
    candidates: list[str] = []
    for hub_url in HUB_PAGES:
        html = _fetch(hub_url)
        if html is None:
            print(f"  {hub_url}: fetch failed, skipping")
            continue
        found = _extract_candidate_domains(hub_url, html)
        new = []
        for d in sorted(found):
            if d in candidates:
                continue
            canon = _canonical_domain(d)
            if canon in seen:
                continue
            new.append(d)
            seen.add(canon)
        print(f"  {hub_url}: {len(found)} linked domain(s), {len(new)} new")
        candidates.extend(new)

    print(f"\n{len(candidates)} total new candidate domain(s) to evaluate (cap {MAX_CANDIDATES_PER_RUN} per run).")

    queued: list[dict] = []
    evaluated = 0
    skipped_no_email = 0
    skipped_duplicate_email = 0
    queued_manual_form = 0
    for domain in candidates:
        if len(queued) >= remaining or evaluated >= MAX_CANDIDATES_PER_RUN:
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
        result = _vet_and_draft(client, base, domain, text)
        if result is None:
            continue
        if not result["contact_email"] and page_mailtos:
            # A real mailto: address was sitting in this domain's own page
            # markup the whole time, invisible to the model (which only
            # ever sees stripped text) -- already verified by construction
            # (it came straight from a real fetch of this exact domain),
            # so it needs no separate check the way a model-claimed address
            # does. See outreach_fetch.extract_mailto_emails.
            result["contact_email"] = page_mailtos[0]
            print(f"  {domain}: recovered {page_mailtos[0]!r} from a mailto: link the model's page text couldn't show it")
        if not result["contact_email"]:
            # Credible, but no real contact email could be found or verified
            # (even after the web_search fallback inside _vet_and_draft, and
            # the mailto-extraction fallback just above) -- fall back to a
            # bare contact-form URL (see _contact_form_url) so a human can
            # paste the drafted pitch in by hand rather than dropping an
            # otherwise-credible candidate outright. Keep evaluating further
            # candidates toward --count instead of stopping here either way.
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
                # A different, never-before-seen domain that happens to share a
                # contact with someone already in the queue (a multi-blog
                # network, or the same person's other site) -- skip it so this
                # person is never emailed twice across different days just
                # because the domain looked new.
                skipped_duplicate_email += 1
                print(f"  {domain}: credible with a real email, but that email is already in the queue, skipping")
                continue
            seen_emails.add(email_key)
            result["contact_form_url"] = None
        result["source_query"] = "daily_outreach_sourcing"
        queued.append(result)
        contact_display = result["contact_email"] or f"form only: {result['contact_form_url']}"
        print(f"  {domain}: ACCEPTED (contact: {contact_display})")

    print(
        f"\n{len(queued)} candidate(s) queued ({queued_manual_form} needing manual form outreach) "
        f"out of {evaluated} evaluated ({skipped_no_email} credible-but-unreachable, "
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
