# Pilot batch status

- **Batch ID**: `msgbatch_016UZwwoZ19t2V9FC4QdNfKi`
- **Submitted**: 2026-09-09T00:46:45Z
- **Requests**: 50 (see `content/pilot_batch_50.csv` for the title list)
- **Expires**: 2026-09-10T00:46:45Z (24h max; typically finishes within an hour)
- **Estimated cost**: ~$0.60 (see `content/scripts/output/pilot_batch_50_manifest.json`, not committed)
- **Status as of submission**: `in_progress`, 50 processing / 0 succeeded / 0 errored

## Next steps once it completes

1. `GET https://api.anthropic.com/v1/messages/batches/msgbatch_016UZwwoZ19t2V9FC4QdNfKi`
   to confirm `processing_status: "ended"`.
2. `GET .../results` (or the `results_url` in that response) to download the
   JSONL results file, one line per `custom_id`.
3. Spot-check a handful of results against the schemas in
   `content/scripts/prompt_templates.py` before writing the Phase 2
   integration script (`content/scripts/integrate_batch_results.py`, not
   written yet) -- see `content/BATCH_CONTENT_PIPELINE_PLAN.md`'s Phase 2
   section for the full integration steps.
