from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
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


class OutreachProspect(Base):
    """One link-building outreach target -- either a tool-pitch email to a
    site that might link to one of Tulo's tools/calculators, or a drafted
    reply to a HARO/Connectively-style source query -- queued for a human
    to approve or reject before anything sends. See a handful of
    clearly-marked example rows seeded by _seed_outreach_examples() for
    what a not-yet-real row looks like.

    Approving a tool_pitch prospect with a contact_email, once
    SNOV_CLIENT_ID/SNOV_CLIENT_SECRET/SNOV_LIST_ID are all configured,
    calls Snov.io's add-prospect-to-list endpoint (see
    _add_prospect_to_snov_list in main.py) -- which, per Snov.io's own
    documented pattern, auto-enrolls the prospect into whatever
    already-active drip campaign is attached to that list in the Snov.io
    dashboard. That's a one-time manual setup on Snov.io's side (connect a
    sending mailbox, write the campaign template, mark it active) this
    code can't and shouldn't do on the user's behalf with real mailbox
    credentials. haro_reply prospects are never auto-sent this way -- a
    one-off personal reply to a specific journalist query doesn't fit a
    one-template-many-recipients drip campaign, so those still require a
    human to actually send the reply themselves once approved.

    status: "queued" (needs a decision) | "approved" | "rejected".
    sent_at/send_error record what happened when an approval tried to
    actually send -- both stay null for a haro_reply, for an approval that
    predates Snov.io being configured, or for one missing a contact_email."""

    __tablename__ = "outreach_prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pitch_type: Mapped[str] = mapped_column(String)  # "tool_pitch" | "haro_reply"
    target_domain: Mapped[str] = mapped_column(String)
    contact_name: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    # For a haro_reply: the source query being responded to. Null for a
    # tool_pitch, which has no originating query.
    source_query: Mapped[str | None] = mapped_column(String, nullable=True)
    subject: Mapped[str] = mapped_column(String)
    body_preview: Mapped[str] = mapped_column(String)
    is_example: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    send_error: Mapped[str | None] = mapped_column(String, nullable=True)
