# Hybrid Content Pipeline — Design Doc (Planning Only)

**Status: not started.** Nothing in this document has been built or run. This
is the blueprint for scaling past the ~193 pages published so far to the
first 2,000 `CONTENT_QUEUE.csv` titles (batches 1-4, 1,947 rows remaining),
using the hybrid approach agreed on: Batch API for bulk first-draft
generation, interactive/agentic Claude Code for integration, cross-linking,
and QA. See the cost/timeline discussion earlier in this project's session
history for the numbers behind this plan; this doc is the "how," not the
"how much."

**Plan owner is on a Claude Max 5x subscription.** This changes where the
two phases' cost actually lands, without changing the phases themselves.

**Correction to an earlier version of this estimate:** a prior pass at
this section carried over the timeline logic from a *different* scenario
(running the entire project -- including writing all 1,947 pages --
through agentic Claude Code sessions) into Phase 2, and quoted 1.5-2+
weeks for it. That's wrong for what Phase 2 actually is once Phase 1
exists: Batch API has already written every page's draft by the time
Phase 2 starts, so Phase 2 is integration and cleanup, not authorship.
Corrected below.

- **Phase 1 (Batch API drafting)** is unaffected by any Claude.ai plan --
  billed separately through the Developer Platform regardless. Estimated
  ~$40-60, ~1 day turnaround (see cost safeguards section below).
- **Phase 2, broken into what it actually is:**
  - Parsing results, schema-validating, serializing into
    `seed_templates.py`, running `_check_content_depth()`, reconciling
    `CONTENT_QUEUE.csv` -- all scripted, not agent conversation. Minutes
    to hours, regardless of plan.
  - Cross-linking is mostly already automatic (see the section above) --
    spot-checking, not per-page work.
  - The one genuinely agentic, Max-usage-bound piece is **fixing whichever
    fraction of the 1,947 pages fail the depth check** -- a bounded
    subset, not a second pass over everything. This is the one real
    unknown; its size isn't known until the pilot batch runs.
  - Realistic result if that failure rate is modest: **the full pipeline
    fits in a few days**, not weeks, even paced across Max 5x's rolling
    usage windows.
- **To make "a couple of days" a guarantee rather than an "if the pilot
  goes well" hope:** run the fix-pass (and integration generally) through
  API/token credits instead of Max 5x session quota. This removes the
  rolling-window pacing entirely -- API rate limits are far above this
  workload's scale, so it runs as one continuous push instead of being
  spread across a subscription's reset cycle.
  - Incremental cost is small because it only touches the failing
    subset, and a targeted fix costs less than original generation:
    roughly **+$8-12 at a 10% failure rate, +$16-23 at 20%, +$24-35 at
    30%** -- all-in total (Batch + fix-pass) landing around **$50-95**
    depending on that rate, versus the pure-Max-5x path's ~$40-60 with a
    less certain timeline.
