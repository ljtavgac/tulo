"""One-off diagnostic: reproduces the exact system prompt / tool-loop /
parsing logic from daily_outreach_sourcing.py against a handful of domains
that failed with "model response wasn't valid JSON" in a recent run, but
prints the RAW, unparsed model output instead of discarding it -- the
production code never logs the raw text on a parse failure, so there's no
way to tell truncation from stray prose from a formatting glitch without
this.
"""

import json
import os
import re

import anthropic
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

MODEL = "claude-sonnet-5"
MAX_TOOL_TURNS = 12

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

BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "https://tulo-backend.onrender.com")

# Domains from today's real "wasn't valid JSON" skips (mix of steps 1 and 5).
DOMAINS = [
    "ambitiouskitchen.com",
    "whatsgabycooking.com",
    "perfectsnacks.com",
    "kristineskitchenblog.com",
    "themodernproper.com",
    "cloudykitchen.com",
]


def _http_search_tulo_content(query: str, limit: int = 6) -> list[dict]:
    try:
        r = requests.get(f"{BACKEND_BASE_URL}/pages", params={"search": query, "limit": limit}, timeout=15)
        r.raise_for_status()
        return [
            {"slug": p["slug"], "title": p["title"], "template_type": p["template_type"], "url": f"https://tulo.io/food/{p['template_type']}/{p['slug']}"}
            for p in r.json()[:limit]
        ]
    except requests.RequestException:
        return []


def diagnose(domain: str, client: anthropic.Anthropic):
    print(f"\n=== {domain} ===")
    try:
        r = requests.get(f"https://{domain}", headers=HEADERS, timeout=20)
        homepage_text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)[:6000]
    except requests.RequestException as e:
        print(f"  fetch failed: {e}")
        return

    system_prompt = (
        "You are vetting a candidate food blog for a cold-outreach link-building pitch from Tulo, a "
        "recipe/ingredient/cooking-tools site. Judge ONLY from the given homepage text (and, if you use "
        "the search_tulo_content tool, its results) whether this looks like a genuine, credible food "
        "blog with a real author, real audience, and original writing -- not a link farm, PBN, or "
        "spun-content mill. If a contact email is visible in the given text, use it. If not, "
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

    messages: list[dict] = [{"role": "user", "content": f"Candidate domain: {domain}\n\nHomepage text:\n{homepage_text}"}]
    response = None
    for turn in range(MAX_TOOL_TURNS):
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
            results = _http_search_tulo_content(block.input.get("query", "")) if block.name == "search_tulo_content" else []
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(results)})
        messages.append({"role": "user", "content": tool_results})
    else:
        print(f"  exceeded {MAX_TOOL_TURNS} tool-use turns")
        return

    print(f"  stop_reason: {response.stop_reason}")
    print(f"  usage: input={response.usage.input_tokens} output={response.usage.output_tokens}")
    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    print(f"  raw length: {len(raw)} chars")
    print(f"  raw text (repr, first 1500 chars):")
    print(f"  {raw[:1500]!r}")

    cleaned = raw
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned.strip())
    try:
        json.loads(cleaned)
        print("  PARSES FINE with current fence-stripping -- not reproducible right now")
    except json.JSONDecodeError as e:
        print(f"  STILL FAILS: {e}")


client = anthropic.Anthropic(api_key=os.environ["PIPELINE_ANTHROPIC_API_KEY"])
for d in DOMAINS:
    diagnose(d, client)
