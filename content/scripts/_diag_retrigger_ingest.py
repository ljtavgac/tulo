"""Throwaway: re-POSTs the exact Featured.com and Connectively digests the
user already forwarded (pasted into chat, reconstructed here as plain
text) to /admin/outreach-queue/ingest-email, in CloudMailin's own JSON
shape, to see whether the "zero drafted" result from the real forward is
reproducible or whether a second pass finds something. Deleted after use.

Usage:
    BACKEND_BASE_URL=https://your-backend \
    OUTREACH_ADMIN_USER=... OUTREACH_ADMIN_PASSWORD=... \
    python3 content/scripts/_diag_retrigger_ingest.py
"""

from __future__ import annotations

import os

import requests

FEATURED_DIGEST = """\
Featured
All-in-One - Looking for journalist requests in the recipes, food, drink...
Workflow summary: Every day at 5:00 AM ET, find opportunities covering "Looking for journalist requests in the recipes, food, drink space." and send to me via email.

Canvas8
Journalist Requests
I'm writing a report looking at how climate change is reshaping British food habits, from the rise of picky eats and cold food for hotter temperatures, a desire for better hydration, to more awareness of which crops are impacted by the heat and how brands are responding. Interested in how brands are innovating to make cold food exciting, who is getting functional hydration right, and what brands can do to show consumers they care with sustainable meals. Potential Topics of...
Match reasoning: Seeks food and beverage experts on climate-driven eating shifts, cold food innovation, and functional hydration -- directly aligned with food and drink reporting
Deadline: Oct 5, 2:00 PM EDT
(No reply email in text -- respond via Featured.com platform)

Food Republic
Monitor HARO
I'm looking for chefs, recipe editors, food writers, and culinary experts who can provide practical insights on a range of different food topics. Subjects may include everything from food storage tips to preparation techniques to common kitchen pitfalls. The information should be accessible to the average home cook. No specific brand or product endorsements unless directly related to the article. When you respond, please share your current position and area of expertise.
Match reasoning: Requests chefs, recipe editors, and culinary experts for practical cooking and food preparation guidance -- core recipes and food journalism focus
Deadline: Dec 31, 12:00 AM EST
(No reply email in text -- respond via Featured.com platform)

Seen Through A Glass
Find Podcasts
Seen Through A Glass is mostly about drinks and food in central Pennsylvania, hosted by long-time drinks writer Lew Bryson. There are shows about particular products -- maple syrup, soft-serve ice cream...
Match reasoning: Established drinks and food podcast covering regional products like maple syrup and soft-serve -- matches drinks and food content distribution
(No reply email in text -- respond via Featured.com platform)

ELLE Gourmet Taste Talks
Find Podcasts
ELLE Gourmet takes you behind the scenes with host Catherine Lefebvre for a fresh look at the world of cooking, culinary travel, and food culture -- one conversation at a time. From acclaimed chefs...
Match reasoning: ELLE Gourmet explores cooking, culinary travel, and food culture through chef interviews -- aligns with food and culinary storytelling
Email: jhowe@ellispark.co
"""

CONNECTIVELY_DIGEST = """\
Connectively Alerts for Sep 18th, 2026

Q&A Alerts -- Questions matching your keyword and source alerts.

[food, 2 alerts]

Black Travel Summit: Brands are sought for a VIP reception gifting experience at a 2026 summit in Milwaukee. We're seeking fun, useful, elevated products in travel, beauty, wellness, lifestyle, tech, food, self-care, fashion and accessories, and culturally inspired goods. Please submit your brand name, website or social media, product offered, retail value, confirmation that 100 units are available, and shipping details. In-kind product contributions only. Submission does not guarantee inclusion.
Answer by Sep 30th (respond via Connectively platform, no reply email in text)

Google: I'm seeking physical products for upcoming 2026 Christmas and holiday gift guide coverage on a lifestyle website for busy women and families. Particularly interested in substantial, useful products for the kitchen, home, garden, and practical everyday living -- bread machines, dehydrators, food-preservation equipment, coffee makers, espresso machines, air fryers, multicookers, food processors, mixers, cookware, vacuums, smart-home products, gardening tools, solar-powered products, DIY tools. Please do not submit samples, promotional items, inexpensive novelty products, tea, supplements, sleep aids, ordinary bath/body products, books, ebooks, apps, digital products, subscriptions, or services. Please include the product name, brief description, retail price, product/company link, and confirmation that a full-size physical product is available for review.
Answer by Nov 15th (respond via Connectively platform, no reply email in text)

Opportunity Alerts -- Opportunities matching your keyword.

[food, 3 alerts]

Essex Foodies (Freelance): CHRISTMAS CONTENT CALL OUT - Looking to feature food, drink, restaurants & CHRISTMAS! The OG Essex foodie page! 14K following, showcasing all things FOOD. https://t.co/5f8QioK0wi Email: essexfoodies@gmail.com #journorequest #prrequest #bloggerrequest
View by Sep 21st

Southern Living: I'm working on the following pieces for Southern Living and looking for pastry chefs, bakers, chefs, food safety experts, food scientists, and a woodworker/cutting-board maker based in or from the south to weigh in: Why Wooden Cutting Boards Get Dark And Rough Over Time, What's The Difference Between Filet Mignon And Tenderloin? Chefs Explain, Do Coconut Flakes Need To Be Refrigerated To Stay Fresh? Please do NOT send commentary before emailing me first so I can send my questions.
View by Sep 21st (no reply email in text -- must email the reporter first to request questions)

NewsNation: We're looking for a brief video reply from an expert on what a Wendy's franchisee bankruptcy could signal for restaurant operators, lenders, and the broader fast-food franchise model. https://www.newsnationnow.com/business/wendys-franchisee-bankruptcy/
View by Sep 18th (no reply email in text)

[drink, 1 alerts]

Forbes: I'm looking for fall-flavor themed cocktails and Halloween cocktails as well as creative lobster dishes. I'm also sourcing for National Coffee Day (this could be coffee-centric beverages, cocktails, OR dishes), and National Dumpling Day! To pitch, please include: Name of drink/dish, Restaurant/bar where it can be ordered (as well as city, state, URL), description, quote from chef/bartender about dish (and name and title of person being quoted), and LINK to image, with an identifying file name, and any appropriate photo credits included.
View by Sep 21st (no reply email in text)

Bylined Article Alerts -- None of the alerts you're subscribed match new bylined article requests on Connectively.
"""


def _post(base: str, auth: tuple[str, str], from_addr: str, subject: str, plain: str) -> None:
    payload = {
        "envelope": {"to": "9fa2d6374492693ffdda@cloudmailin.net", "from": from_addr},
        "headers": {"subject": subject},
        "plain": plain,
        "html": "",
    }
    r = requests.post(f"{base}/admin/outreach-queue/ingest-email", auth=auth, json=payload, timeout=120)
    print(f"{subject!r}: status={r.status_code} body={r.text[:300]}")


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])

    _post(base, auth, "noreply@featured.com", "[RETEST] All-in-One - 4 new opportunities", FEATURED_DIGEST)
    _post(base, auth, "noreply@connectively.us", "[RETEST] Connectively Alerts for Sep 18th, 2026", CONNECTIVELY_DIGEST)


if __name__ == "__main__":
    main()
