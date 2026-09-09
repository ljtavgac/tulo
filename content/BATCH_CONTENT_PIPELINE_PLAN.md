# Hybrid Content Pipeline — Design Doc

**Status: pilot complete, real batch not yet submitted.** The pipeline
described below is built and has run for real: a 50-title pilot (48
published, 2 excluded as duplicates) plus 12 companion recipes for two
broken collections, taking the site from 193 to 253 pages. That run
surfaced 11 real bugs, all now either fixed at the root or turned into a
running script — see "Bulletproofing the next batch" further down for the
complete accounting and the mandatory pre-flight gate before the real
batch runs. This doc is the blueprint for scaling past 253 pages to the
first 2,000 `CONTENT_QUEUE.csv` titles (batches 1-4, ~1,897 rows
remaining after the pilot + duplicates found), using the hybrid approach
agreed on: Batch API for bulk first-draft generation, interactive/agentic
Claude Code for integration, cross-linking, and QA. See the cost/timeline
discussion earlier in this project's session history for the numbers
behind this plan; this doc is the "how," not the "how much."

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

## Post-pilot validation round: schema bugs found, pan_size added, and the
## category_roundup coordination gap

After the 48-page pilot shipped, direct questions about whether pan-size
selection, ingredient substitutes, and collection auto-linking were
actually working on the new pages (rather than assumed) surfaced real
problems worth recording before the full batch ever runs:

- **`step_notes`'s schema would have failed most of the real batch.** It
  used `additionalProperties` as a value schema (an open-ended dict keyed
  by arbitrary step indices) -- `output_config`'s strict mode categorically
  rejects this. Every `recipe_or_dish` request (7,386 of 12,425 remaining
  rows, the largest single category) would have 400'd outright. Found by
  actually generating a real test recipe, not by re-reading the schema.
  Fixed: `step_notes` now travels through generation as an array of
  `{step_index, note}` objects (expressible in strict schema) and gets
  converted back to the site's real int-keyed dict shape at integration
  time (`integrate_batch_results.py`).
- **`recipe_or_dish`'s `max_tokens` budget was too tight once the schema
  grew.** Adding `pan_size` and `related_recipe_slugs` pushed some
  generations into `stop_reason: max_tokens` (truncated, invalid JSON) --
  including a retry of a title that had fit comfortably the first time,
  confirming real attempt-to-attempt length variance, not just a one-time
  fluke. Bumped 4096 -> 8192.
- **`pan_size` was missing from the pipeline entirely** -- not a bug, an
  unexamined scope decision that didn't hold up once questioned: pan
  dimensions and area math (length x width, or pi x r^2) are exactly the
  kind of factual domain knowledge the model handles reliably, and "not
  every recipe needs it" is a conditional-instruction problem the same way
  `technique_link`/`category_link` already are, not a reason to exclude it
  outright. Added with an explicit instruction to only populate it for a
  recipe genuinely baked in a shaped pan/dish, tested against a cake
  (correct, geometrically accurate `pan_size` with a real alternative), a
  stir-fry, and a cocktail (both correctly `null`). `validation.py`'s
  `check_pan_size_math()` independently recomputes the expected area from
  a label's stated dimensions and flags a mismatch -- the model is doing
  real arithmetic here, worth verifying rather than trusting.
- **Retroactively backfilled `pan_size`** onto the 3 already-published
  pilot recipes genuinely baked in a shaped pan/dish
  (`flourless-chocolate-cake`, `gluten-free-bread`,
  `finnish-oven-pancake-pannukakku`), reading their own already-written
  instructions for the real stated pan size rather than guessing.
