"""
Maintenance script: fills in real stock photos (via images.py) for every
page that's missing one. Run manually, same pattern as seed_templates.py --
not an HTTP endpoint, since this hits free-tier external APIs and doesn't
need its own auth/rate-limit surface for what's fundamentally an occasional
batch operation.

No-ops safely with a clear message if no API keys are configured (see
images.py) -- safe to run at any time, keys present or not.

Usage:
    python -m app.fetch_stock_images            # skip pages that already have an image
    python -m app.fetch_stock_images --force     # re-fetch and overwrite existing images

Recipe, Ingredient Hub, How-To, Definition, Comparison, and Substitute
(single hero image) and Category Roundup (one image per recipe card) have
an image slot in their template -- Homepage and Tool pages don't, so
they're skipped entirely.

Searches run concurrently across pages (see CONCURRENCY below) -- this used
to be a strict for-loop, one page at a time, which was fine at a couple
hundred pages but became a real problem once the content queue reached
~2,000: a single-threaded pass could take hours, and (run as a background
task from main.py's startup hook, see lifespan()) kept getting restarted
from zero by the next deploy before it ever finished a pass. Each worker
does only network calls and pure Python (never touches the SQLAlchemy
session, which isn't thread-safe) -- the main thread is the only place
that ever reads or writes to `db`, applying each worker's already-computed
result after the fact.
"""

import copy
import random
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session

from .database import SessionLocal
from .images import _is_reachable, is_allowed_image_url, search_image, ping_download, UNSPLASH_ACCESS_KEY, PEXELS_ACCESS_KEY
from .models import Page

# How many pages' worth of Unsplash/Pexels searches run at once.
#
# INCIDENT (2026-09-09): shipped at 8 for the first run against the full
# ~2,000-page backlog and took production down. 8 concurrent workers, each
# also doing a real GET per candidate via images._is_reachable(), blew
# through Pexels' free-tier rate limit almost immediately (confirmed via a
# live 429 in the Render logs) -- and with only Pexels configured (no
# Unsplash key), every one of ~1,900 pages needing a first-ever fetch hit
# it at once. Render's free tier (0.1 CPU/512MB) has very limited CPU; that
# many threads doing simultaneous network I/O + JSON parsing was enough to
# starve the single process's ability to serve real requests, surfacing as
# the whole site returning server errors, not just a slow image backfill.
# Dropped to 1 (fully sequential) as an immediate stop-the-bleeding measure,
# and paired with the rate_limited short-circuit in fetch_images() below --
# once any worker sees a 429, every other worker bails instead of piling on
# an API that's already throttling this process.
#
# Raised back up (still 2026-09-09) now that both of the conditions that
# caused the incident have changed: the rate-limit short-circuit above
# means a run that starts getting 429'd stops within one request per
# worker instead of continuing to hammer Pexels, and the Render instance
# has since been upgraded from the free tier to 1 CPU/2GB (10x the CPU, 4x
# the RAM). Went to 4 first as a deliberately moderate step, short of the
# 8 that caused the outage on hardware with an order of magnitude less
# headroom.
#
# Raised again to 6, same day, after the two things that made 4 the
# cautious choice both got addressed separately: the site-wide "still
# laggy at times" investigation found and fixed the real per-request CPU
# cost this concurrency lever was competing against (full, uncached
# full-table scans on every page view -- see main.py's _cached_pages and
# the /pages `lean` mode), so there's now real, confirmed headroom on the
# same request-serving path this once threatened to starve. Still short
# of 8 -- there's no need to return all the way to the exact number that
# caused a real production incident just because the two root causes are
# fixed; 6 clears the backlog faster with a smaller step.
CONCURRENCY = 6

# template_type -> the content key holding the search query for a single
# hero image.
SINGLE_IMAGE_TEMPLATES = {
    "recipe_or_dish": "hero_image_query",
    "ingredient_hub": "hero_image_query",
    "howto_technique": "hero_image_query",
    "definition": "hero_image_query",
    "comparison": "hero_image_query",
    "substitute": "hero_image_query",
    "static_page": "hero_image_query",
}

# Templates whose image represents a finished, plated dish rather than a raw
# ingredient or an in-progress technique shot. A bare dish name (e.g.
# "eggplant parmesan") searched against a general-purpose stock site often
# surfaces the raw ingredient or a generic product shot as the top match --
# appending a food-styling qualifier biases toward an actual prepared dish.
# Ingredient Hub/Definition/How-To keep the plain query: a raw or in-progress
# shot is the *correct* image there, not a bug to work around.
DISH_TEMPLATES = {"recipe_or_dish", "category_roundup"}


def _search_query_for(template_type: str, raw_query: str) -> str:
    if template_type in DISH_TEMPLATES:
        return f"{raw_query} plated dish"
    return raw_query


def _category_fallback_query(page_title: str) -> str:
    """A broader query to fall back to when a recipe card's own specific
    dish name (e.g. "nasu dengaku") has no match on Unsplash/Pexels -- a
    thin free-tier catalog is far more likely to have a photo for the
    parent category (e.g. "eggplant", from the page title "Eggplant
    Recipes") than for a niche regional dish name."""
    return re.sub(r"\s+recipes?$", "", page_title, flags=re.IGNORECASE).strip()


