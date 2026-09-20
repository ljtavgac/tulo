"""One-off: measures real Core Web Vitals (via Google PageSpeed Insights,
mobile strategy) for a sample of live prod pages spanning every template
type, and separately times the raw backend API round-trip for the same
pages -- to see how much of any slowness is the uncached (cache: "no-store")
backend fetch vs. everything else (JS bundle, images, third-party ads).

PSI's Lighthouse (lab) result always has LCP/CLS/TBT/server-response-time;
real field INP only appears if the URL has enough Chrome UX Report (CrUX)
traffic, which a small/new site usually doesn't -- reported as
"not available" rather than guessed if absent, never fabricated.
"""

import json
import os
import time

import requests

SITE_URL = "https://tulo.io"
PROD_BACKEND = os.environ["PROD_BACKEND_BASE_URL"].rstrip("/")

# One representative published slug per template type.
SAMPLES = {
    "homepage": ("/", None),
    "recipe_or_dish": ("/food/recipes/chicken-broccoli-rice-casserole", "chicken-broccoli-rice-casserole"),
    "ingredient_hub": ("/food/ingredients/chives", "chives"),
    "howto_technique": ("/food/how-to/how-to-cook-lobster", "how-to-cook-lobster"),
    "definition": ("/food/what-is/what-is-pureeing", "what-is-pureeing"),
    "comparison": ("/food/comparisons/baking-powder-vs-baking-soda", "baking-powder-vs-baking-soda"),
    "substitute": ("/food/substitutes/baking-soda-substitute", "baking-soda-substitute"),
    "category_roundup": ("/food/collections/eggplant-recipes", "eggplant-recipes"),
    "tool_page": ("/food/tools/conversion-calculator", "conversion-calculator"),
}

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


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


def run_psi(url: str) -> dict:
    params = {"url": url, "strategy": "mobile", "category": "performance"}
    r = requests.get(PSI_ENDPOINT, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    lh = data.get("lighthouseResult", {})
    audits = lh.get("audits", {})

    def audit_val(key, field="numericValue"):
        a = audits.get(key)
        return a.get(field) if a else None

    field_data = data.get("loadingExperience") or data.get("originLoadingExperience") or {}
    metrics = field_data.get("metrics", {})

    return {
        "lab": {
            "LCP_ms": audit_val("largest-contentful-paint"),
            "CLS": audit_val("cumulative-layout-shift"),
            "TBT_ms": audit_val("total-blocking-time"),
            "TTFB_ms": audit_val("server-response-time"),
            "SpeedIndex_ms": audit_val("speed-index"),
            "TTI_ms": audit_val("interactive"),
        },
        "field_INP_ms": (metrics.get("INTERACTION_TO_NEXT_PAINT", {}) or {}).get("percentile"),
        "field_LCP_ms": (metrics.get("LARGEST_CONTENTFUL_PAINT_MS", {}) or {}).get("percentile"),
        "field_CLS": (metrics.get("CUMULATIVE_LAYOUT_SHIFT_SCORE", {}) or {}).get("percentile"),
        "has_field_data": bool(metrics),
    }


results = {}
for template_type, (path, slug) in SAMPLES.items():
    url = f"{SITE_URL}{path}"
    print(f"\n=== {template_type}: {url} ===")

    backend_times = measure_backend_latency(slug) if slug else None
    if backend_times:
        print(f"  Raw backend /pages/{slug} latency (3 attempts, ms): {[round(t) for t in backend_times]}")

    try:
        psi = run_psi(url)
    except requests.RequestException as e:
        print(f"  PSI request failed: {e}")
        psi = {"error": str(e)}

    print(f"  PSI lab metrics: {json.dumps(psi.get('lab', {}), indent=2) if 'lab' in psi else psi}")
    if psi.get("has_field_data"):
        print(f"  PSI field data: INP={psi.get('field_INP_ms')}ms LCP={psi.get('field_LCP_ms')}ms CLS={psi.get('field_CLS')}")
    else:
        print("  PSI field data: not available (insufficient real-user traffic for CrUX)")

    results[template_type] = {"url": url, "backend_latency_ms": backend_times, "psi": psi}
    time.sleep(2)  # PSI's unauthenticated tier is rate-limited

print("\n\n=== FULL RESULTS (JSON) ===")
print(json.dumps(results, indent=2))
