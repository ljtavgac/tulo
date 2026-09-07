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
