# Weekly Content Workflow — CONTENT_QUEUE.csv

## The one-button rule
Every row in `CONTENT_QUEUE.csv` is already prioritized (sorted by volume,
pre-assigned to a `batch_number`), already deduplicated (it's the current
clean state of the master catalogue), and already tagged with which
template to use. Nothing needs to be re-strategized week to week.

## Weekly process (give this to Claude Code as the instruction)
1. Open `CONTENT_QUEUE.csv`.
2. Filter to `status == "not_started"`, take the **lowest `batch_number`** present.
3. Build one page per row using the template named in `template_type`
   (see `PAGE_TEMPLATES.md` for the spec of each).
4. Once a row's page is built and published, update that row's `status`
   to `"published"` and save the file back.
5. Done. Next week, repeat — it will automatically pick up the next
   `batch_number` group, since the last one is now marked published.

## Batch 0 = build first, one-time only
`batch_number: 0` contains the Homepage and the 3 Tool pages — these are
P0 priority per the launch plan and should be built before Batch 1's
500 pages, not as part of the weekly rotation.

## Runway
25 batches of 500 (Batch 1–25) = ~5.8 months of Tier 1 content at
500 pages/week before this queue runs dry. When it's running low
(e.g., 2-3 batches of runway left), that's the natural time to come
back and extend it — either by pulling in Tier 1B (KD 30-35, the next
tier down) or by running new discovery batches, same process as
throughout the original research. Everything else in between: no
check-ins needed.

## If you add new keywords later
Any new batch of researched keywords should go through the same
dedup-and-tier check before being appended to `CONTENT_QUEUE.csv` with
a new `batch_number` continuing the sequence — don't hand-merge into
the middle of the existing priority order, since that's what
reintroduces the error risk this system is designed to avoid.

---

## Build order: templates before content (do this first)

**Before touching `CONTENT_QUEUE.csv` at all**, build and review ONE page per template type — not 500, not even a full batch. This is a cost-control step: confirm the structure, styling, brand assets, image sourcing, Instacart module, and ad placements are right on a single example of each page type before generating anything at scale.

1. Build one **Homepage**
2. Build one **Recipe page** (pick any real row from the queue as the test case)
3. Build one **Ingredient Hub page**
4. Build one **How-To/Technique page**
5. Build one **Definition page**
6. Build one **Comparison page**
7. Build one **Category Roundup page**
8. Build one **Substitute page**
9. Build the 3 **Tool pages**

That's 11 pages total, covering every template type. Review and align on all of them — layout, brand assets applied correctly, stock photo sourcing working, Instacart module placeholder in place, ad units positioned per spec — **before** running Batch 0 or Batch 1 from `CONTENT_QUEUE.csv`. Once the templates are approved, THEN proceed into the queue as described above.

This exists specifically to avoid burning content-generation credits on 2,000 pages built from a template that needs revision.

## What actually happened, and the fix (keep this section updated)

The pilot phase above ran long: by the time this note was added, the site
had 99 published pages (not 11) built through iterative feature work and
direct requests, and none of it had been checked against
`CONTENT_QUEUE.csv` before publishing — 35 of those 99 pages (mostly the
technique/ingredient glossary and the 8 cuisine collection pages) have no
matching title in the queue at all, and the queue's own `status` column
had drifted to only reflecting 4 of the 99 as `published`. Both are now
reconciled: every already-published page's matching queue row (by exact
`title`/`proposed_article_title` + `template_type`) is marked
`published`; the 35 with no match were appended as new rows with
`batch_number: off_queue` and `page_purpose: off_queue_addition` so the
CSV is a complete, accurate record of everything actually live, not just
what came from the queue.

**Going forward, this is a hard rule, not a suggestion:** before creating
any new page whose purpose is SEO/keyword targeting, check its title
against `CONTENT_QUEUE.csv` first (`title` and `proposed_article_title`
columns). If a close match exists, use the queue's row (its title,
template, and priority) instead of inventing a new one. If a page is
needed for a reason that isn't keyword targeting (e.g. a definitional
page purely to support a linking feature someone asked for), that's a
legitimate reason to go off-queue — but say so explicitly and add the row
with `page_purpose: off_queue_addition`, `batch_number: off_queue`, the
same way this reconciliation did, rather than letting the queue silently
stop being the full picture again. And per step 4 of the weekly process
above: the moment a queue-sourced page actually goes live, flip its
`status` to `published` in the same change — don't let this drift a
second time.

## Ongoing content QA — prevent future depth gaps, don't just fix past ones

A content-depth gap must not become a recurring problem as the weekly
queue scales to hundreds, then thousands, of pages. This is a standing
part of the weekly process, not a one-time cleanup:

1. Before marking any page's `status` as `published` in
   `CONTENT_QUEUE.csv`, verify it against the required-sections checklist
   for its `template_type` (per `PAGE_TEMPLATES.md`): Recipe pages need
   variations, storage/reheating, nutrition (note or per-ingredient data
   for live recalculation), FAQ, reader tips, and step notes; Ingredient
   Hub pages need buying tips, pairing suggestions, and FAQ; How-To pages
   need the intro paragraph, common mistakes, equipment, and FAQ; and so
   on for each type (Definition, Comparison, Substitute, Category
   Roundup) per its own template spec.
2. This check is per-page, not per-batch — a batch isn't done because
   500 pages exist, it's done because 500 pages each pass their
   checklist.
3. **This is mechanically enforced, not just a manual step.**
   `backend/app/seed_templates.py`'s `_REQUIRED_CONTENT_FIELDS` dict and
   `_check_content_depth()` function run automatically at import time —
   the same module `resync_content()` uses to push every edit to
   production on the next deploy — and hard-fail (`raise ValueError`,
   listing every gap found) if any page of a checked template type is
   missing one of its required fields. A page that fails this check
   cannot ship; there's no way for a required-field gap to reach
   production silently. Extend `_REQUIRED_CONTENT_FIELDS` whenever
   `PAGE_TEMPLATES.md`'s spec for a template type changes, so the two
   stay in sync.
4. Some modules are legitimately data-dependent, not template fields —
   an Ingredient Hub's "recipes using this ingredient" list and a
   Recipe's ingredient-swap tool are both computed live from which
   recipes' ingredients happen to set `hub_slug` to that ingredient's
   page, not authored per-page. These can be correctly empty (no recipe
   on the site yet uses that ingredient, or none of a recipe's
   ingredients happen to match an existing Ingredient Hub) without being
   a bug. That's fine, but treat it as a deliberate, logged exception,
   not a silent gap indistinguishable from a missed section: note which
   ingredients/recipes were deliberately left unlinked and why (e.g. "no
   recipe uses this ingredient yet" or "this hub is a specialty variety,
   not what a generic mention of the same pantry ingredient means")
   rather than just leaving it unexplained.
5. Report status honestly. Don't report a batch as complete without
   stating which pages, if any, have logged exceptions per point 4 above
   — "the depth check passed" and "every module has real content" are
   different claims; make the one that's actually true.

This applies starting with the very next batch generated from
`CONTENT_QUEUE.csv`, not just historical backfill work.
