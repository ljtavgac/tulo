"""Daily outreach sourcing: crawls a fixed set of real, well-known food-
blog directory/roundup pages (see HUB_PAGES below) for candidate blog
domains -- never a search API, per explicit instruction: no Semrush, no
Google/Bing search API, no paid domain-authority service. Filters out
generic platforms and anything already in the outreach queue, then uses
Claude to (a) judge each remaining candidate's own homepage for real,
credible signals using free/visible heuristics only (a genuine author
voice, an actual audience, original writing, a real About/Contact page --
not a link farm, PBN, or spun-content mill), (b) extract a real contact
email if one is actually visible on the page, (c) pick one genuinely
relevant real Tulo page to cite (one of the three fixed tools, or a real
result from Tulo's own public page search -- never invented), and (d)
draft a short, specific, non-generic pitch. Queues up to --count (default
20) passing candidates via POST /admin/outreach-queue/create, same
endpoint every other outreach-sourcing script in this project uses --
lands as status=queued, pending human review in the portal exactly like
every other prospect. Never sends anything itself.

Three code-enforced invariants, mirroring _draft_haro_replies
(backend/app/main.py) exactly, applied here to cold-outreach candidates
instead of HARO digest queries: (1) a claimed contact email is dropped
(not the whole prospect) unless it appears verbatim in the fetched page
text -- rules out the model inventing one; (2) the drafted body must
contain one of the allowed URLs (the three fixed tools, or a real
search_tulo_content result) verbatim, checked the same way; (3) a site
the model doesn't judge genuinely credible is dropped outright, never
queued as a "maybe."

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    PIPELINE_ANTHROPIC_API_KEY=... \
    python3 content/scripts/daily_outreach_sourcing.py [--count 20] [--dry-run]

--dry-run prints what would be queued without ever calling
/admin/outreach-queue/create.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

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
MAX_TOOL_TURNS = 6
MAX_CANDIDATES_PER_RUN = 60  # hard cap on LLM calls regardless of --count, to bound cost/time

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


def _root_domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc.split(":")[0]


def _is_excluded(domain: str) -> bool:
    return any(domain == suf or domain.endswith("." + suf) for suf in EXCLUDED_DOMAIN_SUFFIXES)


def _fetch(url: str, timeout: int = 20) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code != 200:
            return None
        return r.text
    except requests.RequestException:
        return None


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


CONTACT_PAGE_PATHS = ["/contact", "/contact-us", "/about", "/about-us"]


def _contact_page_text(domain: str, max_chars: int = 2000) -> str:
    """Best-effort: most blogs put their real contact email on a separate
    Contact/About page, not the homepage -- confirmed on this pipeline's
    first real run, where every accepted candidate came back with no
    email found from the homepage alone. Tries a few common paths, stops
    at the first that actually loads; a miss here just means
    contact_email stays null, same as before, never blocks vetting."""
    for path in CONTACT_PAGE_PATHS:
        html = _fetch(f"https://{domain}{path}", timeout=10)
        if html is not None:
            return _page_text(html, max_chars)
    return ""


def _existing_domains(base: str, auth: tuple[str, str]) -> set[str]:
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=30)
    r.raise_for_status()
    return {row["target_domain"].lower() for row in r.json()}


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
        "Once decided, respond with ONLY a JSON object (no prose, no markdown fences, no further tool "
        "calls) with exactly these keys: credible (boolean), reason (one sentence, for a human "
        "reviewer, why or why not), contact_email (a real email address if and only if one is "
        "literally visible in the homepage text, else null), subject, body (a short, specific, "
        "non-generic 3-5 sentence pitch mentioning something concrete from this specific site plus "
        "exactly one real URL - from the fixed tools list or a search_tulo_content result, never "
        "invented; use a single hyphen with spaces around it for a dash, e.g. 'word - word', never a "
        "double hyphen or em dash). If credible is false, subject/body/contact_email may be null."
    )

    allowed_urls = {t["url"] for t in TULO_TOOLS}
    messages: list[dict] = [{"role": "user", "content": f"Candidate domain: {domain}\n\nHomepage text:\n{homepage_text}"}]
    response = None
    for _ in range(MAX_TOOL_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system_prompt,
            tools=[SEARCH_TULO_CONTENT_TOOL],
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
    # Despite being told not to, the model occasionally wraps its JSON in a
    # markdown code fence (```json ... ```) -- confirmed live on this
    # pipeline's very first real run, which lost an otherwise-good
    # candidate (alexandracooks.com) to a bare JSONDecodeError over
    # nothing but the fence. Stripping one if present costs nothing when
    # there isn't one.
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        item = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  {domain}: model response wasn't valid JSON, skipping")
        return None

    if not item.get("credible"):
        print(f"  {domain}: rejected -- {item.get('reason', 'no reason given')}")
        return None

    body = item.get("body") or ""
    if not any(url in body for url in allowed_urls):
        print(f"  {domain}: dropped -- credible but no real Tulo URL in drafted body")
        return None

    contact_email = (item.get("contact_email") or "").strip() or None
    if contact_email and contact_email not in homepage_text:
        # Same invariant as _draft_haro_replies' reporter_email check: drop
        # the claimed email, not the whole prospect, rather than trust an
        # address the model didn't actually read off the page.
        print(f"  {domain}: claimed contact_email not found verbatim on page, dropping email only")
        contact_email = None

    return {
        "target_domain": domain,
        "contact_email": contact_email,
        "subject": item.get("subject") or "",
        "body_preview": body,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["PIPELINE_ANTHROPIC_API_KEY"])

    print("Fetching already-contacted domains...")
    seen = _existing_domains(base, auth)
    print(f"  {len(seen)} domain(s) already in the queue (any status) -- will skip these.")

    print("\nCrawling hub pages for candidate domains...")
    candidates: list[str] = []
    for hub_url in HUB_PAGES:
        html = _fetch(hub_url)
        if html is None:
            print(f"  {hub_url}: fetch failed, skipping")
            continue
        found = _extract_candidate_domains(hub_url, html)
        new = sorted(found - seen - set(candidates))
        print(f"  {hub_url}: {len(found)} linked domain(s), {len(new)} new")
        candidates.extend(new)

    print(f"\n{len(candidates)} total new candidate domain(s) to evaluate (cap {MAX_CANDIDATES_PER_RUN} per run).")

    queued: list[dict] = []
    evaluated = 0
    for domain in candidates:
        if len(queued) >= args.count or evaluated >= MAX_CANDIDATES_PER_RUN:
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
        contact_text = _contact_page_text(domain)
        if contact_text:
            text = f"{text}\n\n--- Contact/About page ---\n{contact_text}"
        result = _vet_and_draft(client, base, domain, text)
        if result is None:
            continue
        result["source_query"] = "daily_outreach_sourcing"
        queued.append(result)
        print(f"  {domain}: ACCEPTED" + (f" (contact: {result['contact_email']})" if result["contact_email"] else " (no contact email found)"))

    print(f"\n{len(queued)} candidate(s) passed vetting out of {evaluated} evaluated.")

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
            },
            timeout=30,
        )
        if r.status_code == 200:
            print(f"{p['target_domain']}: queued (id {r.json()['created_prospect_id']})")
        else:
            print(f"{p['target_domain']}: FAILED ({r.status_code}) {r.text[:200]}")


if __name__ == "__main__":
    main()
