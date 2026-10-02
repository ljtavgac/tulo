import os, requests, json
base = os.environ["BACKEND_BASE_URL"].rstrip("/")
auth = (os.environ["OUTREACH_ADMIN_USER"], os.environ["OUTREACH_ADMIN_PASSWORD"])
r = requests.get(f"{base}/admin/outreach-queue/list.json", params={"status": "all"}, auth=auth, timeout=30)
r.raise_for_status()
rows = r.json()
group_id = "566c4f3030cc4a07b023c5eec2e8a7a8"
hits = [row for row in rows if row.get("source_group_id") == group_id]
print(f"{len(hits)} row(s) in group {group_id}")
for row in sorted(hits, key=lambda r: r["id"]):
    print(json.dumps({k: row[k] for k in ("id","status","pitch_type","proposed_title","target_slug","subject")}, indent=2))
