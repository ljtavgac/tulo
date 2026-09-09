# Pilot batch status

- **Batch ID**: `msgbatch_016UZwwoZ19t2V9FC4QdNfKi`
- **Submitted**: 2026-09-09T00:46:45Z
- **Requests**: 50 (see `content/pilot_batch_50.csv` for the title list)
- **Expires**: 2026-09-10T00:46:45Z (24h max; typically finishes within an hour)
- **Estimated cost**: ~$0.60 (see `content/scripts/output/pilot_batch_50_manifest.json`, not committed)
- **Status as of submission**: `in_progress`, 50 processing / 0 succeeded / 0 errored

## Result (completed 2026-09-09T00:50:32Z, ~4 minutes)

- 50/50 requests succeeded at the API level (0 request-level errors).
- Ran `content/scripts/validate_batch_results.py` against the results
  (schema-required-field check, the same depth-check `_check_content_depth()`
  enforces, double-dash scan, title-convention-per-type check,
  category_link/technique_link slug-existence check): **46/50 (92%) fully
  clean**, 0 double-dashes anywhere, 0 title-convention mismatches, both
  real `technique_link` assignments pointed at real existing how-to slugs.
- **Actual cost: $0.71** (161,939 input + 110,212 output tokens at Sonnet 5
  batch pricing) vs. the ~$0.60 pre-submission estimate -- close, output
  ran a bit higher than the max_tokens-budget-based estimate assumed.
- **4 rows need a fix-pass** (8%, in line with the plan's ~10% planning
  assumption):
  - `how-to-saute-spinach`: stopped after `steps`, missing
    `common_mistakes`/`equipment`/`faqs` (stop_reason was `tool_use`, not
    `max_tokens` -- not truncation, the model just didn't fill every
    required key despite the forced tool call).
  - `corn-starch-2`: missing `substitutes`. Also notable: this row's title
    ("corn starch") collided with an *already-published* ingredient hub
    page (`corn-starch` is one of the existing SEED_PAGES slugs), so this
    specific pilot row is likely a duplicate topic already covered on the
    site -- a queue data-quality issue, not just a generation gap.
  - `chateaubriand`: missing `substitutes`.
  - `guanciale`: model emitted **two** `tool_use` blocks in one response
    instead of one, each individually incomplete.
- Anthropic's Batch API create-batch parameters include an `output_config`
  (strict JSON-schema-enforced output, not just tool-choice biasing) that
  wasn't used here -- worth trying for the real batch if the fix-pass rate
  matters at 1,897-row scale, since it may close this exact gap.
- Quality spot-check (`diet-coke-vs-coke-zero`, `what-is-boba`,
  `hoisin-sauce-substitute`, `blackstone-recipes`, `lomo-saltado` for the
  vague "easy peruvian recipes at home" queue title): genuinely specific,
  on-voice, correctly-titled content across every template type checked.
