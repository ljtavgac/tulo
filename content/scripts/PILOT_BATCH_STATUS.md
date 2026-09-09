# Pilot batch status

- **Batch ID**: `msgbatch_016UZwwoZ19t2V9FC4QdNfKi`
- **Submitted**: 2026-09-09T00:46:45Z
- **Requests**: 50 (see `content/pilot_batch_50.csv` for the title list)
- **Expires**: 2026-09-10T00:46:45Z (24h max; typically finishes within an hour)
- **Estimated cost**: ~$0.60 (see `content/scripts/output/pilot_batch_50_manifest.json`, not committed)
- **Status as of submission**: `in_progress`, 50 processing / 0 succeeded / 0 errored

## Result (batch completed 2026-09-09T00:50:32Z, ~4 minutes; fix-passes and
## integration completed the same session)

- 50/50 requests succeeded at the API level (0 request-level errors).
- **Actual cost: $0.71** for the batch (161,939 input + 110,212 output
  tokens at Sonnet 5 batch pricing) + **~$0.14** for the real-time fix-pass
  API calls (standard, non-batch pricing) = **~$0.85 all-in** for the full
  50-title pilot including corrections, vs. the ~$0.60 pre-submission
  estimate for the batch alone.

### A validation gap was found and fixed mid-pilot

The first validation pass only checked "is this field present and
non-empty" and reported 46/50 (92%) clean. That check was **not strong
enough** -- it missed a real corruption class: several array/object fields
(`steps`, `common_mistakes`, `equipment`, `faqs`, `step_notes`) came back as
non-empty **strings** containing literal `<parameter name="item">` tag
fragments instead of proper JSON arrays/objects (a tool-calling XML format
leaking into what should have been a clean array value) -- a non-empty
string still passes a truthiness check, so this slipped through undetected
until `resync_content()` broke on `'str' object has no attribute 'items'`
during a real local backend run.

Fixed by adding real recursive type-checking against the JSON schema
(`content/scripts/validation.py`, shared by the validator and the fix-pass
script now) and an explicit instruction in the prompt style guide telling
the model never to emit that tag syntax. Re-validating with the stronger
check found **12/50 (24%) actually needed a fix-pass**, not 4 -- notably
**all 8 of the pilot's `howto_technique` pages** were affected in some way.

### Fix-pass results

Ran each of the 12 through the live (non-batch) Messages API, retrying up
to 4 times against the strengthened validator:
- **8 fixed cleanly**: `how-to-brew-green-tea`, `what-is-a-latte`,
  `how-to-saute-spinach`, `gluten-free-bread-recipe`,
  `easy-swedish-recipes-at-home`, `how-to-make-garlic-confit`,
  `manhattan-recipe`, `what-is-dubai-chocolate` (1-2 attempts each).
- **4 failed all 4 attempts**, still producing the same tag corruption even
  with the corrected prompt: `how-to-roast-sweet-peppers`,
  `how-to-make-matcha-latte`, `how-to-make-chai-tea`,
  `how-to-make-cold-foam`. This looks like a more persistent model behavior
  than a prompt-wording fix resolves -- **excluded from this batch**, not
  forced. Worth trying Anthropic's stricter `output_config`
  (JSON-schema-enforced output, a real decoding-level constraint rather
  than tool-choice biasing) for these specifically, and for the full
  1,897-row batch generally, before assuming a similar ~8% "genuinely stuck"
  rate at scale.

### Two duplicate-topic exclusions (data-quality finding in the queue itself)

- `corn-starch`: this pilot row's generated content was valid, but its
  title collided with an **already-published** ingredient hub page
  (`corn-starch` is an existing `SEED_PAGES` slug) -- excluded as a
  duplicate, not a generation failure.
