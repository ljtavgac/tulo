"""One-off outreach sourcing batch: calls POST /admin/outreach-queue/create
once per real (non-example) tool-pitch prospect, queued for human review
in the outreach portal -- never sends anything itself.

Sourced two ways, both grounded in real data, neither guessed:
- Semrush backlink-gap analysis: domains already linking to a competitor's
  pan-size conversion page (sallysbakingaddiction.com/cake-pan-sizes/) or
  nutrition-label tool (nutrifox.com) -- i.e. blogs that have already
  shown willingness to link to exactly this kind of resource.
- Filtered by hand to real, English-language food/recipe blogs -- dropped
  generic platforms, aggregators, and non-food sites Semrush's raw list
  also included (yahoo.com, wikipedia.org, wordpress.org, etc.).

No contact_email for any of these -- Semrush's backlink data names a
domain, never a person to contact. Left null on purpose rather than
guessed at (see /admin/outreach-queue/update-contact, built specifically
to fill this gap in the portal once a human looks up the real contact,
e.g. via the blog's own contact page).

Usage:
    BACKEND_BASE_URL=https://your-staging-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/add_outreach_prospects.py
"""

from __future__ import annotations

import os

import requests

PAN_SIZE_PITCH = {
    "subject": "A pan-size & yield calculator that adjusts bake time too",
    "body_preview": (
        "Hi -- I noticed you've linked to pan-size conversion resources before, so thought this might "
        "be a useful addition: we built a free pan-size/yield calculator that recalculates bake time "
        "along with the substitution (not just volume), for readers who only have a different pan on "
        "hand. Happy to share the link if it'd be useful for a relevant post."
    ),
}

NUTRITION_PITCH = {
    "subject": "A live, swap-aware recipe nutrition tool",
    "body_preview": (
        "Hi -- saw you've linked to nutrition-label tools before, so wanted to flag something a bit "
        "different: we built a free tool that recalculates a recipe's nutrition live as a reader "
        "changes servings or swaps an ingredient, rather than a single static label. Happy to share "
        "the link if it'd be a useful addition to a relevant post."
    ),
}

# domain -> which pitch angle (pan-size vs nutrition), based on which
# competitor page Semrush found them already linking to.
PAN_SIZE_PROSPECTS = [
    "natashaskitchen.com",
    "alexandracooks.com",
    "smittenkitchen.com",
    "eatwithclarity.com",
    "simplejoy.com",
    "bellyfull.net",
    "completelydelicious.com",
    "wellseasonedstudio.com",
    "sweetestmenu.com",
    "onelovelylife.com",
]

NUTRITION_PROSPECTS = [
    "cookieandkate.com",
    "themediterraneandish.com",
    "acouplecooks.com",
    "playswellwithbutter.com",
    "cookthestory.com",
    "livelytable.com",
    "simple-veganista.com",
]


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    batches = [(PAN_SIZE_PROSPECTS, PAN_SIZE_PITCH), (NUTRITION_PROSPECTS, NUTRITION_PITCH)]
    for domains, pitch in batches:
        for domain in domains:
            r = requests.post(
                f"{base}/admin/outreach-queue/create",
                auth=auth,
                json={
                    "pitch_type": "tool_pitch",
                    "target_domain": domain,
                    "subject": pitch["subject"],
                    "body_preview": pitch["body_preview"],
                },
                timeout=30,
            )
            if r.status_code == 200:
                print(f"{domain}: queued (id {r.json()['created_prospect_id']})")
            else:
                print(f"{domain}: FAILED ({r.status_code}) {r.text[:200]}")


if __name__ == "__main__":
    main()
