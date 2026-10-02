import os, requests, json
base = os.environ["BACKEND_BASE_URL"].rstrip("/")
auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=30)
r.raise_for_status()
rows = r.json()
hits = [row for row in rows if "chicken tender" in (row.get("source_query") or "").lower()
        or "chicken tender" in (row.get("subject") or "").lower()
        or "chicken tender" in (row.get("body_preview") or "").lower()
        or "chicken tender" in (row.get("proposed_title") or "").lower()]
print(f"{len(hits)} matching row(s)")
for row in hits:
    print(json.dumps(row, indent=2))
