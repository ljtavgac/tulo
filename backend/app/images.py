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
        if url in exclude_urls:
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
        if url in exclude_urls:
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
