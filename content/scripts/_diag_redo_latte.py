"""Throwaway: re-ingests the real daily-meal/latte query (id=72's original
source_query, verbatim from HARO) through the now-fixed pipeline
(max_tokens=8192, many-sub-question opening-paragraph+bold format,
content_opportunity extended to manual-submission, anti-AI-tell style)
to produce a clean, non-test-tagged replacement for id=72. Deleted after
use."""

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


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    payload = {
        "envelope": {"to": "9fa2d6374492693ffdda@cloudmailin.net", "from": "noreply@helpareporter.com"},
        "headers": {"subject": "HARO latte-mistakes query"},
        "plain": LATTE_QUERY,
        "html": "",
    }
    r = requests.post(f"{base}/admin/outreach-queue/ingest-email", auth=auth, json=payload, timeout=180)
    print(f"status={r.status_code} body={r.text}")


if __name__ == "__main__":
    main()
