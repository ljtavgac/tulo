"""One-off: measures real Core Web Vitals for ONE target page (passed via
env vars -- see the matrix strategy in measure-core-web-vitals.yml, which
gives each URL its own fresh runner). Confirmed necessary live
(2026-09-20): running many Lighthouse/Chrome launches sequentially in one
process produced wildly inconsistent results for the identical URL
across two runs (1801ms vs 7447ms LCP), consistent with runner resource
buildup contaminating later measurements -- this isolates each URL
completely and also runs multiple trials of the SAME url to distinguish
real variance from measurement noise.

Also times the raw backend API round-trip for the same page, to see how
much of any slowness is the uncached (cache: "no-store") backend fetch
vs. everything else.
"""

import json
import os
import subprocess
import time

import requests

SITE_URL = "https://tulo.io"
PROD_BACKEND = os.environ["PROD_BACKEND_BASE_URL"].rstrip("/")
TARGET_KEY = os.environ["TARGET_KEY"]
TARGET_PATH = os.environ["TARGET_PATH"]
TARGET_SLUG = os.environ.get("TARGET_SLUG") or None
TRIALS = int(os.environ.get("TRIALS", "3"))


def measure_backend_latency(slug: str, attempts: int = 3) -> list[float]:
    times = []
    for _ in range(attempts):
        start = time.time()
        try:
            requests.get(f"{PROD_BACKEND}/pages/{slug}", timeout=30)
        except requests.RequestException:
            pass
        times.append((time.time() - start) * 1000)
    return times


def run_lighthouse(url: str, out_path: str) -> dict:
    subprocess.run(
        [
            "npx", "--yes", "lighthouse", url,
            "--output=json", f"--output-path={out_path}",
            "--only-categories=performance",
            "--form-factor=mobile",
            "--screenEmulation.mobile", "--screenEmulation.width=412", "--screenEmulation.height=823",
            "--throttling-method=simulate",
            "--chrome-flags=--headless=new --no-sandbox --disable-gpu",
            "--quiet",
        ],
        check=True,
        timeout=120,
    )
    with open(out_path) as f:
        data = json.load(f)
    audits = data.get("audits", {})

    def val(key, field="numericValue"):
        a = audits.get(key)
        return a.get(field) if a else None

    lcp_element_audit = audits.get("largest-contentful-paint-element", {})
    lcp_items = (lcp_element_audit.get("details", {}) or {}).get("items", [])
    lcp_node = lcp_items[0].get("items", [{}])[0] if lcp_items and lcp_items[0].get("items") else {}

    return {
        "LCP_ms": val("largest-contentful-paint"),
        "CLS": val("cumulative-layout-shift"),
        "TBT_ms": val("total-blocking-time"),
        "TTFB_ms": val("server-response-time"),
        "SpeedIndex_ms": val("speed-index"),
        "TTI_ms": val("interactive"),
        "FCP_ms": val("first-contentful-paint"),
        "performance_score": (data.get("categories", {}).get("performance", {}) or {}).get("score"),
        "LCP_element": lcp_node.get("node", {}).get("snippet") if lcp_node else None,
    }


url = f"{SITE_URL}{TARGET_PATH}"
print(f"=== {TARGET_KEY}: {url} ({TRIALS} isolated trials) ===")

if TARGET_SLUG:
    backend_times = measure_backend_latency(TARGET_SLUG)
    print(f"Raw backend /pages/{TARGET_SLUG} latency (3 attempts, ms): {[round(t) for t in backend_times]}")

trials = []
for i in range(TRIALS):
    out_path = f"/tmp/lh_{TARGET_KEY}_{i}.json"
    subprocess.run(["pkill", "-f", "chrome"], check=False)  # clean slate before each trial
    time.sleep(2)
    try:
        lab = run_lighthouse(url, out_path)
        print(f"\nTrial {i + 1}: {json.dumps(lab, indent=2)}")
        trials.append(lab)
    except Exception as e:
        print(f"\nTrial {i + 1} FAILED: {e}")

if trials:
    lcps = sorted(t["LCP_ms"] for t in trials if t.get("LCP_ms") is not None)
    print(f"\n=== {TARGET_KEY} summary across {len(trials)} trials ===")
    print(f"LCP values (ms), sorted: {[round(v) for v in lcps]}")
    if len(lcps) >= 2:
        print(f"LCP spread (max-min): {round(lcps[-1] - lcps[0])}ms -- large spread means noisy/unstable, not a fixed number")
    print(f"Median LCP: {round(lcps[len(lcps) // 2]) if lcps else 'N/A'}ms")
