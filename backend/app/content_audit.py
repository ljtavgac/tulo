"""
Site-wide content quality audit: image completeness, image-relevance risk,
and AI-writing-tell detection, in one pass across every page.

Built after a real debugging session where a batch of ~130 wrong/missing
recipe photos and a hedge-phrase writing tell ("you're likely referring
to X" instead of a direct "X is...") only surfaced through many rounds of
a person clicking through the live site and reporting problems one at a
time. This formalizes that same reasoning into a repeatable check a
future content batch can run against BEFORE it reaches manual review,
instead of relying on that same manual process every time.

Three checks, two different enforcement strengths -- see each section
below for why:

1. Image completeness (does every page that needs a photo have one) is a
   hard yes/no fact, checked against the live database (image_url only
   ever exists there, not in seed_templates.py -- see _RUNTIME_IMAGE_KEYS).
2. AI-tell phrasing splits into BLOCK_PATTERNS (a small, near-zero-
   false-positive list -- verified against this site's own real content
   before being written down here, see each pattern's comment -- wired
   into seed_templates.py's existing import-time guard chain the same way
   as its double-dash check) and ADVISORY_PATTERNS (softer marketing-
   cliche constructions that need a human's judgment call, not an
   automatic block, since a false positive here would crash the app on
   startup for legitimate content -- see _check_no_ai_leakage_tells in
   seed_templates.py for the enforced half of this).
3. Image relevance risk is inherently a heuristic guess about whether a
   query/must_match pair is likely to surface a wrong-subject photo --
   useful to rank pages for review, never something to auto-block on: it
   flags real risk factors (homonym collision words, vessel-dominant
   queries, a weak/generic-only match term), not a certainty of an actual
   bad photo.

Run standalone with `python -m app.content_audit` for a full text report
against whatever DATABASE_URL is configured (exits 1 if anything needs
review, 0 if clean -- wire this into a batch-generation pipeline as a gate
before publishing), or hit /admin/content-audit for the same report as
JSON over HTTP.
"""

import re
import sys
from collections import Counter

from sqlalchemy.orm import Session

from .fetch_stock_images import (
    SINGLE_IMAGE_TEMPLATES,
    _DISH_VESSEL_STOPWORDS,
    _HOWTO_MUST_MATCH_STOPWORDS,
    _recipe_dish_must_match_terms,
)
from .images import is_allowed_image_url
from .models import Page

# ---------------------------------------------------------------------------
# 1. Image completeness -- a thin wrapper around the same missing/broken
#    logic /admin/image-audit already exposes, reused rather than
#    reimplemented so the two never drift into disagreeing with each other
#    about what counts as "this page needs a photo."
# ---------------------------------------------------------------------------


def check_image_completeness(db: Session) -> dict:
    missing: list[dict] = []
    broken: list[dict] = []

    def _check(url: str | None, **identity) -> None:
        if not url:
            missing.append(identity)
        elif not is_allowed_image_url(url):
            broken.append({**identity, "image_url": url})

    for page in db.query(Page).order_by(Page.id).all():
        content = page.content
        query_key = SINGLE_IMAGE_TEMPLATES.get(page.template_type)
        if query_key and query_key in content:
            _check(content.get("image_url"), slug=page.slug, template_type=page.template_type)
        elif page.template_type == "category_roundup":
            for card in content.get("recipe_cards", []):
                _check(card.get("image_url"), slug=page.slug, card=card.get("title"))

    return {"missing_count": len(missing), "missing": missing, "broken_count": len(broken), "broken": broken}


# ---------------------------------------------------------------------------
# 2. Image relevance risk -- formalizes the manual reasoning applied by
#    hand to every real wrong-photo bug found this session (a homonym or
#    idiom overpowering a search engine's loose keyword ranking, a query
#    dominated by container/vessel words, a match term too generic to
#    reject a wrong-subject photo) into a scan that runs unattended
#    against every page at once, instead of one page at a time only after
#    a person happens to notice and report it.
# ---------------------------------------------------------------------------

# Words with a strong, more common non-food meaning that can dominate a
# general-purpose stock-photo search -- every one of these is a real bug
# found by hand this session (small-potatoes' idiom, fruit-leather's
# material collision, root-beer-float's alcohol collision, sorrel-drink's
# herb collision, peach-fuzz's Pantone-color collision, sonic-ocean-water's
# literal-ocean collision, chocolate-gravy's savory-gravy assumption,
# beef-chuck's Chuck Taylor sneakers, colby-jack's jack-o-lantern,
# what-is-moonshine's literal moon). Not exhaustive -- a starting list to
# catch the same *pattern* elsewhere, meant to be extended as new
# collisions are found rather than treated as complete.
HOMONYM_RISK_WORDS = frozenset(
    {
        "leather", "beer", "ocean", "fuzz", "sorrel", "gravy", "mule", "bulldog",
        "float", "small", "ranch", "blue", "chuck", "jack", "colby", "kasha",
        "dip", "bake", "roll", "bar", "ball", "bomb", "sauce", "punch", "smash",
        "mocktail", "dust", "butter", "milk", "cream", "chip", "cake", "pie",
        "moonshine", "navel", "mudslide",
    }
)


