import os, requests, json

base = os.environ["BACKEND_BASE_URL"].rstrip("/")
token = os.environ["ADMIN_TASK_TOKEN"]

def get(path, **params):
    params["token"] = token
    r = requests.get(f"{base}{path}", params=params, timeout=30, allow_redirects=False)
    return r

print("--- batch 25 current state ---")
r = get("/admin/review-queue/data", batch="25", show="all")
print(r.status_code, json.dumps(r.json(), indent=2) if r.status_code == 200 else r.text[:500])

print("\n--- approve-remaining batch 25 ---")
r = get("/admin/review-queue/approve-remaining", batch="25")
print(r.status_code)

print("\n--- batch 25 state after approve-remaining ---")
r = get("/admin/review-queue/data", batch="25", show="all")
print(r.status_code, json.dumps(r.json(), indent=2) if r.status_code == 200 else r.text[:500])

print("\n--- approve-for-prod batch 25 (should cascade to batch 26) ---")
r = get("/admin/review-queue/approve-for-prod", batch="25")
print(r.status_code, r.text[:1000] if r.status_code != 303 else "redirect (success)")

print("\n--- approve-for-prod batch 26 (confirm/retry) ---")
r = get("/admin/review-queue/approve-for-prod", batch="26")
print(r.status_code, r.text[:1000] if r.status_code != 303 else "redirect (success)")
