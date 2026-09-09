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
"""

import copy
import re
import sys

from sqlalchemy.orm import Session

from .database import SessionLocal
from .images import _is_reachable, is_allowed_image_url, search_image, ping_download, UNSPLASH_ACCESS_KEY, PEXELS_ACCESS_KEY
from .models import Page

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


def _substitute_fallback_query(page_title: str) -> str:
    """"Best Substitutes for Baking Soda" -> "Baking Soda"."""
    return re.sub(r"^best substitutes?\s+for\s+", "", page_title, flags=re.IGNORECASE).strip()


# template_type -> a function deriving a broader fallback query from the
# page's title, tried when the template's own hero_image_query (a specific
# shot description) has no stock match. recipe_or_dish and ingredient_hub
# aren't here: hero_image_query for those is already about as broad as a
# useful query gets (a dish or ingredient name), so there's no meaningfully
# broader term left to fall back to.
SINGLE_IMAGE_FALLBACKS = {
    "definition": _definition_fallback_query,
    "howto_technique": _howto_fallback_query,
    "substitute": _substitute_fallback_query,
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


def _apply_result(
    content: dict, queries: list[str], template_type: str, used_urls: set[str], must_match: str | None = None
) -> bool:
    """Tries each query in `queries`, in order, and writes
    image_url/image_attribution into `content` in place from the first one
    that finds a result. Returns True if it found and wrote one.

    `must_match`, when given, is checked against every query attempt (not
    just a fallback query) -- see images.py's _is_relevant() for why: a
    search API can return a wrong-subject photo for the *primary* query
    just as easily as for a fallback one (that's exactly what happened for
    how-to-cook-beets, where "roasted beets whole on baking sheet" itself,
    not a fallback, returned a roasted turkey)."""
    for query in queries:
        search_query = _search_query_for(template_type, query)
        result = search_image(search_query, exclude_urls=frozenset(used_urls), must_match=must_match)
        if result is None:
            print(f"    no result for '{search_query}'")
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
    used_urls: set[str] = set()

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
    # pages are processed, and get first claim on scarce matches, before
    # category_roundup pages, regardless of each one's position in
    # SEED_PAGES / insertion order.
    pages = db.query(Page).all()
    pages.sort(key=lambda p: p.template_type == "category_roundup")

    for page in pages:
        # A card's slug lives inside its parent category_roundup page's own
        # row, so `page.slug in only_slugs` alone would miss a request
        # scoped to a card slug entirely -- check the page's own slug OR
        # any of its cards' slugs before deciding to skip it. Recomputed
        # per page rather than once up front since only category_roundup
        # pages have cards to check.
        page_explicitly_requested = only_slugs is not None and page.slug in only_slugs
        requested_card_slugs: set[str] = set()
        if only_slugs is not None and page.template_type == "category_roundup":
            requested_card_slugs = {
                c.get("slug") for c in page.content.get("recipe_cards", []) if c.get("slug")
            } & only_slugs

        if only_slugs is not None and not page_explicitly_requested and not requested_card_slugs:
            continue
        # Force applies to the whole page (every card on it, for a
        # category_roundup) only for a genuinely unscoped site-wide force
        # run (force=True with no only_slugs at all), or when this page's
        # own slug -- not just one of its cards' -- was explicitly named.
        # `force and only_slugs is not None` deliberately does NOT count:
        # a real bug, found by actually running this against production,
        # was `force=true&slugs=char-siu` re-rolling all 6 of
        # chinese-recipes' cards instead of just char-siu's, because bare
        # `force` used to cascade to every card the moment the page passed
        # the filter above for any reason, including only one matching
        # card. requested_card_slugs (below, in the card loop) is what
        # correctly scopes a single-card request now.
        force_this_page = (force and only_slugs is None) or page_explicitly_requested

        # A deep copy, not a reference: mutating page.content directly (or a
        # shallow copy of it, for category_roundup's nested recipe_cards)
        # would change the "before" value SQLAlchemy compares against too,
        # since it'd be the same object -- then the reassignment below looks
        # like a no-op and it silently never emits the UPDATE.
        content = copy.deepcopy(page.content)
        changed = False

        query_key = SINGLE_IMAGE_TEMPLATES.get(page.template_type)
        if query_key and query_key in content:
            # is_allowed_image_url is false for both a missing image_url and
            # one pointing at a disallowed host -- both need a real fetch.
            # Before this existed, a URL that slipped past images.py's own
            # host filter (or was written before that filter existed)
            # satisfied "already has *a* image_url" forever and never got a
            # second look, so a page that once broke stayed broken through
            # every future startup until someone found it by hand via
            # /admin/image-audit and re-ran with force=true.
            if force_this_page or _needs_fetch(content.get("image_url"), revalidate):
                query = content[query_key]
                queries = [query]
                if page.template_type == "comparison":
                    # Already has two clean, broad item names on hand --
                    # no need to derive anything from the title. No single
                    # must_match term fits here (a comparison photo can
                    # legitimately show either item, or both), so this
                    # template is deliberately left out of the relevance
                    # check rather than forcing a wrong one.
                    queries += [
                        name
                        for name in (content.get("item_a_name"), content.get("item_b_name"))
                        if name and name.lower() != query.lower()
                    ]
                    must_match = None
                elif page.template_type == "recipe_or_dish":
                    # No SINGLE_IMAGE_FALLBACKS entry for recipe_or_dish
                    # (see that dict's comment: a dish name is already about
                    # as broad a query as makes sense) -- but that leaves a
                    # recipe page with a single query and nothing to fall
                    # back on if that exact search comes up empty. In
                    # practice it usually isn't empty: a matching
                    # category_roundup card (e.g. taco-recipes' "Carne Asada
                    # Tacos") searches this exact same query text and, being
                    # defined earlier in SEED_PAGES, gets processed first in
                    # this loop -- so if only one good match exists for a
                    # niche dish name, the card claims it via used_urls and
                    # this page's own identical search comes up with nothing
                    # left. The category name from category_link (e.g.
                    # "Taco") is the same broadening the card itself already
                    # falls back to, so this recipe gets a real second shot
                    # instead of ending up bare just because a card
                    # elsewhere on the site happened to search first.
                    category_title = (content.get("category_link") or {}).get("title")
                    if category_title:
                        fallback = _category_fallback_query(category_title)
                        if fallback and fallback.lower() != query.lower():
                            queries.append(fallback)
                    must_match = None
                else:
                    fallback_fn = SINGLE_IMAGE_FALLBACKS.get(page.template_type)
                    # Also the required subject term for every query tried
                    # for this page, not just used to build the fallback
                    # query itself -- see _apply_result's must_match. Every
                    # template in SINGLE_IMAGE_FALLBACKS reduces to exactly
                    # one core noun (the ingredient/term/technique subject
                    # itself), which is what a photo for this page actually
                    # needs to be of, whether it was found via the specific
                    # hero_image_query or the broader fallback.
                    must_match = fallback_fn(page.title) if fallback_fn else None
                    if must_match and must_match.lower() != query.lower():
                        queries.append(must_match)
                print(f"  {page.slug}: searching '{query}'...")
                try:
                    if _apply_result(content, queries, page.template_type, used_urls, must_match):
                        images_written += 1
                        changed = True
                    elif content.get("image_url"):
                        # Every query came up empty (a thin free-tier catalog,
                        # or every candidate already claimed by used_urls) --
                        # without this, a URL that's broken (not missing)
                        # stays parked here forever: the "does this need a
                        # fetch" check above keeps re-triggering a search on
                        # every future run, but a failed search on its own
                        # never removes the stale value it was trying to
                        # replace. Clearing it instead falls back to
                        # StockPhotoSlot's "no imageUrl -> render nothing"
                        # behavior, which beats a permanently broken <img>
                        # even though it means no photo until a later run's
                        # search actually succeeds.
                        content.pop("image_url", None)
                        content.pop("image_attribution", None)
                        changed = True
                except Exception as e:
                    print(f"    error: {e}")

        elif page.template_type == "category_roundup":
            for card in content.get("recipe_cards", []):
                # Same broken-vs-missing distinction as the single-image
                # branch above -- a card's image_url can end up on a
                # disallowed host too (this is literally the case that
                # motivated adding the host check to images.py in the first
                # place: category cards' image_query terms are often niche
                # enough to surface Unsplash+ results). force_this_card
                # covers a request scoped to just this one card's own slug
                # (see requested_card_slugs above) as well as force_this_page
                # (force=true, or the whole collection page's own slug was
                # named), so `slugs=char-siu` reaches this specific card's
                # photo without touching its 5 siblings.
                force_this_card = force_this_page or card.get("slug") in requested_card_slugs
                if force_this_card or _needs_fetch(card.get("image_url"), revalidate):
                    query = card.get("image_query")
                    if not query:
                        continue
                    # A specific dish name (e.g. "nasu dengaku") often has no
                    # match in a free-tier catalog -- fall back to the
                    # page's own category (e.g. "Eggplant") so a card isn't
                    # left permanently blank just because its exact dish is
                    # too niche to have stock photos of its own.
                    fallback = _category_fallback_query(page.title)
                    queries = [query] if fallback.lower() == query.lower() else [query, fallback]
                    print(f"  {page.slug} / {card.get('title')}: searching '{query}'...")
                    try:
                        if _apply_result(card, queries, page.template_type, used_urls):
                            images_written += 1
                            changed = True
                        elif card.get("image_url"):
                            # Same "a failed search must not leave a broken
                            # value behind" fix as the single-image branch
                            # above -- a card's image_query is often the
                            # niche part of the pair (queries tries it before
                            # the broader category fallback), so this is the
                            # more likely of the two branches to actually
                            # exhaust every candidate.
                            card.pop("image_url", None)
                            card.pop("image_attribution", None)
                            changed = True
                    except Exception as e:
                        print(f"    error: {e}")

        if changed:
            page.content = content  # already an independent object -- see the deepcopy above
            pages_updated += 1

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
