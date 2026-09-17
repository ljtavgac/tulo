"""One-off catch-up batch: rewrites subject/body_preview, via POST
/admin/outreach-queue/update-content, on every real (non-example)
tool_pitch prospect that hasn't sent yet -- the batch
add_outreach_prospects.py already queued before this unified template
existed. Never approves or sends anything itself; only edits the text a
human will review before deciding.

Only touches rows with sent_at still null: a prospect that's already gone
out under the old pitch is done, and editing its stored text now wouldn't
change what a recipient already received -- it'd just make the portal's
record of it inaccurate.

See TOOL_PITCH in add_outreach_prospects.py for why this template replaced
the original two pitch angles (duplicated here rather than imported --
these one-off scripts don't share a package).

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/update_outreach_pitch_template.py
"""

from __future__ import annotations

import os

import requests

NEW_SUBJECT = "Free kitchen tools your readers might like"
NEW_BODY = (
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
)


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(
        f"{base}/admin/outreach-queue/list.json",
        auth=auth,
        params={"status": "all", "pitch_type": "tool_pitch"},
        timeout=30,
    )
    r.raise_for_status()
    prospects = r.json()

    targets = [p for p in prospects if not p["is_example"] and not p["sent_at"]]
    print(f"{len(targets)} real, not-yet-sent tool_pitch prospects to update (of {len(prospects)} total tool_pitch rows).")

    for p in targets:
        r = requests.post(
            f"{base}/admin/outreach-queue/update-content",
            auth=auth,
            data={
                "prospect_id": p["id"],
                "subject": NEW_SUBJECT,
                "body": NEW_BODY,
                "show": p["status"],
            },
            timeout=30,
            allow_redirects=False,
        )
        if r.status_code == 303:
            print(f"{p['target_domain']} (id {p['id']}): updated")
        else:
            print(f"{p['target_domain']} (id {p['id']}): FAILED ({r.status_code}) {r.text[:200]}")


if __name__ == "__main__":
    main()
