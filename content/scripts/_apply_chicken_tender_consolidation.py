import os, requests, json, time

base = os.environ["BACKEND_BASE_URL"].rstrip("/")
auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
GROUP_ID = "566c4f3030cc4a07b023c5eec2e8a7a8"
CONTACT_NAME = "Michael Serrur"
CONTACT_EMAIL = "reply+748ba2de-8d72-4a19-9f1f-66734f325647@helpareporter.com"
DOMAIN = "Food Republic"

def wait_for_new_field_support(timeout=180):
    """Polls the staging backend until POST /admin/outreach-queue/create
    accepts status=article_pending_review (new Render deploy picked up),
    rather than failing on the very first try while the push is still
    deploying."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.post(
            f"{base}/admin/outreach-queue/create",
            auth=auth,
            json={"pitch_type": "haro_reply", "target_domain": "x", "subject": "x", "body_preview": "x",
                  "status": "article_pending_review"},
            timeout=30,
        )
        if r.status_code == 400 and "target_slug and proposed_title are required" in r.text:
            print("New field support is live.")
            return
        print(f"  not ready yet (status {r.status_code}): {r.text[:200]}")
        time.sleep(10)
    raise RuntimeError("Timed out waiting for new deploy")

def reject(prospect_id):
    r = requests.get(f"{base}/admin/outreach-queue/decide",
                      params={"prospect_id": prospect_id, "status": "rejected", "show": "all"},
                      auth=auth, timeout=30, allow_redirects=False)
    print(f"reject #{prospect_id}: {r.status_code}")

def create_article_pending_review(proposed_title, target_slug, rationale):
    r = requests.post(
        f"{base}/admin/outreach-queue/create",
        auth=auth,
        json={
            "pitch_type": "haro_reply",
            "target_domain": DOMAIN,
            "contact_name": CONTACT_NAME,
            "contact_email": CONTACT_EMAIL,
            "subject": f"[Article opportunity] {proposed_title}",
            "body_preview": "(no draft yet -- nothing to preview until this article is created)",
            "status": "article_pending_review",
            "target_slug": target_slug,
            "proposed_title": proposed_title,
            "proposed_template_type": "howto_technique",
            "rationale": rationale,
            "source_group_id": GROUP_ID,
        },
        timeout=30,
    )
    r.raise_for_status()
    print(f"created: {r.json()}")

def update_429_body():
    new_body = (
        "Hi Michael,\n\n"
        "I saw your Food Republic call for chicken tender advice and wanted to send over a few things "
        "from what we've put together at Tulo that touch on the questions below. We ended up writing two "
        "broader guides instead of several narrow ones, so a couple of these point to the same piece.\n\n"
        "1. What are some common mistakes home cooks make when breading chicken tenders (burning, undercooking, wrong breading, etc.)?\n"
        "[URL placeholder -- pending: \"Common Chicken Tender Breading Mistakes and How to Avoid Them\"]\n\n"
        "2. How do you avoid overcooking?\n"
        "Our cook time and temperature guide lays out how long tenders need at various methods and the safe internal temperature to pull them at so they don't dry out: https://tulo.io/food/tools/time-temperature-guide\n\n"
        "3. What's the best way to properly season your tenders?\n"
        "[URL placeholder -- pending: \"Common Chicken Tender Breading Mistakes and How to Avoid Them\" -- now covers seasoning too]\n\n"
        "4. Should you refrigerate chicken before breading, after breading, or not at all? Do chicken tenders need to be at room temperature?\n"
        "[URL placeholder -- pending: \"How to Prep Chicken Tenders for Flavor and Tenderness\"]\n\n"
        "5. What are the best and worst cooking methods -- shallow-frying in cast iron, baking in an air fryer, or a conventional oven?\n"
        "Our air fryer chicken tenders recipe walks through timing and technique for that method specifically: https://tulo.io/food/recipes/air-fryer-chicken-tenders -- and [URL placeholder -- pending: \"Chicken Tender Cooking Methods, Doneness, and How to Fix a Bad Batch\"] compares it against shallow-frying and the oven.\n\n"
        "6. Should you tenderize your chicken? What are some ways to make the meat more succulent and juicy?\n"
        "[URL placeholder -- pending: \"How to Prep Chicken Tenders for Flavor and Tenderness\"]\n\n"
        "7. How should you cut your chicken for the crispiest, most flavorful tenders? Should you only use chicken breast or can you use thigh meat?\n"
        "[URL placeholder -- pending: \"How to Prep Chicken Tenders for Flavor and Tenderness\"]\n\n"
        "8. Do chicken tenders need to rest before eating?\n"
        "[URL placeholder -- pending: \"Chicken Tender Cooking Methods, Doneness, and How to Fix a Bad Batch\"]\n\n"
        "9. Should you use any sort of marinade before breading and cooking?\n"
        "[URL placeholder -- pending: \"How to Prep Chicken Tenders for Flavor and Tenderness\"]\n\n"
        "10. What are some ways to save your tenders if they're overcooked, undercooked, bland, burnt, chewy, etc.?\n"
        "[URL placeholder -- pending: \"Chicken Tender Cooking Methods, Doneness, and How to Fix a Bad Batch\"]\n\n"
        "Let me know if you have any questions or if there's anything else I can help clarify.\n\n"
        "Thanks for your time,\n"
        "Tulo Team"
    )
    r = requests.post(
        f"{base}/admin/outreach-queue/update-content",
        auth=auth,
        data={
            "prospect_id": 429,
            "subject": "A few resources for your chicken tenders piece",
            "body": new_body,
            "show": "all",
        },
        timeout=30,
        allow_redirects=False,
    )
    print(f"update #429 body: {r.status_code}")

def main():
    wait_for_new_field_support()

    for pid in (431, 432, 433):
        reject(pid)

    create_article_pending_review(
        "How to Prep Chicken Tenders for Flavor and Tenderness",
        "how-to-prep-chicken-tenders-for-flavor-and-tenderness",
        "Consolidates the reporter's cut-selection, tenderizing, marinating, and "
        "pre-breading refrigeration questions (originally prospects #431/#432/#433) "
        "into one broader prep-phase article instead of three thin ones.",
    )
    create_article_pending_review(
        "Chicken Tender Cooking Methods, Doneness, and How to Fix a Bad Batch",
        "chicken-tender-cooking-methods-and-fixes",
        "Answers the reporter's cooking-method comparison, resting, and "
        "fixing-a-bad-batch questions, none of which had a planned article at all "
        "under the original 4-article split.",
    )

    update_429_body()

if __name__ == "__main__":
    main()
