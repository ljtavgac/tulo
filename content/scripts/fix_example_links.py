"""One-off: pushes the current (link-including) subject/body_preview from
_seed_outreach_examples() in main.py onto the 3 already-existing live
example rows. Editing that function only affects a brand-new, never-seeded
database -- these 3 rows were seeded on staging long before real Tulo
links were added to the source, so the live rows still had the old,
link-free bodies. Matched by target_domain, which is stable and unique
per example.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/fix_example_links.py
"""

from __future__ import annotations

import os

import requests

# Mirrors the current body_preview text in _seed_outreach_examples()
# (main.py) exactly -- keep these two in sync if that function changes
# again.
UPDATES = {
    "example-cooking-blog.test": {
        "subject": "A free pan-size converter your readers might like",
        "body": (
            "Hi Jamie -- I noticed your banana bread post mentions swapping pan sizes by eye. "
            "We built a free pan-size/yield calculator that adjusts bake time too -- here it is "
            "live on our own banana bread recipe: https://tulo.io/food/recipes/banana-nut-bread. "
            "Thought it might be a useful link for that post."
        ),
    },
    "example-nutrition-site.test": {
        "subject": "A live recipe nutrition recalculator (swap-aware)",
        "body": (
            "Hi Morgan -- following your piece on recipe substitutions, we built a tool that "
            "recalculates a recipe's nutrition live as you swap ingredients or change servings -- "
            "here it is in action on our chicken broccoli rice casserole recipe: "
            "https://tulo.io/food/recipes/chicken-broccoli-rice-casserole. Could be a relevant "
            "link for readers making substitutions."
        ),
    },
    "example-journalist-outlet.test": {
        "subject": "Source for your ingredient-substitution piece",
        "body": (
            "Hi -- happy to help as a source. One common mistake: substituting baking soda for "
            "baking powder 1:1 -- baking soda is roughly 3x stronger and needs its own acid to "
            "activate, so the swap either falls flat or turns bitter. Full ratio breakdown here "
            "if useful for the piece: https://tulo.io/food/substitutes/baking-soda-substitute. "
            "Happy to expand with a couple more examples too."
        ),
    },
}


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/admin/outreach-queue/list.json", auth=auth, params={"status": "all"}, timeout=30)
    r.raise_for_status()
    rows = [row for row in r.json() if row["is_example"] and row["target_domain"] in UPDATES]

    print(f"{len(rows)} example row(s) to update (of {len(UPDATES)} expected).")
    for row in rows:
        update = UPDATES[row["target_domain"]]
        resp = requests.post(
            f"{base}/admin/outreach-queue/update-content",
            auth=auth,
            data={"prospect_id": row["id"], "subject": update["subject"], "body": update["body"], "show": row["status"]},
            timeout=30,
            allow_redirects=False,
        )
        ok = resp.status_code == 303
        print(f"  {'updated' if ok else f'FAILED ({resp.status_code})'}  id={row['id']}  {row['target_domain']}")


if __name__ == "__main__":
    main()
