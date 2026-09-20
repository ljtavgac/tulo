"""One-off: compares the exact set of URLs that would appear in each
environment's sitemap.xml, without needing to fetch the real sitemap.xml
(staging's frontend sits behind Vercel's deployment-protection wall and
can't be fetched directly -- see this session's earlier finding).

Sitemap.ts's own logic: GET /pages with no params/limit/offset (every
published, non-unpublished page, per list_pages()'s legacy branch),
filtered to template_type != "static_page". Reproduces that exact
filter against both backends directly and diffs the resulting slug sets.
"""

import os

import requests

PROD_BASE = os.environ["PROD_BACKEND_BASE_URL"].rstrip("/")
STAGING_BASE = os.environ["STAGING_BACKEND_BASE_URL"].rstrip("/")


def sitemap_slugs(base_url: str) -> set[str]:
    r = requests.get(f"{base_url}/pages", timeout=60)
    r.raise_for_status()
    pages = r.json()
    return {p["slug"] for p in pages if p["template_type"] != "static_page"}


prod_slugs = sitemap_slugs(PROD_BASE)
staging_slugs = sitemap_slugs(STAGING_BASE)

print(f"Prod sitemap slug count:    {len(prod_slugs)}")
print(f"Staging sitemap slug count: {len(staging_slugs)}")

only_prod = sorted(prod_slugs - staging_slugs)
only_staging = sorted(staging_slugs - prod_slugs)

print(f"\nOn prod but NOT staging ({len(only_prod)}):")
for s in only_prod:
    print(f"  {s}")

print(f"\nOn staging but NOT prod ({len(only_staging)}):")
for s in only_staging:
    print(f"  {s}")

if not only_prod and not only_staging:
    print("\nMATCH: identical slug sets -- both sitemaps would list exactly the same URLs.")
else:
    print(f"\nMISMATCH: {len(only_prod) + len(only_staging)} slug(s) differ.")
