"""Throwaway: checks contact_name on the live latte (117) and Southern
Living (122) replies, then patches both with the full email shape
(greeting, context+framing, numbered rows unchanged, closing offer,
sign-off) matching the now-fixed prompt guidance -- avoids a full
re-draft since both were already verified correct in content. Deleted
after use."""

from __future__ import annotations

import os

import requests


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=60)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, dict):
        rows = rows.get("prospects") or rows.get("items") or []
    by_id = {row["id"]: row for row in rows}

    for target_id in (117, 122):
        row = by_id.get(target_id)
        print(f"id={target_id}: contact_name={row.get('contact_name')!r} status={row.get('status')!r}")

    latte_subject = by_id[117]["subject"]
    latte_body = """\
Hi,

I'm writing in response to your HARO query on common at-home latte mistakes. Here are a few things from Tulo that might help answer your questions below:

1. What is the biggest mistake that can ruin an otherwise good homemade latte, and why does it have such a noticeable impact on the drink?
Getting the espresso-to-milk ratio and milk texture wrong is the usual culprit, and we walk through why that throws off the whole cup here: https://tulo.io/food/how-to/how-to-prepare-a-latte

2. If you could give a home barista just three rules for consistently making a coffee-shop-quality latte, what would they be?
Our step-by-step breakdown of pulling the shot, texturing milk, and combining the two in the right proportions covers this: https://tulo.io/food/how-to/how-to-prepare-a-latte

3. Are there any common latte-making shortcuts or viral coffee hacks that you would recommend avoiding? Why?
[can't produce a URL for this]

4. Do you need an expensive machine to pull a good latte?
[can't produce a URL for this]

5. If someone tells you their lattes are coming out too watery, what's your first troubleshooting technique?
Our latte prep guide addresses dialing in the shot and milk ratio, which is the first place to look: https://tulo.io/food/how-to/how-to-prepare-a-latte

6. Does the order in which you add espresso, milk, and sweeteners matter when making a latte? If so, what order do you recommend?
The sequencing is laid out step by step in our latte preparation guide: https://tulo.io/food/how-to/how-to-prepare-a-latte

7. Are some types of dairy or plant-based milk better suited for homemade lattes than others? What should shoppers look for on the label?
We compare how oat and almond milk behave differently for drinks like this here: https://tulo.io/food/comparisons/oat-milk-vs-almond-milk

8. What should properly steamed milk look and feel like before it's added to espresso? Is there a difference between simply frothing milk and properly steaming milk for a latte? What kind of texture should people aim for and is there an ideal temperature?
[URL placeholder -- pending: "How to Steam Milk for a Latte"]

9. What do you see people do wrong with store-bought espresso that makes their latte taste too bitter, burnt, sour, or overly acidic in a latte?
[URL placeholder -- pending: "Why Espresso Tastes Bitter, Sour, or Burnt"]

10. How do the grind settings on your espresso machine impact the outcome of your latte?
[URL placeholder -- pending: "How Grind Size Affects Espresso and Latte Flavor"]

11. Are there any cheap tools (less than $20) you would recommend aspiring at-home baristas invest in to help make a delicious latte?
[can't produce a URL for this]

12. How does the bean selection impact the outcome of your latte? Any recommendations for types of coffee beans or things to be wary of when buying beans from the grocery store for at-home lattes?
[URL placeholder -- pending: "Choosing Coffee Beans for Espresso and Lattes"]

Let me know if you have any questions or if there's anything else I can help clarify.

Thanks for your time,

Tulo Team"""

    sl_subject = by_id[122]["subject"]
    sl_body = """\
Hi,

I'm writing in response to your Connectively query for Southern Living. Here are a few things from Tulo that might help answer your questions below:

1. Why wooden cutting boards get dark and rough over time
[URL placeholder -- pending: "How to Care for and Restore a Wooden Cutting Board"]

2. What's the difference between filet mignon and tenderloin?
[URL placeholder -- pending: "Filet Mignon vs. Beef Tenderloin: What's the Difference?"]

3. Do coconut flakes need to be refrigerated to stay fresh?
https://tulo.io/food/ingredients/desiccated-coconut

Let me know if you have any questions or if there's anything else I can help clarify.

Thanks for your time,

Tulo Team"""

    for prospect_id, subject, body in ((117, latte_subject, latte_body), (122, sl_subject, sl_body)):
        rr = requests.post(
            f"{base}/admin/outreach-queue/update-content",
            data={"prospect_id": prospect_id, "subject": subject, "body": body, "show": "all"},
            auth=auth, timeout=30, allow_redirects=False,
        )
        print(f"patch id={prospect_id} -> status={rr.status_code}")


if __name__ == "__main__":
    main()