def _looks_branded_or_place(title: str) -> bool:
    """A capitalized word mid-title that isn't the title's first word is
    otherwise unremarkable (title case is universal here) -- but a
    digit-letter mix ("Heinz 57") or a bare number is a real signal, the
    same pattern behind Heinz 57 Copycat Sauce and Dubai Chocolate Bar
    both needing their brand name de-branded out of the search query."""
    words = title.replace("'s", "").split()
    for w in words:
        if re.match(r"^[A-Z][a-z]+\d+$", w) or re.match(r"^\d+$", w):
            return True
    return False


def _build_word_frequency(pages: list[dict]) -> Counter:
    freq: Counter = Counter()
    for p in pages:
        c = p["content"]
        bits = [p["title"]]
        if p["template_type"] == "recipe_or_dish":
            for ing in c.get("ingredients", []):
                bits.append(ing.get("name", ""))
        for t in bits:
            for w in re.findall(r"[a-z']+", t.lower()):
                if len(w) > 2:
                    freq[w] += 1
    return freq


def scan_image_relevance_risk(pages: list[dict]) -> list[dict]:
    """Returns one entry per single-image page that trips at least one
    risk signal, ranked by how many signals it tripped. Callers should
    treat score>=2 (multiple risk factors stacked) as the actual review
    list and score==1 as low-confidence/informational only -- verified
    against this site's real ~2,100 pages: a single signal alone fires on
    over 900 pages (mostly "weak_generic_match_only", which is this
    site's own intentional default for a recipe_or_dish page that's never
    needed a stricter override -- see _recipe_dish_must_match_terms'
    docstring -- not itself evidence of a bad photo), while every real
    wrong-photo bug found and fixed by hand this session had at least two
    factors stacked together (e.g. a homonym-risk word in the query AND
    no strict match protecting against it). See run_full_audit, which
    applies this same score>=2 split to the report it returns. Never a
    substitute for a human actually looking at the photo -- see this
    module's own docstring."""
    freq = _build_word_frequency(pages)
    common_words = {w for w, c in freq.items() if c >= 15}  # appears in 15+ places sitewide

    results = []
    for p in pages:
        tt = p["template_type"]
        if tt not in SINGLE_IMAGE_TEMPLATES:
            continue
        c = p["content"]
        query_key = SINGLE_IMAGE_TEMPLATES[tt]
        query = c.get(query_key)
        if not query or c.get("unpublished"):
            continue

        signals = []

        title_words = [w for w in re.findall(r"[a-z']+", p["title"].lower()) if len(w) > 2]
        rare = [w for w in title_words if freq.get(w, 0) <= 2]
        if rare and len(rare) >= max(1, len(title_words) - 1):
            signals.append(f"rare_title_words:{rare}")

        query_words = set(re.findall(r"[a-z']+", query.lower()))
        title_words_set = set(title_words)
        hits = (query_words | title_words_set) & HOMONYM_RISK_WORDS
        if hits:
            signals.append(f"homonym_risk:{sorted(hits)}")

        vessel_hits = query_words & _DISH_VESSEL_STOPWORDS
        if len(vessel_hits) >= 2:
            signals.append(f"vessel_dominant:{sorted(vessel_hits)}")

        existing_mm = c.get("hero_image_must_match") or c.get("salient_ingredient_must_match")
        if tt == "recipe_or_dish":
            salient = c.get("salient_ingredient_query")
            derived = _recipe_dish_must_match_terms(salient or query)
            effective = existing_mm or derived
        else:
            effective = existing_mm or p["title"]
        if effective:
            eff_words = effective if isinstance(effective, (list, tuple)) else [effective]
            eff_words_flat: set[str] = set()
            for term in eff_words:
                eff_words_flat |= set(re.findall(r"[a-z']+", term.lower()))
            if eff_words_flat and eff_words_flat <= common_words:
                signals.append("weak_generic_match_only")
        else:
            signals.append("no_match_check_at_all")

        if _looks_branded_or_place(p["title"]):
            signals.append("branded_or_place_title")

        if signals:
            results.append(
                {
                    "slug": p["slug"],
                    "template_type": tt,
                    "title": p["title"],
                    "query": query,
                    "must_match": c.get("hero_image_must_match"),
                    "salient_query": c.get("salient_ingredient_query"),
                    "signals": signals,
                    "score": len(signals),
                }
            )

    results.sort(key=lambda r: -r["score"])
    return results


