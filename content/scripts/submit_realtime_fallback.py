"""Fallback path when the Message Batches API is stuck/unavailable: runs
every request in a built request file through the real-time Messages API
instead, with bounded concurrency, and writes a results file in the exact
shape validate_batch_results.py / integrate_batch_results.py already
expect -- so nothing downstream of this needs to know which path a given
run took.

Built in direct response to a real incident: the Batch API accepted a
150-request batch, reported it "in_progress" indefinitely, and never
advanced past 0 succeeded for 6+ hours -- confirmed (via
msgbatch_016UZwwoZ19t2V9FC4QdNfKi / msgbatch_01UoMnQeKpdxKbdG3TkwTGUr,
both completed normally earlier the same day) not to be a request-format
or account-rate-limit problem: the exact same request content that sat
stuck in the batch completed via a direct real-time call in under 35
seconds. This script is the practical unblock for that scenario, not a
permanent replacement for the Batch API path -- real-time pricing is
higher than batch pricing, so prefer submit_batch.py whenever Batch API
is actually healthy.

Usage:
    PIPELINE_ANTHROPIC_API_KEY=... python3 content/scripts/submit_realtime_fallback.py \
        content/scripts/output/pilot_batch_150_requests.jsonl [--concurrency 10]
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_CONCURRENCY = 10
MAX_ATTEMPTS = 3


def call_one(entry: dict, api_key: str) -> dict:
    """Runs one request's `params` through the real-time endpoint and
    returns a batch-results-shaped line: {"custom_id", "result": {"type":
    "succeeded", "message": ...}} on success, or {"type": "errored", ...}
    on a request that failed every attempt -- matches the Message Batches
    API's own result shape so downstream tooling can't tell the
    difference."""
    custom_id = entry["custom_id"]
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(entry["params"]).encode(),
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                message = json.loads(resp.read())
            return {"custom_id": custom_id, "result": {"type": "succeeded", "message": message}}
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            last_error = f"HTTP {e.code}: {body[:300]}"
            # A 429 (real-time rate limit) is worth a real backoff; other
            # errors (400s -- a genuinely malformed request) won't fix
            # themselves on retry, but retrying costs little and this
            # path already isn't the fast/cheap one.
            if e.code == 429:
                time.sleep(5 * attempt)
        except Exception as e:
            last_error = str(e)
        print(f"  [{custom_id}] attempt {attempt}/{MAX_ATTEMPTS} failed: {last_error}")
    return {"custom_id": custom_id, "result": {"type": "errored", "error": {"message": last_error}}}


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <requests.jsonl> [--concurrency N]")
        raise SystemExit(1)

    requests_path = Path(sys.argv[1])
    concurrency = DEFAULT_CONCURRENCY
    if "--concurrency" in sys.argv:
        concurrency = int(sys.argv[sys.argv.index("--concurrency") + 1])

    api_key = os.environ["PIPELINE_ANTHROPIC_API_KEY"]

    with requests_path.open() as f:
        entries = [json.loads(l) for l in f]

    print(f"Running {len(entries)} requests through the real-time API, concurrency={concurrency}...")
    out_path = requests_path.parent / requests_path.name.replace("_requests.jsonl", "_results.jsonl")

    results = []
    done = 0
    start = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(call_one, entry, api_key): entry["custom_id"] for entry in entries}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            status = result["result"]["type"]
            elapsed = time.time() - start
            print(f"[{done}/{len(entries)}] {result['custom_id']}: {status} ({elapsed:.0f}s elapsed)")

    succeeded = sum(1 for r in results if r["result"]["type"] == "succeeded")
    with out_path.open("w") as out:
        for r in results:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nDone in {time.time() - start:.0f}s: {succeeded}/{len(entries)} succeeded.")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
