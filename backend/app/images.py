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


def _search_unsplash(query: str) -> ImageResult | None:
    r = requests.get(
        "https://api.unsplash.com/search/photos",
        headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
        params={"query": query, "per_page": 1},
        timeout=10,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        return None
    photo = results[0]
    return ImageResult(
        url=photo["urls"]["regular"],
        photographer=photo["user"]["name"],
        photographer_url=photo["user"]["links"]["html"],
        source="unsplash",
        download_location=photo["links"]["download_location"],
    )


def _search_pexels(query: str) -> ImageResult | None:
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_ACCESS_KEY},
        params={"query": query, "per_page": 1},
        timeout=10,
    )
    r.raise_for_status()
    results = r.json().get("photos", [])
    if not results:
        return None
    photo = results[0]
    return ImageResult(
        url=photo["src"]["large"],
        photographer=photo["photographer"],
        photographer_url=photo["photographer_url"],
        source="pexels",
    )


def search_image(query: str) -> ImageResult | None:
    """Unsplash first, Pexels as fallback. None if no keys are configured,
    both APIs error, or neither has a result for this query."""
    if UNSPLASH_ACCESS_KEY:
        try:
            result = _search_unsplash(query)
            if result:
                return result
        except requests.RequestException:
            pass

    if PEXELS_ACCESS_KEY:
        try:
            return _search_pexels(query)
        except requests.RequestException:
            return None

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
