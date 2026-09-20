"""One-off: measures real Core Web Vitals for a sample of live prod pages
spanning every template type, via Lighthouse CLI run directly against a
locally-launched headless Chrome (not Google's hosted PageSpeed Insights
API -- its unauthenticated tier hits 429 almost immediately from shared
CI IP ranges, confirmed live 2026-09-20). Also times the raw backend API
round-trip for the same pages, to see how much of any slowness is the
uncached (cache: "no-store") backend fetch vs. everything else (JS
bundle, images, third-party ads).

Lighthouse's lab data has no real INP (that's a field-only metric,
measured from actual user interactions) -- Total Blocking Time is the
standard lab proxy, reported as such, never presented as if it were INP.
"""

import json
import os
import subprocess
import time

import requests

SITE_URL = "https://tulo.io"
PROD_BACKEND = os.environ["PROD_BACKEND_BASE_URL"].rstrip("/")

SAMPLES = {
    "homepage": ("/", None),
    "recipe_or_dish_1": ("/food/recipes/chicken-broccoli-rice-casserole", "chicken-broccoli-rice-casserole"),
    "recipe_or_dish_2": ("/food/recipes/smoked-haddock-chowder", "smoked-haddock-chowder"),
    "ingredient_hub": ("/food/ingredients/chives", "chives"),
    "howto_technique": ("/food/how-to/how-to-cook-lobster", "how-to-cook-lobster"),
    "definition_1": ("/food/what-is/what-is-pureeing", "what-is-pureeing"),
    "definition_2": ("/food/what-is/what-is-a-dry-shake", "what-is-a-dry-shake"),
    "comparison_1": ("/food/comparisons/baking-powder-vs-baking-soda", "baking-powder-vs-baking-soda"),
    "comparison_2": ("/food/comparisons/butter-vs-shortening-vs-oil-for-greasing-pans-which-works-best", "butter-vs-shortening-vs-oil-for-greasing-pans-which-works-best"),
    "substitute_1": ("/food/substitutes/baking-soda-substitute", "baking-soda-substitute"),
    "substitute_2": ("/food/substitutes/best-substitutes-for-white-wine-vinegar", "best-substitutes-for-white-wine-vinegar"),
    "category_roundup": ("/food/collections/eggplant-recipes", "eggplant-recipes"),
    "tool_page": ("/food/tools/conversion-calculator", "conversion-calculator"),
}


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


results = {}
for template_type, (path, slug) in SAMPLES.items():
    url = f"{SITE_URL}{path}"
    print(f"\n=== {template_type}: {url} ===")

    backend_times = measure_backend_latency(slug) if slug else None
    if backend_times:
        print(f"  Raw backend /pages/{slug} latency (3 attempts, ms): {[round(t) for t in backend_times]}")

    out_path = f"/tmp/lh_{template_type}.json"
    try:
        lab = run_lighthouse(url, out_path)
        print(f"  Lighthouse (mobile, simulated throttling): {json.dumps(lab, indent=2)}")
    except Exception as e:
        print(f"  Lighthouse run failed: {e}")
        lab = {"error": str(e)}

    results[template_type] = {"url": url, "backend_latency_ms": backend_times, "lighthouse": lab}

print("\n\n=== FULL RESULTS (JSON) ===")
print(json.dumps(results, indent=2))
