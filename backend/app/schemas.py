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
    photographer: str
    photographer_url: str
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
