"""
Real stock-photo sourcing via the official Unsplash and Pexels APIs (both
free, both return verified license/attribution info -- no scraping).

Inert by design: search_image() returns None immediately, with no network
call, if neither API key is configured. That's what lets the rest of the
app (StockPhotoSlot, fetch_stock_images.py) ship now and activate itself
the moment real keys are added, with nothing to revert.

SETUP: get free keys at https://unsplash.com/developers and
https://www.pexels.com/api/, then set UNSPLASH_ACCESS_KEY and/or
PEXELS_ACCESS_KEY as environment variables.
"""

import os
from dataclasses import dataclass

import requests

UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")
PEXELS_ACCESS_KEY = os.environ.get("PEXELS_ACCESS_KEY")


@dataclass
class ImageResult:
    url: str
    photographer: str
    photographer_url: str
    source: str  # "unsplash" | "pexels"
    # Only Unsplash requires this -- see ping_download().
    download_location: str | None = None


SEARCH_RESULTS_PER_PAGE = 10

# next.config.mjs only allowlists these two hosts for next/image -- any photo
# URL outside them renders as a broken image on the site with no error
# anywhere in this pipeline to catch it. Unsplash's search API in particular
# can mix in Unsplash+ ("premium") results whose preview URLs are served
# from plus.unsplash.com instead of images.unsplash.com, so a URL-shape
# check (not just trusting the API response) is what actually prevents a
# result from silently breaking on the frontend.
#
# The single source of truth for this list -- main.py's /admin/image-audit
# and fetch_stock_images.py's re-fetch logic both import it from here rather
# than keeping their own copy, which is exactly how this list drifted out of
# sync with fetch_stock_images.py's skip check in the first place (see
# is_allowed_image_url's docstring).
ALLOWED_IMAGE_HOSTS = ("https://images.unsplash.com/", "https://images.pexels.com/")


def is_allowed_image_url(url: str | None) -> bool:
    """False for a missing URL too, not just a disallowed host -- "does this
    page already have a real, usable photo" is what every caller actually
    wants to know (fetch_stock_images.py's "does this still need a fetch"
    check, and main.py's /admin/image-audit "missing vs. broken" report,
    which checks `if not url` first and only reaches this function once url
    is already known truthy, so it never actually depends on this case).
    Getting this backwards once already caused a real bug: treating a
    missing image_url as "nothing to do here" instead of "needs a fetch"
    silently stopped every brand new page from ever getting a photo.
    """
    return url is not None and url.startswith(ALLOWED_IMAGE_HOSTS)


def _is_reachable(url: str) -> bool:
    """A search API returning a photo doesn't guarantee that photo's actual
    image URL is servable -- confirmed for real against a live Pexels
    result: the search API returned a "large" variant URL that Pexels'
    own image CDN then rejected with a 422 (Cloudflare passed it straight
    through to origin uncached, so this wasn't a caching issue on our end
    -- Pexels itself refused this specific asset, most likely taken down
    or made otherwise unservable after being indexed by search but before
    anyone actually requested the file). is_allowed_image_url() only
    checks that a URL's host looks right, so a URL like that got written
    to the database and stayed there forever: nothing ever re-checked it
    once it "looked" valid, and the browser silently hid the failure (see
    StockPhotoSlot's onError) with no signal anywhere that it needed a
    re-fetch. A live request here, before accepting a candidate, catches
    a dead asset before it ever reaches the database -- only run for
    photos not already ruled out by the exclude/host checks above it in
    each caller's loop, and cheap even then (see below)."""
    # A streamed GET, not HEAD: some image CDNs handle HEAD inconsistently
    # (405s even though the same URL's GET works fine), while GET is
    # universally supported -- stream=True plus closing right after
    # reading the status/headers avoids actually downloading the image
    # body, so this stays cheap.
    try:
        with requests.get(url, timeout=5, stream=True) as r:
            return r.status_code == 200
    except requests.RequestException:
        return False


def _search_unsplash(query: str, exclude_urls: frozenset[str] = frozenset()) -> ImageResult | None:
    r = requests.get(
        "https://api.unsplash.com/search/photos",
        headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
        params={"query": query, "per_page": SEARCH_RESULTS_PER_PAGE},
        timeout=10,
    )
    r.raise_for_status()
    for photo in r.json().get("results", []):
        url = photo["urls"]["regular"]
        if url in exclude_urls or not url.startswith(ALLOWED_IMAGE_HOSTS) or not _is_reachable(url):
            continue
        return ImageResult(
            url=url,
            photographer=photo["user"]["name"],
            photographer_url=photo["user"]["links"]["html"],
            source="unsplash",
            download_location=photo["links"]["download_location"],
        )
    return None


def _search_pexels(query: str, exclude_urls: frozenset[str] = frozenset()) -> ImageResult | None:
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_ACCESS_KEY},
        params={"query": query, "per_page": SEARCH_RESULTS_PER_PAGE},
        timeout=10,
    )
    r.raise_for_status()
    for photo in r.json().get("photos", []):
        url = photo["src"]["large"]
        if url in exclude_urls or not url.startswith(ALLOWED_IMAGE_HOSTS) or not _is_reachable(url):
            continue
        return ImageResult(
            url=url,
            photographer=photo["photographer"],
            photographer_url=photo["photographer_url"],
            source="pexels",
        )
    return None


def search_image(query: str, exclude_urls: frozenset[str] = frozenset()) -> ImageResult | None:
    """Unsplash first, Pexels as fallback. Returns None only if no keys are
    configured or neither provider has an unused match for this query -- a
    real API failure (bad key, rate limit, network error) raises
    requests.RequestException instead of silently masquerading as "no
    result," so callers (see fetch_stock_images.py, which already catches
    and logs per-page errors) can tell "nothing found" apart from
    "something's broken" instead of debugging blind.

    `exclude_urls` skips photos already assigned to another page in the
    same run -- without it, a thin catalog for a niche query (e.g. a
    specific regional dish name) can return the same "best match" photo
    for several different searches, showing up as the same picture on
    multiple recipes."""
    if UNSPLASH_ACCESS_KEY:
        try:
            result = _search_unsplash(query, exclude_urls)
            if result:
                return result
        except requests.RequestException as e:
            print(f"    Unsplash request failed ({e}), falling back to Pexels")

    if PEXELS_ACCESS_KEY:
        return _search_pexels(query, exclude_urls)

    return None


def ping_download(download_location: str) -> None:
    """Unsplash's API Guidelines require triggering this endpoint whenever
    a photo is actually used (not just displayed in search results) --
    https://help.unsplash.com/en/articles/2511245. Pexels has no
    equivalent requirement, so this is only ever called for Unsplash
    results (see fetch_stock_images.py)."""
    try:
        requests.get(
            download_location,
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=10,
        )
    except requests.RequestException:
        pass
