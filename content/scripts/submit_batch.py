"""Submits a built request file to the Message Batches API, polls until
it finishes, and downloads the results file. The one step of the
pipeline that wasn't previously saved as a reusable script -- the
original 50-title pilot and the two follow-up fix passes were each
submitted with one-off inline calls instead.

Usage:
    PIPELINE_ANTHROPIC_API_KEY=... python3 content/scripts/submit_batch.py \
        content/scripts/output/pilot_batch_150_requests.jsonl

Writes the results file next to the request file, replacing
"_requests.jsonl" with "_results.jsonl" -- the shape
validate_batch_results.py and integrate_batch_results.py already expect.

Polls every POLL_INTERVAL_SECONDS. A real batch finishes within an hour
in the common case, worst case 24 hours (per Anthropic's docs) -- this
script blocks and polls for as long as that takes, since there's no
useful partial-result state to act on before `ended`.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.anthropic.com/v1/messages/batches"
POLL_INTERVAL_SECONDS = 30


def _request(method: str, url: str, api_key: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {url} -> HTTP {e.code}: {body_text[:1000]}") from e


def submit(requests_path: Path, api_key: str) -> str:
    with requests_path.open() as f:
        requests = [json.loads(l) for l in f]
    print(f"Submitting {len(requests)} requests from {requests_path}...")
    result = _request("POST", API_BASE, api_key, {"requests": requests})
    batch_id = result["id"]
    print(f"Batch submitted: {batch_id} (status: {result['processing_status']})")
    return batch_id


def poll_until_ended(batch_id: str, api_key: str) -> dict:
    while True:
        result = _request("GET", f"{API_BASE}/{batch_id}", api_key)
        status = result["processing_status"]
        counts = result.get("request_counts", {})
        print(f"  status={status} counts={counts}")
        if status == "ended":
            return result
        time.sleep(POLL_INTERVAL_SECONDS)


def download_results(results_url: str, api_key: str, out_path: Path) -> int:
    req = urllib.request.Request(
        results_url,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
    )
    with urllib.request.urlopen(req) as resp, out_path.open("wb") as out:
        out.write(resp.read())
    with out_path.open() as f:
        return sum(1 for _ in f)


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <requests.jsonl>")
        raise SystemExit(1)

    requests_path = Path(sys.argv[1])
    api_key = os.environ["PIPELINE_ANTHROPIC_API_KEY"]

    batch_id = submit(requests_path, api_key)
    result = poll_until_ended(batch_id, api_key)

    results_url = result.get("results_url")
    if not results_url:
        print(f"Batch ended with no results_url -- full response: {result}")
        raise SystemExit(1)

    out_path = requests_path.parent / requests_path.name.replace("_requests.jsonl", "_results.jsonl")
    n = download_results(results_url, api_key, out_path)
    print(f"Downloaded {n} result lines to {out_path}")


if __name__ == "__main__":
    main()