- **New collections shipped with zero real linked recipes.** Checked
  directly: both `pinwheel-recipes` and `blackstone-recipes` (pilot-created
  collections) have every `recipe_cards` entry at `slug: null`. The
  category-roundup auto-fill (`main.py`, `_recipes_linking_to` +
  title-matching) only connects a placeholder card once a real recipe page
  exists whose own `category_link` points back at the collection *and*
  whose title matches the card exactly -- and the pilot generated the
  collection page describing 5-6 dishes by name without also generating
  those dishes as real pages. Root cause: **the pipeline treats every
  queue row as fully independent**; nothing coordinates "this new
  collection references N specific dishes" with "therefore also write
  those N dishes."

  **Decision: generate matching recipes too.** For a `category_roundup`
  row, after generating its content, also generate a real `recipe_or_dish`
  page for each of its cards (or a subset), with `title` and
  `category_link` force-set to the known-correct values after
  generation (not left to the model's judgment the way an independent
  recipe's category_link genuinely is -- there's no ambiguity here, the
  card already states exactly which collection this recipe is for).
  `title` must match the card's title exactly, case-insensitive, for the
  live title-matching fill to find it -- forced rather than trusted, same
  reasoning as `category_link`.

  Implemented and proven on the two existing broken collections in
  `content/scripts/generate_companion_recipes.py`: takes a collection
  slug, finds its unlinked cards, generates a real recipe for each with
  the card's title/description as inspiration, force-corrects `title` and
  `category_link`, and requires nothing further -- the collection's
  `recipe_cards` list itself is never touched; the live auto-fill finds
  the new recipes by title match on its own, the same way it already
  works for hand-authored content. For the real batch: a `category_roundup`
  row's companion recipes need to be generated in a second pass once the
  collection's own card list exists (Batch API can't chain "generate X,
  then use X's output to build a follow-up request" within one
  submission), so `category_roundup` rows should be submitted and
  integrated slightly ahead of the general batch, not simultaneously with
  it -- costs roughly one extra `recipe_or_dish`-priced request per
  card (~5-6 per collection, ~112 collections in the real queue -- call it
  ~550-650 extra requests, a meaningful but bounded addition).

## Bulletproofing the next batch: every issue found, and what now prevents it

The 48-page pilot (plus the 12 companion recipes generated afterward for
the two broken collections) surfaced 11 distinct bugs. This section is
the complete accounting asked for after that pilot: what broke, why, and
-- for each one -- whether a real, running safeguard now exists or the
fix was one-time manual cleanup with no mechanism stopping a recurrence.
**"Documented" is not a safeguard.** Every item below either has a script
that runs and fails loudly, or is explicitly flagged as still needing
human judgment every time -- nothing here relies on a person remembering
to re-check something by hand.

### The mandatory pre-flight gate

**`content/scripts/preflight_check.py` -- run this before submitting any
real batch, full stop.** It runs, in order:
1. `check_schemas_match_types.py` -- every schema still covers every
   field `frontend/lib/types.ts` actually requires (parses the .ts file
   directly, not a second hand-maintained list).
2. `check_queue_duplicates.py` -- no queue row collides with another
   queue row or an already-published page (see below).
3. **One real generation per template type, against the live Messages
   API with `output_config`** -- not a schema re-read, an actual call,
   for every one of the 7 template types. Each result gets
   `extract_content()`'d, `validate_content()`'d, and checked for
   `max_tokens` headroom, exactly like a real batch result would be.

Step 3 is the one that matters most and is easiest to skip under time
pressure: it's the only check in this whole pipeline that would have
caught the step_notes/`output_config` 400 error *before* it reached a
real batch, because that bug was invisible to schema re-reading -- it
only showed up against the real API. `preflight_check.py` exits non-zero
if `PIPELINE_ANTHROPIC_API_KEY` isn't set specifically so this step can't
be silently skipped by omission.

Verified: `check_schemas_match_types.py` and `check_queue_duplicates.py`
both ran for real against the current schemas and the full 12,425-row
`CONTENT_QUEUE.csv` (not a sample) as part of writing this section --
schemas came back clean, but the duplicate checker found **55 exact
topic collisions never caught before** (see below), proving the tool
works before ever being relied on. Step 3's live-generation path reuses
the exact `call_messages_api` / `extract_content` / `validate_content`
sequence already proven correct by real calls this session (the
companion-recipe generations, the original pilot batch) -- but hasn't
itself been executed in this session (no API key was available while
writing this section). Run it for real with a key before the next batch,
the same way every other claim in this pipeline has been verified against
a real run rather than trusted from code review alone.

### Issue-by-issue accounting

1. **`step_notes`'s schema was incompatible with `output_config`'s strict
   mode** (would have 400'd ~60% of a real batch -- `recipe_or_dish` is
   7,386/12,425 rows). Found by a real test generation, not schema
   review. **Fixed at the root**: `step_notes` now travels as an array of
   `{step_index, note}` objects during generation, converted back to the
   site's int-keyed dict at `normalize_for_storage()` (`validation.py`),
   the one shared choke point every integration path calls.
   **Safeguard: preflight_check.py step 3, every template type, every
   batch.**