- `gluten-free-desserts` / `gluten-free-dessert-recipes`: two different
  queue rows independently generated the same specific dish ("Flourless
  Chocolate Cake"). Kept one (`gluten-free-dessert-recipes`), excluded the
  other. Worth a broader dedup pass on `CONTENT_QUEUE.csv` before the real
  batch -- these two collisions in a 50-row sample suggest more exist across
  the full 12,425-row queue.

### Final outcome: 44/50 published

Integrated via `content/scripts/integrate_batch_results.py` into
`backend/app/seed_templates.py`: 193 original pages + 44 new = 237 total.
Verified: `python -c "import app.seed_templates"` passes (runs the same
`_check_content_depth()` and `_check_no_double_dashes()` the rest of the
site is held to), a real local backend run serves the new pages correctly
(spot-checked `/pages/lomo-saltado`, `/pages/nigiri`,
`/pages/blackstone-recipes`, all HTTP 200 with correct cross-linking
fields). `content/CONTENT_QUEUE.csv` updated: the 44 published titles
flipped from `not_started` to `published`; the 6 excluded rows (2
duplicates, 4 stuck) remain `not_started`.

Quality spot-check across template types (`diet-coke-vs-coke-zero`,
`what-is-boba`, `hoisin-sauce-substitute`, `blackstone-recipes`,
`lomo-saltado` for the vague "easy peruvian recipes at home" queue title):
genuinely specific, on-voice, correctly-titled content.

### Update: root cause found and fixed properly -- all 48 now shipped

The 4 persistently-corrupted rows turned out to have a real fix, not just
more retries. Anthropic's Messages API has an `output_config` parameter
(`{"format": {"type": "json_schema", "schema": {...}}}`) that constrains
token decoding directly against a JSON Schema -- a real guarantee, unlike
forced tool-choice, which only biases the model without strictly
enforcing the schema. Tested directly: all 4 previously-stuck rows came
back clean on the **first** attempt once switched to this mechanism.

**The whole pipeline now uses `output_config` instead of tool-choice**
(`prompt_templates.py`'s `to_strict_schema()` strips the two things
`output_config` doesn't support -- `minItems` above 1 and anything but
`additionalProperties: false` on objects -- from the richer SCHEMA_BY_TYPE
dicts at request-build time). `validation.py`'s `extract_content()`
handles both response shapes for backward compatibility with the
already-downloaded tool-choice-based pilot results.

**A second, separate, more serious bug was found and fixed while
integrating those 4 pages**: every one of the 7 schemas was missing at
least one field that `frontend/lib/types.ts` requires (all cross-linking
fields: `related_recipe_slugs`, `recipe_slugs`, `related_technique_slugs`,
`substitute_page_slug`, `hub_page_slug`, `item_a_link`/`item_b_link`,
`related_collection_slugs`, `related_ingredient_slugs`). This caused two
real production pages (`how-to-make-garlic-confit`,
`how-to-saute-spinach`) to fail to load -- the frontend assumes these
fields are always present as an empty array/null, and a genuinely
*missing* key (not just an empty one) crashed rendering. Fixed two ways:
1. `patch_missing_link_fields.py` mechanically added the correct default
   (`[]` or `null` -- these are either computed live at serve time or left
   for future human curation, never something the model should generate)
   to all 48 already-integrated pages, verified against a live local
   backend run hitting every one of the 48 `/pages/{slug}` endpoints
   directly and checking every required field's presence.
2. Every `SCHEMA_BY_TYPE` entry now declares these fields explicitly
   (always `[]`/`null` by instruction). `check_schemas_match_types.py` is
   a new permanent guard -- it parses `types.ts` directly (rather than
   hand-maintaining a second required-fields list, which is exactly what
   let the two lists drift apart the first time) and fails loudly if any
   schema is ever missing a required field again. Run this before ever
   submitting a real batch.

**Final result: 48/50 pilot titles published** (193 -> 241 pages), the 2
duplicate-topic exclusions (`corn-starch`, `gluten-free-desserts`) still
excluded as documented above. `CONTENT_QUEUE.csv` fully reconciled.

### Not yet done

- This only updated the repo (`backend/app/seed_templates.py` +
  `CONTENT_QUEUE.csv`), committed and pushed to `main`. Getting these 48
  pages actually live on the production site still requires the backend's
  normal deploy process to pick up the push and run `resync_content()` --
  same as every previous content change this session. If a page still
  doesn't load after that deploy completes, it's worth re-checking rather
  than assuming -- this pilot already found two real content bugs behind
  an initial "probably just not deployed yet" instinct.
- Image backfill (`fetch_images()`) for the 48 new pages hasn't run --
  they'll render without a photo until that runs, same self-healing
  behavior as the rest of the site.
- The 2 excluded duplicate-topic rows are not queued for retry --
  flagged for a decision (e.g. using `corn-starch`'s generated content to
  refresh the existing page instead of publishing a duplicate).
