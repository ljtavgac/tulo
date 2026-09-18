"""Throwaway: re-runs the exact real Featured.com and Connectively digests
(as originally forwarded/pasted) through the now-fixed ingest-email
pipeline (JSON-parse retry fix), to see how many drafted opportunities
-- including manual-submission ("copy/paste") ones -- it now produces.
Deleted after use."""

from __future__ import annotations

import os

import requests

FEATURED_DIGEST = """\
None selected

Skip to content
Using tulo.io Mail with screen readers

2 of 21
All-in-One - Looking for journalist requests...: 4 new opportunities - Sep 18
External
Inbox


Featured <noreply@featured.com>
4:16 PM (14 minutes ago)
to me

Featured
4 new
All-in-One - Looking for journalist requests in the recipes, food, drink...
All-in-OneFri, Sep 18, 1:16 PM
Workflow summary: Every day at 5:00 AM ET, find opportunities covering "Looking for journalist requests in the recipes, food, drink space." and send to me via email.


Canvas8
Journalist Requests
I'm writing a report looking at how climate change is reshaping British food habits, from the rise of picky eats and cold food for hotter temperatures, a desire for better hydration, to more awareness of which crops are impacted by the heat and how brands are responding. Interested in how brands are innovating to make cold food exciting, who is getting functional hydration right, and what brands can do to show consumers they care with sustainable meals. Potential Topics of... View full brief ->

Match reasoning

Seeks food and beverage experts on climate-driven eating shifts, cold food innovation, and functional hydration -- directly aligned with food and drink reporting

Oct 5, 2:00 PM EDT

View Details
F
Food Republic
Monitor HARO
I'm looking for chefs, recipe editors, food writers, and culinary experts who can provide practical insights on a range of different food topics. Subjects may include everything from food storage tips to preparation techniques to common kitchen pitfalls. The information should be accessible to the average home cook. No specific brand or product endorsements unless directly related to the article. When you respond, please share your current position and area of expertise.

Match reasoning

Requests chefs, recipe editors, and culinary experts for practical cooking and food preparation guidance -- core recipes and food journalism focus

Dec 31, 12:00 AM EST

View Details

Seen Through A Glass
Find Podcasts
Latest: Aug 27, 2026 - 96 episodes - en

Seen Through A Glass is mostly about drinks and food in central Pennsylvania, hosted by long-time drinks writer Lew Bryson. There are shows about particular products -- maple syrup, soft-serve ice ...

Match reasoning

Established drinks and food podcast covering regional products like maple syrup and soft-serve -- matches drinks and food content distribution

View Details

ELLE Gourmet Taste Talks
Find Podcasts
Latest: Jun 25, 2026 - 2 episodes - en

ELLE Gourmet takes you behind the scenes with host Catherine Lefebvre for a fresh look at the world of cooking, culinary travel, and food culture - one conversation at a time. From acclaimed chefs ...

Match reasoning

ELLE Gourmet explores cooking, culinary travel, and food culture through chef interviews -- aligns with food and culinary storytelling

jhowe@ellispark.co

View Details
View workflow run
You're receiving this because your workflow is set to email results.
"""

