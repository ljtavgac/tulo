"""Throwaway: one-shot data cleanup after deploying the rationale/
placeholder split and the visual-grouping fix.

1. Fixes id=80's source_group_id, which 404'd during the original
   backfill (78 and 79 succeeded, 80 didn't -- cause unconfirmed,
   likely a transient blip during the staging redeploy that shipped the
   endpoint a few seconds earlier).
2. Rejects id=74, the original pre-split Southern Living reply --
   superseded by 78/79/80, which cover the same three topics correctly
   split out. Kept it around only for audit; it's now just confusing
   clutter next to the new set.
3. Backfills rationale + replaces the old "Why: ..." body_preview text
   with the new clean placeholder on every already-queued
   content_opportunity row (78/79/80 for Southern Living, 83-87 for the
   latte retest) -- these predate the rationale field, so without this
   they'd keep showing the internal-reasoning text this session's fix
   was built to stop showing.

Deleted after use."""

from __future__ import annotations

import os

import requests

# proposed_title, rationale -- copied verbatim from the two prior
# diagnostic runs that created these rows (check-77-80, check-82-87).
CONTENT_OPPORTUNITIES = {
    78: (
        "Why Wooden Cutting Boards Turn Dark and Rough (and How to Restore Them)",
        "This is a recurring, evergreen kitchen question about wood absorbing moisture, oils going rancid, "
        "and knife scarring that Tulo doesn't currently have a dedicated care/restoration page for.",
    ),
    79: (
        "Filet Mignon vs. Tenderloin: What's the Difference?",
        "This is a common cut-of-beef confusion (filet mignon is a specific portion of the whole beef "
        "tenderloin) that fits Tulo's comparison format and doesn't yet exist on the site.",
    ),
    80: (
        "Coconut Flakes: Storage, Shelf Life, and Do They Need Refrigeration?",
        "Tulo has ingredient hubs for related products like desiccated coconut but nothing specifically "
        "addressing sweetened/shredded coconut flake storage and refrigeration, a common pantry question.",
    ),
    83: (
        "Steaming Milk for Lattes: Texture and Temperature Guide",
        "Home baristas regularly confuse frothing with proper steaming, so a page covering ideal microfoam "
        "texture and target temperature would directly answer a common, evergreen question.",
    ),
    84: (
        "Why Does Espresso Taste Bitter or Burnt? Troubleshooting Guide",
        "This is a common, recurring espresso complaint that a diagnostic page on over-extraction, stale "
        "grounds, and brew mistakes could permanently address.",
    ),
    85: (
        "How Grind Size Affects Espresso and Latte Flavor",
        "Grind size is one of the most impactful and least understood variables in home espresso brewing, "
        "making it a solid standalone technique topic.",
    ),
    86: (
        "Affordable Home Barista Tools Under $20",
        "Budget-conscious home coffee drinkers frequently look for inexpensive tools that improve espresso "
        "and latte results, making this a useful evergreen roundup.",
    ),
    87: (
        "How to Choose Coffee Beans for Espresso and Lattes",
        "Bean freshness and roast level meaningfully affect latte quality, and there's currently no "
        "ingredient hub guiding shoppers through grocery-store bean choices.",
    ),
}


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    by_id = {row["id"]: row for row in rows}

    # 1. Fix id=80's missing source_group_id, matching 78/79's.
    group_id = by_id.get(78, {}).get("source_group_id")
    if group_id:
        rr = requests.get(
            f"{base}/admin/outreach-queue/update-source-group",
            params={"prospect_id": 80, "source_group_id": group_id, "show": "all"},
            auth=auth, timeout=30, allow_redirects=False,
        )
        print(f"fix id=80 source_group_id -> {group_id!r}: status={rr.status_code}")
    else:
        print("id=78 has no source_group_id -- skipping id=80 fix, check manually")

    # 2. Reject id=74 if not already.
    row74 = by_id.get(74)
    if row74 and row74.get("status") != "rejected":
        rr = requests.get(
            f"{base}/admin/outreach-queue/decide",
            params={"prospect_id": 74, "status": "rejected", "show": "all"},
            auth=auth, timeout=30, allow_redirects=False,
        )
        print(f"reject id=74 (status was {row74.get('status')!r}): status={rr.status_code}")
    else:
        print(f"id=74: {'already rejected' if row74 else 'not found'}, skipping")

    # 3. Backfill rationale + clean placeholder body_preview.
    for prospect_id, (title, rationale) in CONTENT_OPPORTUNITIES.items():
        row = by_id.get(prospect_id)
        if not row:
            print(f"id={prospect_id}: not found, skipping")
            continue
        placeholder = f'[Placeholder -- once "{title}" is created, reviewed, and live, this will link to it here.]'
        rr1 = requests.get(
            f"{base}/admin/outreach-queue/update-rationale",
            params={"prospect_id": prospect_id, "rationale": rationale, "show": "all"},
            auth=auth, timeout=30, allow_redirects=False,
        )
        rr2 = requests.post(
            f"{base}/admin/outreach-queue/update-content",
            data={"prospect_id": prospect_id, "subject": row["subject"], "body": placeholder, "show": "all"},
            auth=auth, timeout=30, allow_redirects=False,
        )
        print(f"id={prospect_id}: rationale status={rr1.status_code}, body_preview status={rr2.status_code}")


if __name__ == "__main__":
    main()
