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
    durable signal that click writes, so a click in the admin portal is
    the entire approval; nothing re-asks in chat. The actual merge is
    kicked off immediately via _trigger_batch_merge's GitHub Actions
    dispatch, and re-fired by _retry_stale_batch_approvals (checked on
    every review_queue()/outreach_queue() page load) if this row is
    still sitting with merged_at=None past a short grace period -- a
    real, reported incident: an earlier version of this docstring
    claimed a scheduled daily_batch.py run already did this retry, which
    was never actually true, so a silently-failed dispatch had no
    automatic recovery at all until that function existed.

    `merged_at` is null until the merge actually happens -- lets the
    merge step (and the retry above) find exactly the rows still
    needing action without re-processing ones it already handled, and
    lets the admin UI show "requested" vs. "merged" instead of just a
    single ambiguous timestamp."""

    __tablename__ = "batch_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    merged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OutreachProspect(Base):
    """One link-building outreach target -- either a tool-pitch email to a
    site that might link to one of Tulo's tools/calculators, or a drafted
    reply to a HARO/Connectively-style source query -- queued for a human
    to review before approving or rejecting. See a handful of
    clearly-marked example rows seeded by _seed_outreach_examples() for
    what a not-yet-real row looks like.

    A haro_reply row is normally already a real drafted reply, not a
    to-do: see _draft_haro_replies in main.py, which reads a forwarded
    digest and creates one row per query it's a genuine fit for (with a
    real contact_email/contact_name and a real proposed body) -- creating
    nothing at all when no query in that digest is a real fit, rather
    than a row for a human to triage by hand. A non-empty contact_email
    and a body containing a real Tulo URL are both enforced in code (see
    _draft_haro_replies), not just asked for in the prompt -- a drafted
    item failing either is dropped rather than turned into a row missing
    one. Only falls back to the old
    raw-digest-with-placeholder-body shape (body_preview exactly equal to
    _UNDRAFTED_HARO_PLACEHOLDER in main.py) when ANTHROPIC_API_KEY isn't
    configured or that call/parse fails -- see outreach_queue_ingest_email.
    The portal hides Approve on that placeholder shape specifically (see
    card() in main.py) since it has no real contact_email and isn't
    meant to be sent as-is.

    subject/body_preview are the literal email -- exactly what gets sent,
    not a template or a preview of something composed elsewhere. A human
    can edit both on a queued card (see /admin/outreach-queue/update-content
    in main.py) before deciding.

    Approving any prospect (tool_pitch or haro_reply alike) with a
    contact_email, once GMAIL_SMTP_USER/GMAIL_SMTP_APP_PASSWORD are
    configured, sends subject/body_preview directly via Gmail SMTP (see
    _send_outreach_email in main.py) to contact_email. Replaces an earlier
    Snov.io add-prospect-to-list integration (see git history) that
    handed the actual send to a separately-authored campaign template --
    which meant this portal could never guarantee what a reviewer saw here
    was what actually went out.

    status: "queued" (needs a decision) | "approved" | "rejected" | "article_pending"
    | "article_requested" | "article_pending_review" | "article_failed". The
    last four exist only for a haro_reply whose query has no existing Tulo page/tool to
    cite but is genuinely answerable by one new article (see
    _draft_haro_replies' content-opportunity items, a separate outcome
    from a normal drafted reply): "article_pending" is the freshly-flagged
    opportunity, shown in the portal with a Create Article button instead
    of Approve/Reject (no contact_email verbatim-body invariant applies
    here since there's no body to send yet). Clicking it flips to
    "article_requested" -- a fast, synchronous status change only; actual
    generation needs a real Anthropic call plus a git commit+push to
    staging, neither of which this backend process can do on its own (no
    push credentials, and generation can run past a request timeout), so
    it's picked up externally instead (see
    content/scripts/generate_haro_article.py +
    .github/workflows/generate-haro-article.yml). Once that script pushes
    the new page to staging, it calls
    POST /admin/outreach-queue/link-article to store target_slug and flip
    to "article_pending_review" -- still not sendable, since the page is
    only on staging pending the normal human content-review step, not
    live on prod yet. outreach_queue()'s own render checks any
    "article_pending_review" row's target_slug against prod's real
    /pages/<slug> on every page load; once that page is confirmed live,
    it's re-drafted with the real URL, subject/body_preview filled in,
    and status flips to "queued" -- a normal, sendable row from that point
    on, no different from any other haro_reply.

    "article_failed" -- generate_haro_article.py exhausted its own
    generation retries and could not produce a valid page at all. Set by
    POST /admin/outreach-queue/mark-article-failed, which that script
    calls before re-raising (so the CI job still shows red for
    debugging, but the row doesn't just sit at "article_requested"
    forever looking like it's still in progress). body_preview holds a
    reviewer-facing "can't produce this" note; the only action available
    is Reject, or a human can re-run Create Article to try again.

    sent_at/send_error record what happened when an approval tried to
    actually send -- both stay null for an approval that predates
    GMAIL_SMTP_USER/GMAIL_SMTP_APP_PASSWORD being configured, or for one
    missing a contact_email."""

    __tablename__ = "outreach_prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pitch_type: Mapped[str] = mapped_column(String)  # "tool_pitch" | "haro_reply"
    target_domain: Mapped[str] = mapped_column(String)
    # The forwarding service a haro_reply came in through (Featured.com,
    # Connectively, HARO, Qwoted, SourceBottle, Terkel) -- see
    # _source_platform_label in main.py. Null for a tool_pitch/
    # content_pitch (no inbound digest) and for any haro_reply ingested
    # before this field existed. Distinct from target_domain, which holds
    # the individual reporter's own outlet name (e.g. "Food Republic"),
    # not the platform that routed the digest -- a reviewer doing a
    # manual-submission copy/paste needs to know which platform's site to
    # go paste into, which target_domain alone doesn't tell them.
    source_platform: Mapped[str | None] = mapped_column(String, nullable=True)
    # Shared across every prospect split out of the same single inbound
    # digest email (see outreach_queue_ingest_email) -- null for a
    # digest that produced only one prospect (nothing to link to) and
    # for anything ingested before this field existed. Lets the portal
    # warn a reviewer that a reply they're about to approve has sibling
    # content_opportunity items sitting in a different status tab (a
    # real, reported confusion: Southern Living's reply and its
    # spun-off article proposals looked like unrelated rows).
    source_group_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    contact_name: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    # Set by a sourcing script when a credible candidate has no findable
    # email but does have a live /contact or /contact-us page (see
    # _contact_form_url in content/scripts/*.py) -- lets the portal tell a
    # reviewer to paste the drafted subject/body into that page's form by
    # hand instead of dropping the candidate outright. Null for every
    # ordinary prospect (has a real contact_email already, or predates
    # this field). Never used for sending -- there is no automated form
    # submission, only a human copy/pasting.
    contact_form_url: Mapped[str | None] = mapped_column(String, nullable=True)
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
    # The following three are only ever set on a content-opportunity row
    # (see the status docstring above) -- null on every ordinary prospect.
    proposed_title: Mapped[str | None] = mapped_column(String, nullable=True)
    proposed_template_type: Mapped[str | None] = mapped_column(String, nullable=True)
    target_slug: Mapped[str | None] = mapped_column(String, nullable=True)
    # Why _draft_haro_replies thinks this content_opportunity is worth
    # building -- reviewer-only context for the Create Article/Reject
    # decision, shown in the article_pending "not-ready" box, never in
    # body_preview. A real, reported confusion: body_preview used to
    # hold this same "Why: ..." text, which reads like internal
    # deliberation a reporter should never see, even though it was
    # never actually sent (see the status docstring above -- a
    # content_opportunity has no sendable body until its article goes
    # live). Null for a non-content_opportunity row.
    rationale: Mapped[str | None] = mapped_column(String, nullable=True)
    # True when the source query itself said something like "No AI Pitches
    # Considered" (see _query_disallows_ai_pitches in main.py) -- a real,
    # not hypothetical, note found on an actual HARO query this project
    # triaged. When true, body_preview is never the model's own AI-drafted
    # prose, regardless of pitch_type: _draft_haro_replies replaces a
    # "reply" item's drafted body with _NO_AI_PITCHES_PLACEHOLDER
    # immediately, and _resolve_pending_articles does the same instead of
    # its usual auto-filled template once a content_opportunity's article
    # goes live -- in both cases the point is that a human writes the
    # actual words that reach this reporter, not that a human merely
    # reviews AI-written ones. The portal hides Approve on that
    # placeholder exactly like _UNDRAFTED_HARO_PLACEHOLDER (see card()).
    ai_pitches_disallowed: Mapped[bool] = mapped_column(Boolean, default=False)
    # Reject Content -- an action independent of this row's own status
    # above (which tracks the *reply/email* decision only): a human can
    # reject a content-opportunity's generated page (remove it from
    # staging) regardless of whether they've approved, rejected, or not
    # yet decided on the eventual reply to the reporter. Set by the portal's
    # own "Reject Content" button (see card() in main.py), only shown when
    # target_slug is set and neither flag here is true yet. Backend has no
    # git push credentials (same constraint as article generation, see the
    # status docstring above), so this is a request, not an instant delete:
    # content/scripts/reject_haro_article.py +
    # .github/workflows/reject-haro-article.yml pick it up, actually
    # remove the page from staging's seed_templates.py, and call
    # POST /admin/outreach-queue/confirm-article-removed, which sets
    # content_removed. target_slug is deliberately left in place after
    # removal (a historical record of what was rejected), not cleared.
    content_removal_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    content_removed: Mapped[bool] = mapped_column(Boolean, default=False)