def _definition_fallback_query(page_title: str) -> str:
    """"What Is Tahini? (And How to Use It)" -> "Tahini" -- strips the
    boilerplate question framing down to just the term itself, which is
    both a plainer and broader query than whatever specific shot
    hero_image_query asked for (e.g. "tahini paste jar")."""
    term = re.sub(r"^what is\s+", "", page_title, flags=re.IGNORECASE)
    return re.split(r"[?(]", term)[0].strip()


def _howto_fallback_query(page_title: str) -> str:
    """"How to Cut a Watermelon" -> "Watermelon" -- strips the leading "How
    to <verb>" and any article, leaving just the food/equipment noun a
    stock site is actually likely to have a photo of, rather than the
    specific in-progress action shot hero_image_query asked for."""
    rest = re.sub(r"^how to\s+\S+\s+", "", page_title, flags=re.IGNORECASE)
    return re.sub(r"^(a|an|the)\s+", "", rest, flags=re.IGNORECASE).strip()


# Words this derivation strips only from the *must_match* value, never from
# the query text above -- a search engine tolerates (even benefits from)
# extra context words, but images._is_relevant()'s exact-substring check
# doesn't, and this derivation's single-word verb-strip only handles the
# simple "How to <verb> <object>" shape. A title with a compound verb
# ("How to Tell If..."), a trailing modifier ("...Fast", "...Quickly"), or
# a prepositional tail ("...in the Fridge", "...on the Stove") leaves that
# filler in _howto_fallback_query's own result, which becomes an
# effectively unmatchable required term (see how-to-tell-if-eggs-are-good,
# whose naive result was "If Eggs Are Good" -- no real photo's alt text
# will ever contain that phrase). This list also drops non-visual judgment
# words (good/bad/safe/ripe's opposite "eating"/"lasts") that a
# photographer would never caption a photo with, and kitchen-location/
# appliance words (stove/oven/microwave/refrigerator/fridge) that describe
# *where* the technique happens, not what the photo needs to show -- see
# _howto_must_match_term's own real-world example (found live: "Popcorn
# Stove" required "stove" to appear in a stovetop-popcorn photo's alt
# text, which it essentially never does; "Popcorn" alone matches).
_HOWTO_MUST_MATCH_STOPWORDS = frozenset({
    "a", "an", "the", "to", "of", "in", "on", "at", "from", "for", "out",
    "with", "without", "if", "is", "are", "be", "still", "fast", "quickly",
    "every", "most", "and", "get", "much", "youll", "before", "after",
    "while", "know", "how", "your", "again", "back", "up", "down", "over",
    "into", "onto", "so", "just", "it", "its", "good", "bad", "eating",
    "home", "long", "lasts", "stays", "safe", "eat",
    "stove", "oven", "microwave", "refrigerator", "fridge", "ripe", "word",
})


def _howto_must_match_term(fallback_term: str) -> str | None:
    """Cleans up _howto_fallback_query's result specifically for use as a
    must_match value (see _HOWTO_MUST_MATCH_STOPWORDS above for why the
    query text itself is left alone). Returns None -- skip the relevance
    check for this attempt entirely, the same policy recipe_or_dish already
    uses when no reliable subject term exists -- when nothing substantial
    survives, or when more than 3 words do: a long remainder is a sign this
    title's shape didn't reduce to one clean noun phrase, and forcing an
    unreliable multi-word exact-match requirement is worse than not
    checking at all."""
    words = [w for w in re.findall(r"[A-Za-z']+", fallback_term) if w.lower().replace("'", "") not in _HOWTO_MUST_MATCH_STOPWORDS]
    if not words or len(words) > 3:
        return None
    return " ".join(words)


def _howto_relaxed_terms(must_match_term: str | None) -> tuple[str, ...] | None:
    """Last-resort relaxed attempt once the (already-cleaned) must_match
    term itself has been tried and failed -- same pattern and rationale as
    _ingredient_hub_relaxed_term below, generalized to howto_technique.

    A 2-3 word must_match term is still often too specific: real alt text
    rarely contains an exact multi-word phrase, especially since this
    derivation can't always tell which word order the title implies (e.g.
    "How to Get the Most Juice Out of a Lemon" reduces to "Juice Lemon",
    but a real photo's alt text is far more likely to say "lemon" alone,
    or "lemon juice" -- never "juice lemon" as an ordered phrase). Rather
    than guess which single word is "the" head noun (position isn't
    consistent enough across titles to get that right generally -- see
    "Pork Butt" vs. "Juice Lemon", where the photographable subject is
    the first word in one and the last in the other), this returns every
    word as an OR-tuple: images._is_relevant() already treats a tuple as
    "any one of these is an acceptable match" for comparison pages, so a
    photo matching on just "lemon" (out of "Juice Lemon") or just "pork"
    (out of "Pork Butt") now correctly passes at this final, most
    permissive tier -- exactly the retry a real audit of stuck pages
    called for.

    Returns None when the term is already a single word (nothing left to
    relax) or absent."""
    if not must_match_term:
        return None
    words = must_match_term.split()
    return tuple(words) if len(words) > 1 else None