- **Image backfill is separate from all of the above** -- bounded by
  Unsplash/Pexels free-tier rate limits (only Pexels is currently
  configured), not by any Claude plan or API tier. Fetching ~1,900 photos
  could take the better part of a day of background, unattended time.
  This doesn't need to gate "content live": pages already render
  correctly with no photo and self-heal as `fetch_images()` keeps running
  (per this session's earlier image-pipeline work), so it's reasonable to
  treat photos as filling in progressively rather than a blocker on the
  batch being considered done.
- **Recommendation:** budget the small incremental API cost for the
  fix-pass from the start rather than betting on Max 5x's pacing being
  fast enough -- cheap insurance against the one real unknown (the
  pilot's failure rate) that turns "probably a couple of days" into
  "reliably a couple of days."

## Phase 1 built: two corrections found while actually writing it

`content/scripts/prompt_templates.py` and `content/scripts/build_batch_requests.py`
are written (Phase 1a/1b done). Building them for real surfaced two things
this plan got wrong or missed:

1. **Batch API does support tool-enforced structured output.** The line
   above about "no tool-enforced structured output" was wrong -- each batch
   request is an ordinary Messages API call, so it can carry `tools` and a
   forced `tool_choice` exactly like an interactive request. The actual
   implementation forces a per-template-type tool call with a strict
   `input_schema` (matching `frontend/lib/types.ts` field-for-field) instead
   of just prompting for raw JSON text. This should substantially cut the
   Phase 2 fix-pass rate, since a malformed/missing-field response becomes
   much harder for the model to produce at all, rather than something a
   validation pass has to catch after the fact.
2. **`CONTENT_QUEUE.csv`'s `proposed_article_title` column is unreliable for
   anything but `recipe_or_dish`.** It's a naive "keyword + Recipe" template:
   an `ingredient_hub` row like "Nigiri" becomes "Nigiri Recipe", a
   `howto_technique` row like "how to make matcha latte" becomes "Matcha
   Latte Recipe". Using it verbatim at scale would have put a wrong,
   recipe-shaped title on every non-recipe page in the batch. Fixed by
   having the model generate the page's own `title` field itself, following
   the real per-type convention shown in that type's calibration example
   (bare ingredient name, "How to ___", "What Is ___?", etc.) -- the prompt
   never passes `proposed_article_title` through at all. The request file's
   `custom_id` is built from the raw `title` keyword column instead (still
   not the final slug -- that gets derived from the model's actual generated
   title during Phase 2, checked for collisions against real pages at that
   point).

## Why hybrid (recap)

Batch API is cheap and fast for raw text generation but has no tool access,
no file access, and no awareness of other requests in the same batch.
Everything this site's quality bar actually depends on — mechanical
content-depth verification, cross-linking, slug collision avoidance,
image sourcing — requires an agentic pass regardless. So: Batch drafts the
content, an agentic pass integrates and fixes it.

## What "automatic" already means on this site (verified, not assumed)

Before designing the pipeline, it matters exactly which cross-linking is
already computed live (needs nothing from the pipeline) versus which
requires a specific field to be set correctly at generation time. Traced
directly from `backend/app/main.py`:

**Fully automatic, zero pipeline work needed:**
- Ingredient Hub / Substitute "recipes using this ingredient" — computed
  live from ingredient name → hub matching (`_resolve_hub_slug`,
  `_recipe_slugs_using_ingredient`).
- How-To "recipes using this technique" — computed live from any recipe
  whose `technique_link` points to that how-to page.
- Definition "related recipes" — computed live by scanning recipe
  instructions for the term's `link_terms`.
- Recipe "More recipes" — computed live (`_related_recipes`), scored by
  shared `category_link`, shared `technique_link`, and shared ingredient
  hubs. A curated list (if present) is preserved and only supplemented.
- Ingredient Hub "related ingredients" — computed live from ingredient
  co-occurrence across recipes.
- **Collection pages (category_roundup)** — computed live: any recipe
  whose `category_link` points to a collection is automatically folded
  into that collection's card grid (filling a matching placeholder title
  or appending a new card), on every page load.

**Requires a value set correctly at generation time — this is the one real
gap:**
- `category_link` on a new recipe. Checked directly: `CONTENT_QUEUE.csv`'s
  `category` column is **empty** for the queue rows checked (e.g. every
  enchilada-related row), so this can't be read off the queue as-is. All
  19 existing collections were confirmed in `SEED_PAGES` (Mexican, Italian,
  Japanese, etc.), so the target list exists — a new recipe just needs to
  be pointed at the right one, or correctly left unset if none apply.
- `hub_slug` on ingredients is *also* resolved automatically by name match
  even when unset (`_resolve_hub_slug`), so this is lower-priority to get
  right at generation time than `category_link` — worth setting explicitly
  where obvious, but not a hard requirement the way `category_link` is.

**Design implication:** the batch prompt for `recipe_or_dish` needs the
full list of existing collection titles/slugs in its context, with an
instruction to set `category_link` when the dish clearly belongs to one
of them, and leave it `null` otherwise (never invent a new collection —
that's a separate, human-reviewed decision, not a per-recipe one).

## Phase 1 — Batch draft generation

### 1a. Per-template-type prompt templates

One prompt template per `template_type` (`recipe_or_dish`, `ingredient_hub`,
`howto_technique`, `definition`, `comparison`, `substitute`,
`category_roundup`), each containing:
- The exact target JSON schema, derived directly from `frontend/lib/types.ts`
  and cross-checked against `backend/app/seed_templates.py`'s
  `_REQUIRED_CONTENT_FIELDS` — every required field must be in the schema,
  every field's exact key name must match (this is where a mismatch would
  silently fail `_check_content_depth()` later, so schema accuracy here is
  the highest-leverage thing to get right before submitting a real batch).
- 1-2 real, already-published examples of that template type (pulled from
  current `SEED_PAGES`) for tone/depth calibration — the same bar every
  page on the site is already held to (tips & variations, storage,
  reader tips, FAQs, step notes, real nutrition data, specific non-generic
  `image_alt` text per the SEO audit's fix).
- The specific row's title, `template_type`, and any other queue metadata
  (`category`, `cluster_capture_potential`, `proposed_article_title`).
- For `recipe_or_dish` specifically: the full list of existing collection
  titles/slugs (for `category_link`) and a short list of existing
  technique/how-to slugs (for `technique_link`), so the model can set both
  correctly instead of leaving every new recipe orphaned from them.
- An explicit instruction to return **only** a single JSON object, no
  prose, no markdown fencing — this needs a real test against a handful of
  sample requests before trusting it at 1,947-request scale, since
  Batch API has no tool-enforced structured output the way an interactive
  session could verify inline.

### 1b. Building the batch request file

A script (`content/scripts/build_batch_requests.py`, not written yet) that:
1. Reads `CONTENT_QUEUE.csv`, filters to batches 1-4 with
   `status == not_started`.
2. For each row, renders that template type's prompt with the row's data.
3. Emits one JSONL line per row: `{"custom_id": "<slug-or-row-id>",
   "params": {"model": "claude-sonnet-5", "max_tokens": ..., "system": ...,
   "messages": [...]}}`, matching the Message Batches API request shape.
4. Writes the full request file, plus a small manifest (row count per
   template type, estimated token/cost total) to review *before* submission.

1,947 requests fits in a single batch (limit is 100,000 requests / 256MB).

### 1c. Submitting and retrieving

Submit via the `/v1/messages/batches` endpoint (or the Python/TS SDK's batch
helper). Poll status; most batches finish within an hour, worst case 24
hours. Download the results file (JSONL, one line per `custom_id`) once
`processing_status` is `ended`.

## Phase 2 — Integration (this is the agentic part)

A script (`content/scripts/integrate_batch_results.py`, not written yet)
plus an interactive Claude Code pass, in this order:

1. **Parse results.** For each result line: on success, `json.loads()` the
   model's text output; on a per-request error, log it to a "needs retry"
   list rather than failing the whole run.
2. **Schema validation before touching the repo.** Validate each parsed
   object against the same required-field list `_check_content_depth()`
   enforces, *before* inserting anything — catches gaps in one batch pass
   instead of one page at a time. Anything failing goes to a "needs fix"
   list alongside the request errors from step 1.
3. **Serialize into `seed_templates.py`.** Convert each validated dict into
   the file's existing literal-Python-dict formatting (matching indentation
   and quoting conventions already established) and insert new entries —
   mechanically, the same pattern used for the 81-recipe merge earlier this
   session, not hand-typed.
4. **Cross-link wiring:**
   - `category_link` / `technique_link`: already set by the model per 1a,
     but spot-check a sample against the actual existing slugs (a
     hallucinated slug that doesn't exist would silently produce a dead
     link, since nothing currently validates `category_link.slug` against
     real pages).
   - Collection card auto-fill: verify title-matching still catches
     placeholder cards where they exist (same pattern as the 82-card
     wiring pass), and hand-check any collection where a new recipe should
     have appended as a *new* card rather than filled a placeholder.
   - `hub_slug` on ingredients: spot-check the automatic name-resolution
     catches real matches; hand-tag anything it misses due to naming
     mismatches (the same false-positive risk already documented in
     `_resolve_hub_slug` — exact match only, no fuzzy matching).
5. **Run `_check_content_depth()` for real** (`python -c "import
   app.seed_templates"`). Anything still failing goes to the "needs fix"
   list from step 2.
6. **Fix pass.** For the (expected small) percentage that fail validation:
   either a targeted interactive fix (read the gap, write the missing
   field directly) or a small second Batch request scoped to just those
   rows — decide based on how many there are once real numbers exist.
7. **Image backfill.** Run `fetch_images()` (already includes the
   reachability check and the recipe-before-card ordering fix from this
   session) — this needs no new code, just running it against the larger
   page set.
8. **Full verification pass**, matching this project's established
   standard: `tsc --noEmit`, `next build`, a local backend+frontend run,
   spot-check a sample of new pages (recipe detail page, its collection,
   its ingredient hub links, "More recipes") in an actual browser before
   calling a batch done.
9. **CONTENT_QUEUE.csv reconciliation** — flip `status` to `published` for
   everything that shipped, same script pattern as the 81-recipe merge.

## Rollout sequencing

1. **Pilot batch first** (~50 rows, a real cross-section of template
   types) — validates the prompt templates actually produce valid,
   schema-passing JSON at the expected quality bar, and gives a real
   measured cost/token number to replace the estimate from planning.
   Nothing beyond the pilot runs until this is reviewed together.
2. Fix whatever the pilot reveals (prompt wording, schema mismatches,
   category_link accuracy) — expect at least one iteration here.
3. Submit the remaining ~1,897 rows as the real batch.
4. Run the full Phase 2 integration pipeline once results are back.
5. Reconcile the queue, ship, verify live.

## Cost safeguards (answering the "exorbitant bill" question directly)

Confirmed against current Anthropic Console docs, not assumed:
- **Org-level monthly spend cap by usage tier** is enforced automatically
  server-side — Start tier $500/month, Build tier $1,000/month, Scale tier
  $200,000/month. Once hit, the API returns `429` /
  `enforced_spend_limit_reached` and pauses until the next calendar month
  (or a tier increase). New accounts often start even lower, in an
  "Evaluation" tier, until usage history is established.
- **You can additionally set your own spend limit below your tier's cap**,
  in Console → Settings → Billing → Spend limits. Once reached, requests
  fail with a clear `invalid_request_error` until you raise or remove it —
  this is the direct, recommended safeguard: set this to something like
  2x the pilot's actual measured cost before submitting the full batch,
  so a runaway job fails loudly and cheaply instead of surprising you on
  an invoice.
- **Per-workspace spend/rate limits** are also settable — if useful, this
  work could run under its own Console workspace with its own cap,
  isolated from any other API usage on the account.
- **Rate limits** (requests/tokens per minute) independently cap how fast
  any single batch can be processed, which is a secondary safety net
  against a misconfigured loop submitting the same batch repeatedly.

Recommended concrete step before Phase 1 ever runs for real: set a
Console spend limit at roughly pilot-cost × 40 (covering the full
remaining ~1,897 rows with headroom), not the tier's default cap.

## Open decisions before building any of this for real

1. Confirm the Console account + API key + billing are set up (see the
   earlier sign-up steps).
2. Review and approve the per-template-type prompt templates before any
   batch — these are the actual quality lever, more than the pipeline code.
3. Decide the pilot batch's specific 50 titles (a deliberate cross-section,
   not just "the first 50 rows") so it actually exercises every template
   type and at least one recipe that should land in an existing collection
   (e.g., an enchilada dish, to verify the `category_link` instruction
   works end to end).
4. Confirm the Console spend limit value before submitting the real batch.