# ---------------------------------------------------------------------------
# 3. AI-tell phrasing
# ---------------------------------------------------------------------------

# Each entry: (label, compiled regex, scope). scope "start" only flags a
# match in the first ~80 characters of a string (a sentence-opener
# construction) -- "anywhere" flags it wherever it appears. "start" is used
# specifically for constructions that are also completely ordinary English
# in the middle of a sentence (see BLOCK_PATTERNS' own comment on
# "referring to") and would false-positive constantly if checked
# unrestricted; every "anywhere" pattern below was checked against this
# site's real, current content and found zero legitimate hits before being
# added (see the audit session that built this file).
_START_WINDOW = 80


def _compile(patterns: list[tuple[str, str, str]]) -> list[tuple[str, re.Pattern, str]]:
    return [(label, re.compile(pattern, re.IGNORECASE), scope) for label, pattern, scope in patterns]


# Near-zero-false-positive: verified against this site's actual content
# (2,109 pages) with zero legitimate matches before being added here.
# Wired into seed_templates.py's import-time guard chain (see
# _check_no_ai_leakage_tells there) the same way as its double-dash
# check -- a batch that reintroduces one of these fails loudly at startup
# instead of quietly reaching the live site.
BLOCK_PATTERNS = _compile(
    [
        # The exact tell reported live: a definitional field hedging about
        # what the reader probably means instead of just stating the
        # answer ("Moonshine is..."), a real instance found and since
        # fixed on a page whose slug wasn't recorded before the fix landed.
        # "referring to" alone is NOT here -- confirmed common and
        # legitimate mid-sentence across dozens of real etymology
        # explanations ("...referring to the meat rotating on a spit") --
        # only the hedge-at-the-start-of-an-answer shape is the tell.
        ("hedge_referring_to_opener", r"^.{0,10}you'?re (?:likely|probably|most likely) referring to", "start"),
        ("hedge_referring_to_opener_2", r"^.{0,10}you (?:might|may|could) be referring to", "start"),
        ("hedge_referring_to_opener_3", r"^.{0,10}it seems (?:like )?you'?re referring to", "start"),
        # Direct model-identity/meta leakage -- never appropriate in
        # published site copy under any phrasing.
        ("ai_identity_leakage", r"\bas an ai\b|\blanguage model\b|\bas a large language model\b", "anywhere"),
        ("training_cutoff_leakage", r"as of my (?:last )?(?:training|knowledge) (?:data|update|cutoff)", "anywhere"),
        ("chat_closing_leakage", r"\bi hope this helps\b|\bi hope that helps\b", "anywhere"),
        ("browsing_refusal_leakage", r"i (?:cannot|can'?t) browse the (?:internet|web)", "anywhere"),
    ]
)

# Softer marketing-cliche constructions -- real AI tells, but common
# enough in low-effort human copywriting too that a false positive is
# plausible, so these are advisory (reported for review) rather than an
# automatic build-breaking failure. Also verified against current content
# with zero hits before being added, but kept advisory rather than
# blocking since that's a much smaller sample than a future 500-page
# batch will produce.
ADVISORY_PATTERNS = _compile(
    [
        ("marketing_hook_whether_youre", r"\bwhether you'?re an? \w+ or\b", "anywhere"),
        ("marketing_elevate", r"\belevate (?:your|any)\b", "anywhere"),
        ("marketing_unlock", r"\bunlock (?:a|the)\b", "anywhere"),
        ("marketing_unleash", r"\bunleash\b", "anywhere"),
        ("marketing_next_level", r"\bnext level\b|\bto the next level\b", "anywhere"),
        ("marketing_game_changer", r"\bgame[- ]changer\b", "anywhere"),
        ("marketing_must_try", r"\bmust[- ]try\b", "anywhere"),
        ("marketing_symphony_tapestry", r"\ba symphony of\b|\btapestry of\b", "anywhere"),
        ("marketing_testament", r"(?:stands as |is )?a testament to\b", "anywhere"),
        ("marketing_todays_world", r"in today'?s (?:fast-paced )?world\b", "anywhere"),
        ("marketing_realm_of", r"\bin the realm of\b", "anywhere"),
        ("marketing_look_no_further", r"\blook no further\b", "anywhere"),
        ("marketing_embark", r"\bembark on\b", "anywhere"),
        ("marketing_boasts", r"\bboasts an?\b", "anywhere"),
        ("not_only_but_also", r"\bnot only\b.{0,60}\bbut also\b", "anywhere"),
        ("hedge_worth_noting", r"\bit'?s (?:important|worth) (?:to note|noting)\b", "anywhere"),
        ("essay_conclusion_opener", r"^(?:in conclusion|to sum up|in summary),", "start"),
        ("essay_dive_delve_opener", r"^(?:dive|delve) into\b", "start"),
    ]
)


