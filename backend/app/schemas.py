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


class PageSummary(BaseModel):
    """Lighter shape for list responses (roundup grids, related-content modules)."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    template_type: str
    title: str
