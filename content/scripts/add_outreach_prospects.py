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

Originally split into two pitch angles (pan-size vs. nutrition) matched
to which competitor page each domain had linked to, describing tools that
weren't directly linkable (the pan-size/yield resizing and live nutrition
recalculation both live inside individual recipe pages, not as their own
URL). Replaced with one unified pitch linking Tulo's three actual
standalone tool pages instead -- every prospect gets the same real,
clickable links regardless of which competitor page originally surfaced
them, since there's no reason to split the pitch once it's not tied to a
specific tool that needs its own separate framing.

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

# Single source of truth for the tool-pitch template -- also duplicated
# (deliberately, these scripts don't share a package) in
# content/scripts/update_outreach_pitch_template.py, which backfills this
# same text onto prospects created before this template existed.
TOOL_PITCH = {
    "subject": "Free kitchen tools your readers might like",
    "body_preview": (
        "Hi there,\n"
        "\n"
        "I came across your site while looking at kitchen conversion and nutrition resources -- good "
        "stuff for readers.\n"
        "\n"
        "We've built a few free tools at Tulo that might be a useful addition alongside what you've "
        "already got:\n"
        "\n"
        "Kitchen Conversion Calculator -- cups, tablespoons, grams, ounces, and oven temps, US <-> "
        "metric: https://tulo.io/food/tools/conversion-calculator\n"
        "\n"
        "Cooking Time & Temperature Guide -- safe cook times and USDA minimum internal temps by protein "
        "and method (oven, air fryer, grill): https://tulo.io/food/tools/time-temperature-guide\n"
        "\n"
        "Custom Recipe Generator -- built around whatever's already in a reader's kitchen: "
        "https://tulo.io/food/tools/recipe-generator\n"
        "\n"
        "All free, no signup required. Happy to answer any questions if one of these would be a useful "
        "addition to a relevant post.\n"
        "\n"
        "Thanks for your time,\n"
        "\n"
        "Tulo Team"
    ),
}

# Sourced via two separate Semrush backlink-gap queries (pan-size vs.
# nutrition competitor pages); kept as one combined list since both now
# get the same unified pitch above.
PROSPECT_DOMAINS = [
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

    for domain in PROSPECT_DOMAINS:
        r = requests.post(
            f"{base}/admin/outreach-queue/create",
            auth=auth,
            json={
                "pitch_type": "tool_pitch",
                "target_domain": domain,
                "subject": TOOL_PITCH["subject"],
                "body_preview": TOOL_PITCH["body_preview"],
            },
            timeout=30,
        )
        if r.status_code == 200:
            print(f"{domain}: queued (id {r.json()['created_prospect_id']})")
        else:
            print(f"{domain}: FAILED ({r.status_code}) {r.text[:200]}")


if __name__ == "__main__":
    main()