CONNECTIVELY_DIGEST = """\
None selected

Skip to content
Using tulo.io Mail with screen readers
Enable desktop notifications for tulo.io Mail.
   OK  No thanks

2 of 320
Connectively Alerts for Sep 18th, 2026
Inbox

Connectively <noreply@connectively.us> Unsubscribe
4:22 PM (9 minutes ago)
to ljtavgac

Connectively logo

Q&A Alerts
Questions matching your keyword and source alerts.

food
2 alerts

Brands are sought for a VIP reception gifting experience at a 2026 summit in Milwaukee. We're seeking fun, useful, elevated products in travel, beauty, wellness, lifestyle, tech, food, self-care, fashion and accessories, and culturally inspired goods. Black-owned and diverse-owned brands are especially encouraged to submit. Think "I'm glad I got this!" rather than typical swag. Desired items include: Travel accessories and luggage essentials Luggage tags, bag charms, and passport accessories Travel-size beauty and skincare Haircare products Wellness and self-care products Candles and home fragrance Gourmet snacks, chocolates, and sweets Coffee, tea, and non-alcoholic beverages Tech accessories and travel gadgets Portable chargers and charging accessories Jewelry and fashion accessories Sunglasses Travel journals and elevated stationery Sleep masks and comfort items Mini fragrances or perfume Gift cards and experience certificates Milwaukee- or Wisconsin-made products Culturally inspired products Other unique lifestyle or travel items Selected items will be gifted to VIP attendees during an exclusive reception. Please submit your brand name, website or social media, product offered, retail value, confirmation that 100 units are available, and shipping details. In-kind product contributions only. Submission does not guarantee inclusion.
Favicon for Black Travel Summit	Black Travel Summit
Answer by Sep 30th
I'm seeking physical products for upcoming 2026 Christmas and holiday gift guide coverage on a lifestyle website for busy women and families. For this round of holiday coverage, I'm particularly interested in substantial, useful products that could serve as a main Christmas gift, especially products for the kitchen, home, garden, and practical everyday living. Products of particular interest include: * Bread machines, dehydrators, and food-preservation equipment * Coffee makers, espresso machines, grinders, and other coffee equipment * Air fryers, multicookers, and other countertop kitchen appliances * Food processors, mixers, and specialty food-preparation appliances * Higher-quality cookware and useful kitchen equipment * Vacuums, steam cleaners, and substantial home-cleaning equipment * Smart-home products and practical technology * Home organization equipment and systems * Gardening tools, equipment, and indoor growing products * Solar-powered products and portable power products * Useful outdoor and preparedness-related equipment * DIY and home-maintenance tools or equipment * Other substantial home and kitchen products that would make useful Christmas gifts I am primarily seeking substantial, gift-worthy products rather than stocking stuffers or small novelty items. Please do not submit samples, promotional items, inexpensive novelty products, tea, supplements, sleep aids, ordinary bath/body products, books, ebooks, apps, digital products, subscriptions, or services. Please include the product name, brief description, retail price, product/company link, and confirmation that a full-size physical product is available for review. I review pitches before accepting products. If I agree to receive your product, it will be included in appropriate 2026 holiday gift guide coverage after it is received. Products provided for coverage will not be returned. Holiday coverage may include one or more themed gift guides depending on the products selected.
Favicon for Google	Google
Answer by Nov 15th
View All Questions
Opportunity Alerts
Opportunities matching your keyword.

food
3 alerts

CHRISTMAS CONTENT CALL OUT -- Looking to feature food, drink, restaurants & CHRISTMAS! The OG Essex foodie page! 14K following -> showcasing all things FOOD -> https://t.co/5f8QioK0wi Email: essexfoodies@gmail.com #journorequest #prrequest #bloggerrequest
Freelance

External link View by Sep 21st
I'm working on the following pieces for Southern Living and looking for pastry chefs, bakers, chefs, food safety experts, food scientists, and a woodworker/cutting-board maker based in or from the south to weigh in: Why Wooden Cutting Boards Get Dark And Rough Over Time, What's The Difference Between Filet Mignon And Tenderloin? Chefs Explain, Do Coconut Flakes Need To Be Refrigerated To Stay Fresh? Please do NOT send commentary before emailing me first so I can send my questions. Thanks!
southern living

External link View by Sep 21st
We're looking for a brief video reply from an expert on what a Wendy's franchisee bankruptcy could signal for restaurant operators, lenders, and the broader fast-food franchise model. https://www.newsnationnow.com/business/wendys-franchisee-bankruptcy/
NewsNation

External link View by Sep 18th
drink
1 alerts

I'm looking for fall-flavor themed cocktails and Halloween cocktails as well as creative lobster dishes. I'm also sourcing for National Coffee Day (this could be coffee-centric beverages, cocktails, OR dishes), and National Dumpling Day! To pitch, please include: Name of drink/dish, Restaurant/bar where it can be ordered (as well as city, state, URL), description, quote from chef/bartender about dish (and name and title of person being quoted), and LINK to image, with an identifying file name, and any appropriate photo credits included.
forbes

External link View by Sep 21st
View New Opportunities
Bylined Article Alerts
Requests for bylined article pitches matching your keyword and source alerts.

None of the alerts you're subscribed match new bylined article requests on Connectively.

View All Requests
You can edit these alerts or unsubscribe from all alerts to stop these emails.
"""


def ingest(base: str, auth: tuple[str, str], sender: str, subject: str, digest: str) -> None:
    payload = {
        "envelope": {"to": "9fa2d6374492693ffdda@cloudmailin.net", "from": sender},
        "headers": {"subject": subject},
        "plain": digest,
        "html": "",
    }
    r = requests.post(f"{base}/admin/outreach-queue/ingest-email", auth=auth, json=payload, timeout=180)
    print(f"{sender}: status={r.status_code} body={r.text}")


def main() -> None:
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
    ingest(base, auth, "noreply@featured.com", "All-in-One - Looking for journalist requests...: 4 new opportunities", FEATURED_DIGEST)
    ingest(base, auth, "noreply@connectively.us", "Connectively Alerts for Sep 18th, 2026", CONNECTIVELY_DIGEST)


if __name__ == "__main__":
    main()
