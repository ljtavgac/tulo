"""Throwaway: full clean-slate re-test after unifying the bundling and
numbered-sub-question reply paths.

Rejects every currently-active row tied to the two test digests
(latte: 83, 84, 87 orphaned from a dead group, plus 88-93 the last
round's group; Southern Living: 78, 79, 80, which never got a linked
reply at all), then re-ingests both queries fresh against the fixed
prompt and prints the results: the reply's body (to check numbered-row
format, no bold, and presence even with zero real URLs for Southern
Living) plus every linked content_opportunity's title.

Deleted after use."""

from __future__ import annotations

import os

import requests

LATTE_QUERY = """\
I am seeking coffee experts to provide insights for an article on the common mistakes people make when crafting their own at-home latte and tips for how to make them better. The questions guiding my article are listed below:
1. What is the biggest mistake that can ruin an otherwise good homemade latte, and why does it have such a noticeable impact on the drink?
2. If you could give a home barista just three rules for consistently making a coffee-shop-quality latte, what would they be?
3. Are there any common latte-making shortcuts or viral coffee hacks that you would recommend avoiding? Why?
4. Do you need an expensive machine to pull a good latte?
5. If someone tells you their lattes are coming out too watery, what's your first troubleshooting technique?
6. Does the order in which you add espresso, milk, and sweeteners matter when making a latte? If so, what order do you recommend?
7. Are some types of dairy or plant-based milk better suited for homemade lattes than others? What should shoppers look for on the label?
8. What should properly steamed milk look and feel like before it's added to espresso? Is there a difference between simply frothing milk and properly steaming milk for a latte? What kind of texture should people aim for and is there an ideal temperature?
9. What do you see people do wrong with store-bought espresso that makes their latte taste too bitter, burnt, sour, or overly acidic in a latte?
10. How do the grind settings on your espresso machine impact the outcome of your latte?
11. Are there any cheap tools (less than $20) you would recommend aspiring at-home baristas invest in to help make a delicious latte?
12. How does the bean selection impact the outcome of your latte? Any recommendations for types of coffee beans or things to be wary of when buying beans from the grocery store for at-home lattes?
"""

SOUTHERN_LIVING_QUERY = """\
I'm working on the following pieces for Southern Living and looking for pastry chefs, bakers, chefs, food safety experts, food scientists, and a woodworker/cutting-board maker based in or from the south to weigh in: Why Wooden Cutting Boards Get Dark And Rough Over Time, What's The Difference Between Filet Mignon And Tenderloin? Chefs Explain, Do Coconut Flakes Need To Be Refrigerated To Stay Fresh? Please do NOT send commentary before emailing me first so I can send my questions. Thanks!
"""


def reject(base: str, auth: tuple[str, str], prospect_id: int) -> None:
    r = requests.get(
        f"{base}/admin/outreach-queue/decide",
        params={"prospect_id": prospect_id, "status": "rejected", "show": "all"},
        auth=auth, timeout=30, allow_redirects=False,
    )
    print(f"reject id={prospect_id} -> status={r.status_code}")


def ingest(base: str, auth: tuple[str, str], sender: str, subject: str, text: str) -> list[int]:
    payload = {
        "envelope": {"to": "9fa2d6374492693ffdda@cloudmailin.net", "from": sender},
        "headers": {"subject": subject},
        "plain": text,
        "html": "",
    }
    r = requests.post(f"{base}/admin/outreach-queue/ingest-email", auth=auth, json=payload, timeout=180)
    print(f"ingest ({sender}): status={r.status_code} body={r.text}")
    data = r.json()
    return data.get("created_prospect_ids") or ([data["created_prospect_id"]] if "created_prospect_id" in data else [])


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    for old_id in (83, 84, 87, 88, 89, 90, 91, 92, 93, 78, 79, 80):
        reject(base, auth, old_id)

    latte_ids = ingest(base, auth, "noreply@helpareporter.com", "HARO latte-mistakes query", LATTE_QUERY)
    sl_ids = ingest(base, auth, "noreply@connectively.us", "Southern Living query", SOUTHERN_LIVING_QUERY)

    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    by_id = {row["id"]: row for row in rows}

    for label, ids in (("LATTE", latte_ids), ("SOUTHERN LIVING", sl_ids)):
        print(f"\n\n========== {label} ({len(ids)} items) ==========")
        for pid in sorted(ids):
            row = by_id.get(pid)
            if not row:
                print(f"id={pid}: not found")
                continue
            print(f"\n--- id={pid} type={'reply' if not row.get('proposed_template_type') else 'content_opportunity'} group={row.get('source_group_id')} ---")
            print(f"title/subject: {row.get('proposed_title') or row.get('subject')!r}")
            if not row.get("proposed_template_type"):
                print(f"BODY:\n{row.get('body_preview')}")


if __name__ == "__main__":
    main()
