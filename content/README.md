# Content planning

Source-of-truth docs for Tulo's content strategy and publishing process.

- `PAGE_TEMPLATES.md` — spec for each of the 9 page templates, and the competitive-gap reasoning behind them
- `WORKFLOW.md` — the build order (templates before content) and the ongoing weekly batch process
- `launch_plan.md` — the publish-cadence plan (signal-gated ramp, not a flat schedule)
- `CONTENT_QUEUE.csv` — 12,495 prioritized, pre-classified pages, ready to drive the weekly batch process once the page templates are reviewed and approved

Nothing in this directory is read by the app yet. Once template review is done, `WORKFLOW.md`'s weekly process becomes the next phase: taking rows from `CONTENT_QUEUE.csv`, generating a page per row, and marking each row's `status` published as it goes.
