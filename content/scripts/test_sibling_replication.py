"""One-off: verifies sibling replication actually works now that
SIBLING_BACKEND_BASE_URL/SIBLING_ADMIN_TASK_TOKEN are configured on both
Render services. Since _replicate_image_fields_to_sibling() is called
synchronously inline (not backgrounded), the sibling write has already
happened by the time the primary request returns -- no extra wait needed.

Picks one low-traffic slug (aquavit), reads its current real values from
STAGING, writes a temporary marker appended to the photographer field via
staging's own /admin/set-image-fields (triggering replication), then
immediately reads PROD to confirm the marker arrived there too. Finally
reverts BOTH sides back to the exact original values (also via staging,
also replicating), leaving no trace either way.

This never touches image_url, only image_attribution.photographer, and
only for a few seconds -- chosen to be detectable but as low-impact as
possible on a live page.
"""

import os
import sys

import requests

PROD_BASE = os.environ["PROD_BACKEND_BASE_URL"].rstrip("/")
PROD_TOKEN = os.environ["PROD_ADMIN_TASK_TOKEN"]
STAGING_BASE = os.environ["STAGING_BACKEND_BASE_URL"].rstrip("/")
STAGING_TOKEN = os.environ["STAGING_ADMIN_TASK_TOKEN"]

SLUG = "aquavit"
MARKER = " [replication-test-2026-09-20]"


def export(base, token, slug):
    r = requests.get(f"{base}/admin/export-images", params={"token": token, "slugs": slug}, timeout=30)
    r.raise_for_status()
    return r.json()[slug]


def set_fields(base, token, slug, image_url, attribution):
    r = requests.post(
        f"{base}/admin/set-image-fields",
        params={"token": token, "slug": slug},
        json={"image_url": image_url, "image_attribution": attribution},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


original = export(STAGING_BASE, STAGING_TOKEN, SLUG)
print(f"Original staging value for {SLUG}: {original}")

test_attribution = dict(original["image_attribution"] or {})
test_attribution["photographer"] = (test_attribution.get("photographer") or "") + MARKER

print("\nWriting test marker to staging (should replicate to prod synchronously)...")
set_fields(STAGING_BASE, STAGING_TOKEN, SLUG, original["image_url"], test_attribution)

prod_after_test = export(PROD_BASE, PROD_TOKEN, SLUG)
print(f"Prod value immediately after: {prod_after_test}")

replicated = MARKER in (prod_after_test["image_attribution"] or {}).get("photographer", "")

print("\nReverting both sides to the original value...")
set_fields(STAGING_BASE, STAGING_TOKEN, SLUG, original["image_url"], original["image_attribution"])

staging_final = export(STAGING_BASE, STAGING_TOKEN, SLUG)
prod_final = export(PROD_BASE, PROD_TOKEN, SLUG)
print(f"Staging final: {staging_final}")
print(f"Prod final:    {prod_final}")

clean = staging_final == original and prod_final["image_attribution"] == original["image_attribution"] and prod_final["image_url"] == original["image_url"]

print()
if replicated:
    print("RESULT: replication WORKED -- the marker written to staging appeared on prod.")
else:
    print("RESULT: replication DID NOT fire -- prod never received the marker. Check SIBLING_* env vars and confirm both services actually redeployed.")

if not clean:
    print("::error::Revert did not fully restore original state -- manual check needed.")
    sys.exit(1)
print("Both sides confirmed back to their original, correct value.")
sys.exit(0 if replicated else 1)