# Container/vessel words that are themselves common, legitimate stock-photo
# subjects in their own right -- a search engine can rank a photo of just
# the empty pan/bowl/skillet as a strong keyword match for a query that
# only mentions it as *how* the dish is served, not what it visually is.
# Confirmed live: one-pan-mexican-chicken-and-rice's query ("mexican
# chicken skillet with rice and melted cheese") returned a photo the user
# reported as showing the pan, not the chicken and rice -- and 252 of 929
# recipe_or_dish hero_image_query strings contain a word from this list, so
# this isn't a one-off. Excluded from _recipe_dish_must_match_terms' result
# below so a container-only photo can't satisfy the relevance check just
# because the query happens to mention "skillet"/"bowl"/etc -- distinct
# from _HOWTO_MUST_MATCH_STOPWORDS (generic function words), used alongside
# it there.
_DISH_VESSEL_STOPWORDS = frozenset({
    "skillet", "pan", "pot", "casserole", "dish", "bowl", "tray", "sheet",
    "baking", "dutch", "oven", "cast", "iron", "instant", "slow", "cooker",
    "crock", "crockpot", "wok", "saucepan", "griddle", "mason", "jar",
    "glass", "plate", "platter", "cutting", "board", "container",
    "containers", "foil", "table",
})


def _recipe_dish_must_match_terms(query: str) -> tuple[str, ...] | None:
    """Derives a lenient OR-tuple of required content words from a recipe's
    own hero_image_query, for use as images.py's must_match.

    recipe_or_dish otherwise has no relevance check at all (see
    SINGLE_IMAGE_FALLBACKS' own comment on why it's deliberately left out
    of that dict -- requiring the *exact* dish name risks false-rejecting a
    perfectly good photo whose alt text just doesn't happen to repeat it).
    That blanket skip is also what let a real bug through uncaught: nothing
    ever checked a candidate photo's alt text actually mentioned the food
    itself, only the search engine's own loose keyword ranking (see
    images._is_relevant()'s docstring for other, previously-confirmed live
    examples of that same failure mode on other templates).

    This isn't the exact-dish-name check that comment warns against: after
    stripping _HOWTO_MUST_MATCH_STOPWORDS (generic function words) and
    _DISH_VESSEL_STOPWORDS (pan/skillet/bowl/etc, themselves common
    stock-photo subjects a container-only photo could otherwise satisfy),
    what's left is returned as an OR-tuple, not a required exact phrase --
    a genuine photo of the dish only needs its alt text to mention *any
    one* of these words (e.g. just "chicken", or just "rice"), the same
    low-risk, broad-match reasoning _howto_relaxed_terms already relies on.

    Returns None (skip the check entirely, same as recipe_or_dish's
    existing default) when nothing usable survives -- e.g. a query that
    reduces to only container/stopwords."""
    words: list[str] = []
    seen: set[str] = set()
    for word in re.findall(r"[a-z']+", query.lower()):
        word = word.strip("'")
        if not word or word in _HOWTO_MUST_MATCH_STOPWORDS or word in _DISH_VESSEL_STOPWORDS:
            continue
        if word not in seen:
            seen.add(word)
            words.append(word)
    return tuple(words) if words else None


def _substitute_fallback_query(page_title: str) -> str:
    """"Best Substitutes for Baking Soda" -> "Baking Soda"."""
    return re.sub(r"^best substitutes?\s+for\s+", "", page_title, flags=re.IGNORECASE).strip()


def _ingredient_hub_fallback_query(page_title: str) -> str:
    """The page's title IS already the bare ingredient name (e.g. "Milano
    Cookies", "Chives") -- unlike the other three below, there's no
    boilerplate framing to strip. Kept here anyway (as the identity
    function) purely so this template type gets a must_match term wired
    up through the exact same path as the others -- see
    images._is_relevant()'s docstring: a real wrong-subject photo (an
    unrelated stock image) got written for milano-cookies the same way it
    did for how-to-cook-beets and best-substitutes-for-butter, just
    without a fallback function to hang the fix on until now."""
    return page_title


def _ingredient_hub_relaxed_term(page_title: str) -> str:
    """Last word of the title -- the head noun ("Milano Cookies" ->
    "Cookies", "Celtic Salt" -> "Salt", "Bread Flour" -> "Flour") -- a
    last-resort, looser query+must_match pair tried only after the exact
    title itself comes up with nothing. Confirmed necessary for real: even
    after the identity fallback above, milano-cookies found no match for
    "Milano Cookies" on Pexels (the only provider configured at the time)
    -- a specific branded product name genuinely isn't tagged on a generic
    stock site the way a plain ingredient name is. A representative
    "cookies" photo beats no photo at all for a page like this."""
    words = page_title.strip().split()
    return words[-1] if words else page_title


