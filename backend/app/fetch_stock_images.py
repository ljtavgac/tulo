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
from .images import is_allowed_image_url, search_image, ping_download, UNSPLASH_ACCESS_KEY, PEXELS_ACCESS_KEY
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


def _apply_result(content: dict, queries: list[str], template_type: str, used_urls: set[str]) -> bool:
    """Tries each query in `queries`, in order, and writes
    image_url/image_attribution into `content` in place from the first one
    that finds a result. Returns True if it found and wrote one."""
    for query in queries:
        search_query = _search_query_for(template_type, query)
        result = search_image(search_query, exclude_urls=frozenset(used_urls))
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


def fetch_images(db: Session, force: bool = False, only_slugs: set[str] | None = None) -> tuple[int, int]:
    """Returns (pages_updated, images_written).

    `only_slugs`, when given, restricts the run to exactly those pages and
    always re-fetches them (as if `force` were true just for them) -- for
    redoing a specific page whose photo is wrong (not missing, not broken,
    just a bad match) without touching, and risking re-rolling, every other
    page's already-correct photo the way a site-wide force run would.
    """
    pages_updated = 0
    images_written = 0
    # Shared across the whole run so two different pages/cards never end up
    # with the literally same photo -- see search_image()'s exclude_urls.
    used_urls: set[str] = set()

    for page in db.query(Page).all():
        if only_slugs is not None and page.slug not in only_slugs:
            continue
        force_this_page = force or only_slugs is not None

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
            if force_this_page or not is_allowed_image_url(content.get("image_url")):
                query = content[query_key]
                queries = [query]
                if page.template_type == "comparison":
                    # Already has two clean, broad item names on hand --
                    # no need to derive anything from the title.
                    queries += [
                        name
                        for name in (content.get("item_a_name"), content.get("item_b_name"))
                        if name and name.lower() != query.lower()
                    ]
                else:
                    fallback_fn = SINGLE_IMAGE_FALLBACKS.get(page.template_type)
                    if fallback_fn:
                        fallback = fallback_fn(page.title)
                        if fallback and fallback.lower() != query.lower():
                            queries.append(fallback)
                print(f"  {page.slug}: searching '{query}'...")
                try:
                    if _apply_result(content, queries, page.template_type, used_urls):
                        images_written += 1
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
                # enough to surface Unsplash+ results).
                if force_this_page or not is_allowed_image_url(card.get("image_url")):
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