2. **`max_tokens` too tight, causing real truncated/invalid JSON.**
   `recipe_or_dish` bumped 4096 -> 6144 -> 8192 after a retry of the same
   title failed twice, proving real attempt-to-attempt variance. Then,
   while writing this section, `validate_batch_results.py`'s new
   headroom check (below) found the *other 5* template types' budgets
   had the identical latent problem -- 12 already-published pilot
   results had used 85-100% of their budget, including one page
   (`what-is-dubai-chocolate`) that finished at literally 100% of
   `definition`'s old 1500-token cap without actually truncating this
   time. **Fixed**: `ingredient_hub`/`howto_technique` 2500 -> 3500,
   `definition` 1500 -> 2200, `comparison` 2200 -> 3000, `substitute`
   2000 -> 2800. **Safeguard**: `TOKEN_HEADROOM_WARN_THRESHOLD` (85%) is
   now checked in both `validate_batch_results.py` (post-hoc, every real
   batch) and `preflight_check.py` step 3 (pre-flight, before spend
   commitment) -- a budget drifting tight again gets flagged before it
   silently truncates a real batch, not after.
3. **Manifest/custom_id mapping bug**: re-deriving `custom_id -> CSV row`
   from the *current* `seed_templates.py` silently produced wrong
   mappings on any re-run after partial integration. **Fixed**:
   `load_id_to_row_from_manifest()` reads the frozen manifest written at
   request-build time instead. **Safeguard**: both
   `integrate_batch_results.py` and `validate_batch_results.py` prefer
   the manifest automatically and print a loud `WARNING` if it's missing
   and they have to fall back to the fragile re-derivation.
4. **Double-integration risk**: re-running integration against a results
   file already (fully or partially) integrated would silently insert
   the same pages again under a `-2`-suffixed slug, since the old
   collision-resolution loop treated *any* taken slug as "a different
   page happens to collide." Caught once by a manual page-count check
   before committing; **now structurally fixed**:
   `integrate_batch_results.py` snapshots the slug set that existed
   *before* the run starts and skips (without writing) any candidate
   slug already in that snapshot, printing which custom_ids were
   skipped and why. Verified end to end against three real scenarios
   while writing this section: an already-published slug gets skipped
   with zero write to `seed_templates.py`; a genuinely new page inserts
   normally; re-running the exact same results file a second time
   correctly no-ops. A true within-this-run collision (two NEW pages
   generating the same slug) now prints a loud `WARNING` naming the
   corn-starch/Flourless-Chocolate-Cake precedent instead of silently
   renaming and moving on.
5. **Insertion-anchor fragility**: a naive `"]\n"` search matched nested
   list closings and even a `list[tuple[str,str]] = []` type-hint line
   instead of `SEED_PAGES`'s real closing bracket. Fixed with an exact
   anchor string. **New safeguard added while writing this section**: a
   sanity check now counts `"slug":` occurrences before and after every
   insertion and raises (refusing to write) if the delta isn't exactly
   the number of new entries -- catches both a wrong insertion point and
   a double-integration slipping past guard #4 for any reason, before
   anything touches disk. Also fixed a related bug this sanity check
   surfaced immediately: a fully-skipped run (0 new entries) used to
   still write the pilot's hardcoded header comment into the file with
   nothing under it; it now writes nothing at all when there's nothing
   to insert, and the header itself is now generated from the actual CSV
   filename and today's date instead of a copy-pasted "Batch API pilot
   (2026-09-09)" string that would have silently mislabeled every future
   batch that reused this script.
6. **CSV line-ending corruption**: `csv.writer`'s default `\r\n` made a
   44-row status change look like a full-file rewrite in `git diff`.
   Fixed via explicit `lineterminator='\n'`. No dedicated safeguard
   beyond remembering this on the next CSV-writing script -- low risk
   since it's a one-line, well-understood fix, not worth automating
   further.
7. **Schema-completeness gap**: all 7 schemas were missing fields
   `frontend/lib/types.ts` actually requires (`recipe_slugs`,
   `related_technique_slugs`, `substitute_page_slug`, `item_a_link`/
   `item_b_link`, `related_collection_slugs`, `related_ingredient_slugs`,
   `related_recipe_slugs`) -- found because two real pages 404'd on a
   missing, not just empty, required key. **Safeguard**:
   `check_schemas_match_types.py`, parsing `types.ts` directly (no second
   hand-maintained field list to drift), run as preflight step 1.