# template_type -> a function deriving the page's single core-subject term,
# used two ways: as a broader fallback query when the template's own
# hero_image_query (a specific shot description) has no stock match, AND
# (via _apply_result's must_match, checked against every query attempt, not
# just the fallback) as the term a candidate photo's own alt/description
# text must actually contain -- see images._is_relevant(). recipe_or_dish
# isn't here: a specific dish name (e.g. "lomo saltado") often genuinely
# doesn't appear in a real, correct photo's own alt text the way an
# ingredient's bare name does, so requiring the exact title risks
# false-rejecting already-good matches rather than catching bad ones --
# unlike the four template types below, where the term is either exactly
# the page's own title (ingredient_hub) or a short, mechanical strip of
# fixed boilerplate. recipe_or_dish still gets a relevance check (see its
# own branch in fetch_images(), using _recipe_dish_must_match_terms), just
# not this single-term-per-title shape: a lenient OR-tuple of the query's
# own content words instead of one required exact phrase.
SINGLE_IMAGE_FALLBACKS = {
    "definition": _definition_fallback_query,
    "howto_technique": _howto_fallback_query,
    "substitute": _substitute_fallback_query,
    "ingredient_hub": _ingredient_hub_fallback_query,
}


def _needs_fetch(url: str | None, revalidate: bool) -> bool:
    """False only for a URL that's present, on an allowed host, and (when
    revalidate is on) still actually loads -- true for everything else:
    missing, wrong host, or (revalidate only) dead at the source. The one
    check every "does this page/card need a fetch" decision in this module
    should go through, so `force`/`revalidate` semantics stay identical
    between the single-image branch and the category_roundup card branch
    rather than each reimplementing its own version and drifting apart."""
    if not is_allowed_image_url(url):
        return True
    return revalidate and not _is_reachable(url)


class _UsedUrls:
    """Thread-safe wrapper around the set of photo URLs already claimed in
    this run -- see fetch_images()'s used_urls docstring for why this needs
    to be shared across pages at all. Plain set() isn't safe to read
    (snapshot for exclude_urls) and write (add on a match) from multiple
    worker threads at once without this: two threads racing between the
    snapshot and the add could both claim the literal same photo for two
    different pages, the exact bug used_urls exists to prevent, just
    reintroduced by concurrency instead of by a missing set."""

    def __init__(self) -> None:
        self._urls: set[str] = set()
        self._lock = threading.Lock()

    def snapshot(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._urls)

    def add(self, url: str) -> None:
        with self._lock:
            self._urls.add(url)


def _apply_result(
    content: dict,
    attempts: list[tuple[str, str | None]],
    template_type: str,
    used_urls: "_UsedUrls",
    extra_exclude: frozenset[str] = frozenset(),
) -> bool:
    """Tries each (query, must_match) pair in `attempts`, in order, and
    writes image_url/image_attribution into `content` in place from the
    first one that finds a result. Returns True if it found and wrote one.

    Each attempt carries its own must_match rather than one fixed term for
    the whole call, so a caller can progressively relax the required
    subject term across attempts (see _ingredient_hub_relaxed_term) instead
    of only ever trying alternate query text at one fixed strictness.
    must_match, when not None, is checked by images.py's _is_relevant() --
    see its docstring for why this exists: a search API can return a
    wrong-subject photo for the *primary* query just as easily as for a
    fallback one (that's exactly what happened for how-to-cook-beets,
    where "roasted beets whole on baking sheet" itself, not a fallback,
    returned a roasted turkey).

    `extra_exclude` is separate from `used_urls` (which tracks photos
    claimed by *other* pages this run): it's for excluding this same
    page's own current, presumably-wrong photo on a targeted re-fetch --
    see the caller for why that's needed. must_match alone doesn't
    reliably prevent re-selecting it: _is_relevant() intentionally accepts
    a photo with blank alt/description text regardless of must_match (see
    its own docstring), so a low-effort stock photo with no description
    can keep winning the same search on every re-run even with a required
    subject term set, exactly what happened on what-is-boudin.

    Called from within a worker thread (see fetch_images) -- touches only
    `content` (a deep copy local to this page, per-worker, never shared)
    and `used_urls` (its own internal lock), never the SQLAlchemy session."""
    for query, must_match in attempts:
        search_query = _search_query_for(template_type, query)
        result = search_image(search_query, exclude_urls=used_urls.snapshot() | extra_exclude, must_match=must_match)
        if result is None:
            print(f"    no result for '{search_query}'" + (f" (must mention {must_match!r})" if must_match else ""))
            continue
        content["image_url"] = result.url
        content["image_attribution"] = {
            "photographer": result.photographer,
            "photographer_url": result.photographer_url,
            "source": result.source,
        }
        if result.source == "unsplash" and result.download_location:
            ping_download(result.download_location)
        used_urls.add(result.url)
        return True
    return False


