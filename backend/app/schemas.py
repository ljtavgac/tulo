from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    template_type: str
    title: str
    status: str
    batch_number: int | None
    content: dict
    created_at: datetime


class ImageAttribution(BaseModel):
    # Both optional: a manually-overridden photo (see main.py's
    # /admin/review-queue/override-image, source == "manual_override")
    # writes both as None -- there's no known photographer for a URL a
    # reviewer just pasted in. Real live bug (2026-09-14): these were
    # required strings, which meant the first page anyone ever used that
    # override on took down every non-lean /pages list response (homepage
    # carousels, section index pages, search) with a 500 the moment
    # Pydantic tried to validate it -- individual /pages/{slug} fetches
    # were unaffected since they don't go through this model at all.
    photographer: str | None
    photographer_url: str | None
    source: str


class PageSummary(BaseModel):
    """Lighter shape for list responses (roundup grids, related-content modules).

    image_url/image_attribution/hero_image_query aren't real columns -- they
    live inside the JSON content blob -- so list_pages() builds these
    explicitly per page rather than relying on Pydantic's from_attributes to
    pull them automatically. Included so grids of pages (section index
    pages) can render a real photo tile instead of a text-only link,
    without an extra per-page round trip.
    """

    model_config = ConfigDict(from_attributes=True)

    slug: str
    template_type: str
    title: str
    image_url: str | None = None
    image_attribution: ImageAttribution | None = None
    hero_image_query: str | None = None
    # Real, specific caption text (e.g. "Grilled, citrus-marinated skirt
    # steak, sliced thin against the grain"), not just hero_image_query
    # reused as alt text -- see _summary_image()'s docstring in main.py.
    image_alt: str | None = None
    # Only populated for definition ("What Is X?") pages that have it --
    # literal word forms (verb, gerund, ...) other prose should auto-link
    # to this page with, since the page's own title reads as a question and
    # (for a technique like "searing") doesn't share a spelling with the
    # base verb a recipe step actually uses ("Sear the chicken").
    link_terms: list[str] | None = None
