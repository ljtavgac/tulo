from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Page(Base):
    """A single content page (recipe, ingredient hub, how-to, etc).

    `content` holds the template-specific structured data -- its shape
    varies by template_type (see PAGE_TEMPLATES.md), which is why it's a
    JSON column rather than a fixed set of typed columns: one table serves
    all 9 templates instead of nine near-duplicate tables.
    """

    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    template_type: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="draft")
    batch_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class PageReview(Base):
    """Tracks a human's approve/flag decision on one page's content-quality
    review, keyed by slug -- deliberately its own table rather than a field
    on Page.content: this is reviewer *process* state (who looked at this,
    what did they decide), not published content, and doesn't belong in
    seed_templates.py or get overwritten by resync_content().

    Built for the daily-batch review workflow (see /admin/review-queue in
    main.py): a new content batch lands with `status="pending"` implicitly
    (no row here yet) for every one of its pages, a reviewer marks each
    "approved" or "flagged" (optionally with a `note` on what's wrong), and
    the queue view re-surfaces "pending"/"flagged" pages on every visit
    without needing the reviewer to remember what they already covered.
    Does not itself gate publishing -- content["unpublished"] in
    seed_templates.py is still the only thing that controls whether a page
    is actually live; this is a review checklist, not an enforcement
    mechanism, kept that way so a flag doesn't silently take a page down
    that a human hasn't actually decided to unpublish yet."""

    __tablename__ = "page_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String)  # "approved" | "flagged"
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class BatchApproval(Base):
    """One row per batch_number the user has explicitly approved for
    promotion to main via /admin/review-queue/approve-for-prod -- the
    durable signal the daily pipeline's merge step (content/scripts/
    daily_batch.py, run by the scheduled job) checks for, so a click in
    the admin portal is the entire approval; nothing re-asks in chat.

    `merged_at` is null until the merge actually happens -- lets the
    merge step find exactly the rows still needing action
    (merged_at is null) without re-processing ones it already handled,
    and lets the admin UI show "requested" vs. "merged" instead of just
    a single ambiguous timestamp."""

    __tablename__ = "batch_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    merged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