def fetch_images(
    db: Session,
    force: bool = False,
    only_slugs: set[str] | None = None,
    revalidate: bool = False,
) -> tuple[int, int]:
    """Returns (pages_updated, images_written).

    `only_slugs`, when given, restricts the run to exactly those pages and
    always re-fetches them (as if `force` were true just for them) -- for
    redoing a specific page whose photo is wrong (not missing, not broken,
    just a bad match) without touching, and risking re-rolling, every other
    page's already-correct photo the way a site-wide force run would. A
    slug in this set also matches a category_roundup *card* by its own
    slug, not just a top-level Page.slug -- a card's photo is nested
    inside its parent collection page's own row, so without this a caller
    asking to redo one specific dish's card (as opposed to its standalone
    recipe page, a different row entirely) would silently no-op: the
    collection page's own slug wouldn't be in only_slugs, so the whole
    page -- card included -- would get skipped by the top-level filter
    below before ever reaching the card loop. Confirmed as a real bug via
    char-siu's chinese-recipes card: an admin re-fetch scoped to
    `slugs=char-siu` refreshed the standalone recipe page (a real, useful
    photo) while leaving the card's own separately-fetched, since-dead
    photo completely untouched, because the two live in different Page
    rows and only one of those rows matched the filter.

    `revalidate`, when true, treats an existing image_url as needing a
    fresh fetch if it's simply no longer reachable, not just missing or on
    a disallowed host. images.py's own _is_reachable() already guards
    against writing a dead URL in the first place (checked once, at the
    moment a candidate is selected) -- but a photo can still be taken down
    at the source *after* it was fetched and validated, with nothing to
    catch that later than a human noticing a missing photo (StockPhotoSlot
    hides a failed image load rather than showing a broken-image icon).
    Off by default since it costs one real network request per
    already-valid image already in the database, unlike the cheap
    string-only check every other run does -- meant to be run
    periodically (e.g. a scheduled weekly call to
    /admin/fetch-images?revalidate=true) as the actual mechanism that
    catches this class of decay without requiring a bug report first, the
    same way `force` costs more than the default run and is used
    deliberately rather than on every call.
    """
    pages_updated = 0
    images_written = 0
    # Shared across the whole run so two different pages/cards never end up
    # with the literally same photo -- see search_image()'s exclude_urls.
    used_urls = _UsedUrls()
    # Set the moment any worker sees a 429 from a provider -- every worker
    # checks this before starting its own search and bails out immediately
    # if it's set (see CONCURRENCY's incident note above). Without this, a
    # run that starts getting rate-limited keeps right on submitting a
    # request per remaining page anyway, each one doomed to fail the same
    # way, for no reason but to burn time and process resources a real
    # request could have used instead.
    rate_limited = threading.Event()

    # A standalone recipe_or_dish page and its parent category_roundup's
    # card for that same dish (e.g. carne-asada-tacos and taco-recipes'
    # "Carne Asada Tacos" card) search the exact same query text. Whichever
    # is processed first claims the one available match via used_urls and
    # leaves the other to fall back to a broader term -- and a thin
    # free-tier catalog for a niche dish name can easily have exactly one
    # good match, or exhaust even the broader category fallback once
    # several cards in the same collection have already tried it. The
    # recipe page is the primary content people land on and share and
    # needs a real hero photo; a card missing one just renders without an
    # image (see StockPhotoSlot) -- not a broken page. So single-hero-image
    # pages are run to completion, and get first claim on scarce matches,
    # as their own concurrent phase before category_roundup pages' phase
    # starts -- not just sorted within one shared pool, which concurrency
    # would let race against each other and defeat this ordering.
    all_pages = db.query(Page).all()
    single_image_pages = [p for p in all_pages if SINGLE_IMAGE_TEMPLATES.get(p.template_type)]
    category_roundup_pages = [p for p in all_pages if p.template_type == "category_roundup"]
    # db.query(Page).all() with no order_by comes back in a stable order
    # (insertion/primary-key order in practice) every single call -- so
    # every recurring pass (see main.py's _run_periodic_image_fetch) hit
    # the same pages first, in the same order, every time. Harmless once
    # the backlog is small, but at today's ~1,000-page backlog and a
    # provider rate limit that caps how many pages one pass can even
    # attempt, that meant whichever pages happened to sort first got every
    # pass's full attempt budget while pages further back never got a
    # single try. Shuffled within each phase (never across the two -- see
    # the phase-ordering comment above) so a genuinely fixable page isn't
    # permanently starved by sorting behind a page that keeps failing for
    # reasons no retry fixes (see fetch_images()'s own docstring on thin
    # free-tier catalogs).
    random.shuffle(single_image_pages)
    random.shuffle(category_roundup_pages)

    def process_single_image_page(page: Page) -> tuple[Page, dict | None, int]:
        """Pure computation + network calls only -- never touches `db` or
        any other SQLAlchemy state, so it's safe to run in a worker thread.
        Returns (page, new_content_or_None_if_unchanged, images_written_delta);
        the caller applies the result back onto `page` in the main thread."""
        if rate_limited.is_set():
            return page, None, 0
        if only_slugs is not None and page.slug not in only_slugs:
            return page, None, 0
        force_this_page = (force and only_slugs is None) or (only_slugs is not None)

        # A deep copy, not a reference: mutating page.content directly would
        # change the "before" value SQLAlchemy compares against too, since
        # it'd be the same object -- then the reassignment in the main
        # thread looks like a no-op and it silently never emits the UPDATE.
        content = copy.deepcopy(page.content)
        query_key = SINGLE_IMAGE_TEMPLATES[page.template_type]
        if query_key not in content:
            return page, None, 0
        # is_allowed_image_url is false for both a missing image_url and one
        # pointing at a disallowed host -- both need a real fetch. Before
        # this existed, a URL that slipped past images.py's own host filter
        # (or was written before that filter existed) satisfied "already
        # has *a* image_url" forever and never got a second look, so a page
        # that once broke stayed broken through every future startup until
        # someone found it by hand via /admin/image-audit and re-ran with
        # force=true.
        if not (force_this_page or _needs_fetch(content.get("image_url"), revalidate)):
            return page, None, 0

        query = content[query_key]
        queries = [query]
        if page.template_type == "comparison":
            # Already has two clean, broad item names on hand -- no need to
            # derive anything from the title. Used to skip the relevance
            # check entirely here (reasoning: no single must_match term
            # fits when either item, or both, is a legitimate photo) --
            # but "no single term" isn't "no check at all", and skipping it
            # let a photo of neither item through on ube-vs-taro with
            # nothing to catch it. images.py's _is_relevant() accepts a
            # tuple of alternatives for exactly this -- both item names as
            # an OR check, so a photo showing either one (or both) passes,
            # and only a photo matching neither gets rejected.
            item_names = tuple(
                name for name in (content.get("item_a_name"), content.get("item_b_name")) if name
            )
            queries += [name for name in item_names if name.lower() != query.lower()]
            attempts = [(q, item_names or None) for q in queries]
        elif page.template_type == "recipe_or_dish":
            # No SINGLE_IMAGE_FALLBACKS entry for recipe_or_dish (see that
            # dict's comment: a dish name is already about as broad a query
            # as makes sense) -- but that leaves a recipe page with a single
            # query and nothing to fall back on if that exact search comes
            # up empty. In practice it usually isn't empty: a matching
            # category_roundup card (e.g. taco-recipes' "Carne Asada Tacos")
            # searches this exact same query text and, being in the earlier
            # phase, gets first claim via used_urls -- so if only one good
            # match exists for a niche dish name, the card claims it and
            # this page's own identical search comes up with nothing left.
            # The category name from category_link (e.g. "Taco") is the
            # same broadening the card itself already falls back to, so
            # this recipe gets a real second shot instead of ending up bare
            # just because a card elsewhere on the site happened to search
            # first.
            category_title = (content.get("category_link") or {}).get("title")
            if category_title:
                fallback = _category_fallback_query(category_title)
                if fallback and fallback.lower() != query.lower():
                    queries.append(fallback)
            # A real, lenient relevance check -- see
            # _recipe_dish_must_match_terms' own docstring for why this
            # isn't the exact-dish-name requirement recipe_or_dish was
            # deliberately built without, just a check that a candidate's
            # alt text mentions *some* real food-content word from the
            # query, not only a vessel/container word it happens to share.
            # "Some" is doing a lot of work here, though: for a dish whose
            # query has a common single-word ingredient in it at all
            # ("cheese", "chicken", "soup", "tea"), that one word alone is
            # enough to pass -- lenient by design (see that function's
            # docstring), but it means the primary query can still "succeed"
            # on a technically-passing, actually-wrong photo (some unrelated
            # cheese, or the wrong style of soup) well before ever finding
            # out the salient-ingredient tier below exists.
            must_match = _recipe_dish_must_match_terms(query)
            dish_attempts = [(q, must_match) for q in queries]
            # Opt-in per page via this content key: a generic, raw/plain
            # shot of the dish's single most recognizable ingredient, for
            # dishes a general-purpose stock library is unlikely to have
            # actually photographed as a finished, correctly-labeled plate
            # -- a branded product name ("Sonic Ocean Water"), a dish whose
            # name reads as something else entirely to a keyword search
            # ("chocolate gravy" as a savory brown gravy; "onion soup mix"
            # as an actual bowl of soup, not the dry seasoning blend it is;
            # "Manhattan clam chowder" as the far more commonly-photographed
            # cream-based New England style), or a regional/foreign dish
            # name with no real stock coverage at all. Its own must_match is
            # derived from *this* query, not the dish's -- a raw-ingredient
            # photo's alt text will say "chia seeds" or "clams", never the
            # dish's own name, so reusing the dish-level must_match here
            # would reject the very photos this tier exists to find.
            #
            # Tried FIRST, not last, when present -- a page only gets this
            # field curated because the dish-name search was already found
            # to be unreliable for it (see the comment above must_match), so
            # trusting that curated answer over a lenient, easily-satisfied
            # dish-name search is the whole point. Originally shipped as a
            # last-resort tier instead, which meant it only ever ran for a
            # page whose dish-name search returned literally nothing --
            # for a page where that search instead "succeeds" on a weak,
            # wrong match (exactly the failure case this tier exists for),
            # the curated fallback never got a chance to run at all.
            salient_query = content.get("salient_ingredient_query")
            salient_attempts = (
                [(salient_query, _recipe_dish_must_match_terms(salient_query))] if salient_query else []
            )
            attempts = salient_attempts + dish_attempts
        else:
            fallback_fn = SINGLE_IMAGE_FALLBACKS.get(page.template_type)
            # Also the required subject term for every query tried for this
            # page, not just used to build the fallback query itself -- see
            # _apply_result's must_match. Every template in
            # SINGLE_IMAGE_FALLBACKS reduces to exactly one core noun (the
            # ingredient/term/technique subject itself), which is what a
            # photo for this page actually needs to be of, whether it was
            # found via the specific hero_image_query or the broader
            # fallback.
            fallback_term = fallback_fn(page.title) if fallback_fn else None
            if fallback_term and fallback_term.lower() != query.lower():
                queries.append(fallback_term)
            # howto_technique's fallback_term often still carries filler
            # _howto_fallback_query's single-word verb-strip can't catch
            # (see _howto_must_match_term's own docstring) -- fine to keep
            # in the query text above (harmless extra context for a search
            # engine), but not as the required exact-substring match term.
            must_match = (
                _howto_must_match_term(fallback_term)
                if page.template_type == "howto_technique" and fallback_term
                else fallback_term
            )
            attempts = [(q, must_match) for q in queries]
            # ingredient_hub only: a last-resort relaxed attempt once the
            # exact title itself has been tried and failed -- see
            # _ingredient_hub_relaxed_term's docstring for the real case
            # (milano-cookies) that motivated this.
            if page.template_type == "ingredient_hub":
                relaxed = _ingredient_hub_relaxed_term(page.title)
                if relaxed and relaxed.lower() != (must_match or "").lower():
                    attempts.append((relaxed, relaxed))
            # howto_technique only: same last-resort idea, but as an
            # OR-tuple of must_match's individual words rather than a
            # single relaxed term -- see _howto_relaxed_terms' docstring
            # for why a positional guess (first word vs. last word) can't
            # be made to work generally here the way it can for
            # ingredient_hub's title-derived term.
            elif page.template_type == "howto_technique":
                relaxed_terms = _howto_relaxed_terms(must_match)
                if relaxed_terms:
                    attempts.append((fallback_term, relaxed_terms))

        # Per-page escape hatch: recipe_or_dish is deliberately left out of
        # the relevance check above (see its own comment -- a dish name is
        # usually broad enough that any photo the query returns is fine).
        # "Usually" isn't "always": homemade-turkey-feed's photo came back
        # of some other small bird, not a turkey, because turkey-feed is
        # really an animal-care topic wearing a recipe_or_dish template, not
        # an actual dish -- the query's own words don't guarantee the photo
        # is really of a turkey the way "chicken alfredo" effectively
        # guarantees a photo tagged for that query is alfredo. Rather than
        # add a must_match derivation for every recipe_or_dish page (which
        # would start rejecting perfectly good dish photos whose alt text
        # just doesn't happen to repeat the dish name), individual pages
        # can opt into a required term via this optional content key.
        override_must_match = content.get("hero_image_must_match")
        if override_must_match:
            attempts = [(q, override_must_match) for q, _ in attempts]

        # Only exclude the page's own current photo when it was explicitly
        # named (slugs=...) -- not for the passive background loop, which
        # never re-touches an already-set image_url in the first place
        # (see _needs_fetch above), and not for a bare site-wide force run,
        # where re-selecting the same still-good photo for most pages is
        # the expected, harmless outcome. This is specifically for "someone
        # asked to fix this one page's wrong photo" -- see _apply_result's
        # own docstring for why must_match alone doesn't already cover it.
        self_exclude = (
            frozenset({content["image_url"]})
            if only_slugs is not None and content.get("image_url")
            else frozenset()
        )
        print(f"  {page.slug}: searching '{query}'...")
        try:
            if _apply_result(content, attempts, page.template_type, used_urls, extra_exclude=self_exclude):
                return page, content, 1
            elif content.get("image_url"):
                # Every query came up empty (a thin free-tier catalog, or
                # every candidate already claimed by used_urls) -- without
                # this, a URL that's broken (not missing) stays parked here
                # forever: the "does this need a fetch" check above keeps
                # re-triggering a search on every future run, but a failed
                # search on its own never removes the stale value it was
                # trying to replace. Clearing it instead falls back to
                # StockPhotoSlot's "no imageUrl -> render nothing" behavior,
                # which beats a permanently broken <img> even though it
                # means no photo until a later run's search succeeds.
                content.pop("image_url", None)
                content.pop("image_attribution", None)
                return page, content, 0
        except Exception as e:
            print(f"    error: {e}")
            # A plain string check, not exception-type introspection: every
            # provider error already gets str()'d into this exact message
            # by requests' own HTTPError, and matching on it here needs no
            # new import or coupling to requests' exception internals for
            # what's meant to be a blunt, reliable "stop" signal.
            if "429" in str(e):
                rate_limited.set()
        return page, None, 0

    def process_category_roundup_page(page: Page) -> tuple[Page, dict | None, int]:
        """Same not-touching-`db` contract as process_single_image_page --
        see that function's docstring."""
        if rate_limited.is_set():
            return page, None, 0
        # A card's slug lives inside its parent category_roundup page's own
        # row, so `page.slug in only_slugs` alone would miss a request
        # scoped to a card slug entirely -- check the page's own slug OR
        # any of its cards' slugs before deciding to skip it.
        page_explicitly_requested = only_slugs is not None and page.slug in only_slugs
        requested_card_slugs: set[str] = set()
        if only_slugs is not None:
            requested_card_slugs = {
                c.get("slug") for c in page.content.get("recipe_cards", []) if c.get("slug")
            } & only_slugs
        if only_slugs is not None and not page_explicitly_requested and not requested_card_slugs:
            return page, None, 0
        # Force applies to every card on the page only for a genuinely
        # unscoped site-wide force run (force=True with no only_slugs at
        # all), or when this page's own slug -- not just one of its cards'
        # -- was explicitly named. `force and only_slugs is not None`
        # deliberately does NOT count: a real bug, found by actually
        # running this against production, was `force=true&slugs=char-siu`
        # re-rolling all 6 of chinese-recipes' cards instead of just
        # char-siu's, because bare `force` used to cascade to every card
        # the moment the page passed the filter above for any reason,
        # including only one matching card. requested_card_slugs (below) is
        # what correctly scopes a single-card request now.
        force_this_page = (force and only_slugs is None) or page_explicitly_requested

        content = copy.deepcopy(page.content)
        images_written_delta = 0
        changed = False
        for card in content.get("recipe_cards", []):
            # Same broken-vs-missing distinction as the single-image path
            # -- a card's image_url can end up on a disallowed host too
            # (this is literally the case that motivated adding the host
            # check to images.py in the first place: category cards'
            # image_query terms are often niche enough to surface
            # Unsplash+ results). force_this_card covers a request scoped
            # to just this one card's own slug (see requested_card_slugs
            # above) as well as force_this_page (force=true, or the whole
            # collection page's own slug was named), so `slugs=char-siu`
            # reaches this specific card's photo without touching its 5
            # siblings.
            force_this_card = force_this_page or card.get("slug") in requested_card_slugs
            if force_this_card or _needs_fetch(card.get("image_url"), revalidate):
                query = card.get("image_query")
                if not query:
                    continue
                # A specific dish name (e.g. "nasu dengaku") often has no
                # match in a free-tier catalog -- fall back to the page's
                # own category (e.g. "Eggplant") so a card isn't left
                # permanently blank just because its exact dish is too
                # niche to have stock photos of its own.
                fallback = _category_fallback_query(page.title)
                queries = [query] if fallback.lower() == query.lower() else [query, fallback]
                attempts = [(q, None) for q in queries]
                card_explicitly_requested = card.get("slug") in requested_card_slugs
                self_exclude = (
                    frozenset({card["image_url"]})
                    if (page_explicitly_requested or card_explicitly_requested) and card.get("image_url")
                    else frozenset()
                )
                print(f"  {page.slug} / {card.get('title')}: searching '{query}'...")
                try:
                    if _apply_result(card, attempts, page.template_type, used_urls, extra_exclude=self_exclude):
                        images_written_delta += 1
                        changed = True
                    elif card.get("image_url"):
                        # Same "a failed search must not leave a broken
                        # value behind" fix as the single-image path -- a
                        # card's image_query is often the niche part of the
                        # pair (queries tries it before the broader
                        # category fallback), so this is the more likely of
                        # the two to actually exhaust every candidate.
                        card.pop("image_url", None)
                        card.pop("image_attribution", None)
                        changed = True
                except Exception as e:
                    print(f"    error: {e}")
                    if "429" in str(e):
                        rate_limited.set()
                        break  # this page's remaining cards too, not just future pages
        return page, (content if changed else None), images_written_delta

    def run_phase(pages: list[Page], worker) -> None:
        nonlocal pages_updated, images_written
        if not pages:
            return
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            futures = [pool.submit(worker, page) for page in pages]
            for future in as_completed(futures):
                page, new_content, delta = future.result()
                images_written += delta
                if new_content is not None:
                    page.content = new_content
                    pages_updated += 1

    run_phase(single_image_pages, process_single_image_page)
    run_phase(category_roundup_pages, process_category_roundup_page)

    db.commit()
    return pages_updated, images_written


if __name__ == "__main__":
    if not UNSPLASH_ACCESS_KEY and not PEXELS_ACCESS_KEY:
        print(
            "No UNSPLASH_ACCESS_KEY or PEXELS_ACCESS_KEY set -- nothing to do.\n"
            "Get free keys at https://unsplash.com/developers and/or "
            "https://www.pexels.com/api/, then set them as environment "
            "variables and re-run this script."
        )
        sys.exit(0)

    force = "--force" in sys.argv
    session = SessionLocal()
    try:
        updated, written = fetch_images(session, force=force)
        print(f"\nDone. {updated} page(s) updated, {written} image(s) written.")
    finally:
        session.close()