def _walk_strings(value, location: str):
    """Yields (location, text) for every string value nested anywhere in
    `value` -- same shape as seed_templates.py's _find_double_dashes'
    inline walker, generalized here so this module doesn't need to
    reimplement it per check."""
    if isinstance(value, str):
        yield location, value
    elif isinstance(value, dict):
        for key, sub_value in value.items():
            yield from _walk_strings(sub_value, f"{location}.{key}")
    elif isinstance(value, list):
        for i, sub_value in enumerate(value):
            yield from _walk_strings(sub_value, f"{location}[{i}]")


def _scan_patterns(pages: list[dict], patterns: list[tuple[str, re.Pattern, str]]) -> list[dict]:
    hits = []
    for page in pages:
        for location, text in _walk_strings(page["content"], page["slug"]):
            window = text[:_START_WINDOW]
            for label, pattern, scope in patterns:
                haystack = window if scope == "start" else text
                m = pattern.search(haystack)
                if m:
                    hits.append({"slug": page["slug"], "location": location, "pattern": label, "excerpt": text[:160]})
    return hits


def scan_ai_tells(pages: list[dict]) -> dict:
    return {
        "blocking": _scan_patterns(pages, BLOCK_PATTERNS),
        "advisory": _scan_patterns(pages, ADVISORY_PATTERNS),
    }


# ---------------------------------------------------------------------------
# 4. Orchestration
# ---------------------------------------------------------------------------


def run_full_audit(db: Session) -> dict:
    from .seed_templates import SEED_PAGES  # deferred: seed_templates' own import-time

    # checks must run first (they already did, at process startup) before
    # this module trusts SEED_PAGES as a clean baseline for the two
    # content-only scans below.

    image_completeness = check_image_completeness(db)
    image_risk = scan_image_relevance_risk(SEED_PAGES)
    ai_tells = scan_ai_tells(SEED_PAGES)

    # See scan_image_relevance_risk's own docstring for why score>=2 is the
    # real review list and score==1 is informational-only noise.
    image_risk_review = [r for r in image_risk if r["score"] >= 2]
    image_risk_low_confidence = [r for r in image_risk if r["score"] == 1]

    clean = (
        image_completeness["missing_count"] == 0
        and image_completeness["broken_count"] == 0
        and not ai_tells["blocking"]
    )
    return {
        "clean": clean,
        "image_completeness": image_completeness,
        "image_relevance_risk": {
            "review_count": len(image_risk_review),
            "review": image_risk_review,
            "low_confidence_count": len(image_risk_low_confidence),
            "low_confidence": image_risk_low_confidence,
        },
        "ai_tells": {
            "blocking_count": len(ai_tells["blocking"]),
            "blocking": ai_tells["blocking"],
            "advisory_count": len(ai_tells["advisory"]),
            "advisory": ai_tells["advisory"],
        },
    }


if __name__ == "__main__":
    from .database import SessionLocal

    session = SessionLocal()
    try:
        report = run_full_audit(session)
    finally:
        session.close()

    print(f"Image completeness: {report['image_completeness']['missing_count']} missing, "
          f"{report['image_completeness']['broken_count']} broken")
    print(f"Image relevance risk: {report['image_relevance_risk']['review_count']} page(s) worth reviewing "
          f"({report['image_relevance_risk']['low_confidence_count']} more single-signal, informational only)")
    print(f"AI tells: {report['ai_tells']['blocking_count']} blocking, "
          f"{report['ai_tells']['advisory_count']} advisory")

    if report["ai_tells"]["blocking"]:
        print("\nBLOCKING AI-tell matches (must fix before this batch ships):")
        for hit in report["ai_tells"]["blocking"][:20]:
            print(f"  [{hit['pattern']}] {hit['slug']} ({hit['location']}): {hit['excerpt']!r}")

    if report["ai_tells"]["advisory"]:
        print("\nAdvisory AI-tell matches (human judgment call, not auto-blocked):")
        for hit in report["ai_tells"]["advisory"][:20]:
            print(f"  [{hit['pattern']}] {hit['slug']} ({hit['location']}): {hit['excerpt']!r}")

    if report["image_completeness"]["missing"]:
        print(f"\nMissing images (first 20 of {report['image_completeness']['missing_count']}):")
        for m in report["image_completeness"]["missing"][:20]:
            print(f"  {m}")

    if report["image_relevance_risk"]["review"]:
        print(f"\nImage relevance risk -- worth reviewing (first 20 of {report['image_relevance_risk']['review_count']}):")
        for r in report["image_relevance_risk"]["review"][:20]:
            print(f"  [{r['score']}] {r['slug']} ({r['template_type']}): {r['signals']}")

    sys.exit(0 if report["clean"] else 1)