8. **`pan_size` type mismatch** on 7 hand-authored (pre-pipeline) pages --
   a truthy string crashing `RecipeIngredientsPanel.tsx`'s unconditional
   `panSize?.alternatives.find(...)`. Fixed on all 7 (6 corrected, 1
   removed where the field doesn't apply). **Safeguard for anything
   generated going forward**: `pan_size` is now a real schema field with
   its own type/shape enforcement via `check_schema_types()` plus
   `check_pan_size_math()` independently recomputing expected area from
   the label's stated dimensions -- a type mismatch or bad arithmetic
   both fail validation before integration, not after a page ships.
9. **`NULLABLE_OK_FIELDS` validator false positives** (twice: once
   missing new slug/LinkRef fields, once missing `pan_size`) -- a
   hand-maintained list drifting out of sync with the schemas it was
   supposed to validate against, the exact same class of bug as #7 one
   level down. **Fixed at the root, not patched again**: `validation.py`
   now *derives* this set from the schemas themselves (any field whose
   JSON-schema type includes `"null"`, plus the shared
   `ALWAYS_EMPTY_SLUGS_ARRAY`/`ALWAYS_NULL_SLUG` marker objects) instead
   of a third copy of the list. Verified the derived set is byte-for-byte
   identical to the old hand-maintained one before replacing it. Only two
   fields (`variety_notes`, `link_terms`) aren't structurally derivable
   this way (legitimately-empty free text/arrays with no `null` in their
   type) and stay in a small, explicitly-documented residual set -- any
   new nullable LinkRef or slug field added in the future needs no update
   here at all.
10. **Companion-recipe integration regression** (self-caught): an ad hoc
    one-off script for generating companion recipes skipped the
    `step_notes` list-to-dict conversion, crashing the backend the exact
    same way the original garlic-confit bug did. Caught immediately by
    the established "run a real local backend before trusting a fix"
    discipline. **Fixed at the root**: `normalize_for_storage()` pulled
    into `validation.py` as the one shared choke point; both
    `integrate_batch_results.py` and `generate_companion_recipes.py` call
    it now instead of each re-deriving the conversion. Any future
    integration path that skips this call and ships a raw `step_notes`
    list will crash the same way -- there's no schema-level guard against
    a *new* script forgetting to call it, so this is a "know the pattern"
    risk, not a fully closed one. If a third integration path gets
    built, route it through `normalize_for_storage()` from the start.
11. **Category_roundup/companion-recipe coordination gap**: new
    collections (`pinwheel-recipes`, `blackstone-recipes`) shipped with
    every `recipe_cards` entry at `slug: null` because the pipeline
    treated every queue row as fully independent -- nothing connected "a
    new collection names N specific dishes" to "therefore also generate
    those N dishes." **Decision (user-confirmed): generate matching
    recipes too**, not deprioritize new collections or ship them
    unlinked. Built and proven on both broken collections via
    `generate_companion_recipes.py`. **Process safeguard, not yet a
    script**: for the real batch, `category_roundup` rows must be
    submitted and integrated *before* the general batch (not
    simultaneously), since their companion recipes are a second,
    dependent generation pass -- Batch API can't chain "generate a
    collection, then use its own card list to build follow-up requests"
    within one submission. Budget roughly one extra `recipe_or_dish`-
    priced request per card (~5-6 per collection x ~112 real-queue
    collections = ~550-650 extra requests). This sequencing requirement
    is documented here and in the Rollout sequencing section below, but
    nothing currently *enforces* running `category_roundup` rows first
    other than following this doc -- worth a build-time check
    (`check_queue_duplicates.py`-style script that fails if any
    `category_roundup` row is in the same submission batch as its own
    dependent recipes) if this trips someone up in practice.

### CONTENT_QUEUE.csv-wide duplicate detection (new)

The pilot's two duplicate collisions (`corn-starch` vs. the
already-published `Cornstarch` hub; two different queue rows both
generating "Flourless Chocolate Cake") were found by chance in a 50-row
sample -- there was no mechanism checking the other 12,375 rows.
**`content/scripts/check_queue_duplicates.py`** now exists and runs in
under a second against the full queue (verified: 0.16s for 12,377
`not_started` rows against 253 published pages). It normalizes each
title by stripping *all* non-alphanumeric characters (not just replacing
them with hyphens) specifically so "corn starch" and "Cornstarch" collide
in the check the same way they collide in reality, and reports two tiers:

