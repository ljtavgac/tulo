"""Finds every real, published page that's unreachable through its
section index's "Load more" pagination -- a confirmed backend bug (see
GET /pages's paged branch in main.py): when a batch of `limit` published
items is completed by borrowing one row from the next raw window, and
that next window itself has fewer remaining raw rows than `limit`, the
endpoint incorrectly reports has_more=False even though unexamined rows
(some published) remain in that same short window.

For each of the 7 browsable section template types:
  1. Fetch the full raw list (GET /pages?template_type=X, no limit --
     every row regardless of publish status).
  2. Walk the paginated "Load more" flow (GET /pages?...&paged=true) to
     wherever it actually stops.
  3. Diff: raw slugs not in the paginated-reachable set are candidates.
  4. Individually check each candidate via GET /pages/{slug} -- a 404
     means it's *legitimately* unpublished (working as intended, not a
     bug); a 200 means it's real, published, and genuinely hidden by the
     pagination bug.

Prints one CSV-ish line per genuinely-hidden page: template_type,slug,
image_url (so it's easy to see which ones likely have unreviewed/missing
images, per the batch-1-predates-review-workflow pattern already
confirmed on baking-soda-substitute).

Usage:
    PROD_BACKEND_BASE_URL=https://your-backend python3 content/scripts/find_hidden_pages.py
"""

from __future__ import annotations

import os

import requests

SECTION_TEMPLATE_TYPES = [
    "recipe_or_dish",
    "ingredient_hub",
    "howto_technique",
    "category_roundup",
    "definition",
    "comparison",
    "substitute",
]

# Must match every section index page.tsx's own PAGE_SIZE (all 12 as of
# this writing) -- a larger walk size can fetch straight past the exact
# batch-boundary condition that triggers the bug, silently under-counting
# real hidden pages for large sections (confirmed: a first pass at 50
# found 0 candidates for recipe_or_dish/ingredient_hub, which is not
# credible for datasets that size and was almost certainly this mistake).
WALK_PAGE_SIZE = 12


def _raw_slugs(base: str, template_type: str) -> set[str]:
    r = requests.get(f"{base}/pages", params={"template_type": template_type}, timeout=60)
    r.raise_for_status()
    return {item["slug"] for item in r.json()}


def _paginated_reachable_slugs(base: str, template_type: str) -> set[str]:
    reachable: set[str] = set()
    offset = 0
    while True:
        r = requests.get(
            f"{base}/pages",
            params={"template_type": template_type, "paged": "true", "limit": WALK_PAGE_SIZE, "offset": offset},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        reachable.update(item["slug"] for item in data["items"])
        if not data["has_more"]:
            break
        offset = data["next_offset"]
    return reachable


def main() -> None:
    base = os.environ["PROD_BACKEND_BASE_URL"].rstrip("/")

    all_hidden: list[dict] = []
    for template_type in SECTION_TEMPLATE_TYPES:
        raw = _raw_slugs(base, template_type)
        reachable = _paginated_reachable_slugs(base, template_type)
        candidates = sorted(raw - reachable)
        print(f"{template_type}: {len(raw)} raw, {len(reachable)} reachable via Load more, {len(candidates)} candidate(s)")

        for slug in candidates:
            r = requests.get(f"{base}/pages/{slug}", timeout=30)
            if r.status_code == 404:
                continue  # legitimately unpublished, not a bug
            page = r.json()
            all_hidden.append({"template_type": template_type, "slug": slug, "image_url": page.get("image_url")})

    print(f"\n{len(all_hidden)} genuinely hidden (published but pagination-unreachable) page(s) total:")
    print("template_type,slug,image_url")
    for row in all_hidden:
        print(f"{row['template_type']},{row['slug']},{row['image_url']}")


if __name__ == "__main__":
    main()