- **Exact collisions (block submission)**: run for real against the
  actual current queue while writing this section and found **55 real
  collisions never caught before** -- 44 queue-row-vs-queue-row (mostly
  spacing/hyphenation variants like "crock pot" vs. "crockpot", "pani
  puri" vs. "panipuri") and 11 queue-row-vs-already-published (including
  the known `corn-starch`/`Cornstarch` case, plus 7 more `what-is-X`
  definition pages and `gruyère cheese` vs. the existing `gruyere-cheese`
  hub that had never been flagged before). These need to be excluded or
  merged in `CONTENT_QUEUE.csv` before any of batches 1-25 (whichever
  the real batch actually spans) is submitted.
- **Near-duplicates (human judgment, not auto-excluded)**: a looser
  singular/plural-insensitive pass, reported separately since it also
  produces some correct non-duplicates (a `recipe_or_dish` "swordfish
  recipe" next to a `category_roundup` "swordfish recipes" are two
  legitimately different pages, not a collision) -- flagged for a person
  to glance over, not something a script should silently resolve either
  way.

This does **not** catch the "two different topics independently generate
the same specific dish" class (`gluten-free-desserts` vs.
`gluten-free-dessert-recipes` both landing on "Flourless Chocolate
Cake") -- that's emergent from generation, invisible in the queue's own
title text before any request is even sent. That class is caught
downstream instead: `integrate_batch_results.py`'s guard #4 above will
at minimum flag it loudly as a same-run slug collision rather than
silently shipping both under different slugs, though a validate-time
check (comparing every result's generated title against every other
result's in the same batch, before integration ever runs) would catch it
earlier and is a reasonable next addition if this recurs at real-batch
scale.

### What this leaves genuinely open

Being direct about what's still a process rule rather than an enforced
mechanism, so it doesn't get mistaken for "fully closed":
- The `category_roundup`-before-general-batch sequencing (#11) is
  written down, not enforced by any script.
- `normalize_for_storage()` prevents the exact companion-recipe
  regression from recurring in the two paths that call it today, but a
  hypothetical third integration path that forgets to call it would
  reproduce the same crash -- there's no schema-level or import-time
  guard forcing every integration path through it.
- The queue-wide duplicate scan's near-duplicate tier is intentionally
  left to human review; scaling that judgment call across however many
  near-duplicates the real ~12,377-row scan turns up (50 in this run)
  hasn't been tried yet.

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

**Updated post-pilot: step 0 is now mandatory and non-negotiable** — see
"Bulletproofing the next batch" above for exactly what it catches and why
each check exists.

0. **Run `content/scripts/preflight_check.py` against the real batch's
   CSV.** Must pass clean — schema completeness, zero exact queue/queue
   or queue/published collisions, and a real live generation + validation
   for every template type actually present in this batch, with healthy
   `max_tokens` headroom. Do not proceed to step 1 (or, for the real
   batch, step 3 below) on a failing or skipped pre-flight.
1. **Pilot batch first** (~50 rows, a real cross-section of template
   types) — validates the prompt templates actually produce valid,
   schema-passing JSON at the expected quality bar, and gives a real
   measured cost/token number to replace the estimate from planning.
   Nothing beyond the pilot runs until this is reviewed together.
   (Already done once — this step reruns for any future pilot-scale
   change to the prompts/schemas themselves.)
2. Fix whatever the pilot reveals (prompt wording, schema mismatches,
   category_link accuracy) — expect at least one iteration here.
3. **Submit `category_roundup` rows first, as their own smaller batch,
   ahead of the general batch** — their companion recipes (see issue #11
   above) are a second, dependent generation pass that needs the
   collection's own card list to exist first; Batch API can't chain that
   within one submission. Integrate these and their companion recipes
   before moving on.
4. Submit the remaining rows as the real batch.
5. Run the full Phase 2 integration pipeline once results are back —
   `validate_batch_results.py` (including its `max_tokens`-headroom
   warning) before `integrate_batch_results.py`, never the reverse.
6. Reconcile the queue, ship, verify live — a real local backend run and
   a handful of spot-checked pages in an actual browser, not just
   `import app.seed_templates` succeeding.

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
