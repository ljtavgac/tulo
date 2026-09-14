"""One-off full-site audit: unlike bake_images_from_staging.py (which bakes
a hand-picked list of slugs -- meant for a single batch, or a specific known
fix), this discovers EVERY single-hero-image page live on staging via the
public GET /pages?template_type=... listing (no admin token needed -- the
same endpoint the site itself uses for section index pages) and bakes
whichever ones don't already match what's committed in seed_templates.py.

Real gap this closes (2026-09-14): image_url only ever lives in the runtime
database (see bake_images_from_staging.py's own docstring). Two separate
things could leave a slug's baked data stale or missing entirely, with no
way to notice short of spotting it live:
  1. A batch merged to prod before the bake step existed / before it was
     wired into daily_batch.py (see bake_batch_images there) -- its photos
     were never baked at all.
  2. A manual fix made via /admin/review-queue (a flagged re-fetch, or a
     pasted override-image URL) writes straight to staging's database and
     was never guaranteed to get baked afterward -- it could sit on staging
     indefinitely with zero path to production, however long ago it happened.

This audits everything at once instead of relying on remembering which
slugs were ever touched. Safe to re-run: bake() always replaces a slug's
baked data with staging's current live state, so a slug that's already
correct is a no-op rewrite (same bytes, no real diff), and running this
again later just picks up whatever's changed on staging since.

Usage:
    python3 content/scripts/audit_and_bake_all_images.py \\
        --base-url https://tulo-backend-staging.onrender.com \\
        --token <STAGING_ADMIN_TASK_TOKEN>

Meant to run from a repo checkout on the `staging` branch with push access
(the same shape as daily_batch.py's git steps) -- commits and pushes
directly to staging if anything was baked. Does NOT touch main; syncing to
prod is the normal, separate, human-gated approval step.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bake_images_from_staging import SEED_TEMPLATES_PATH, bake  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

# Mirrors backend/app/fetch_stock_images.py's SINGLE_IMAGE_TEMPLATES keys --
# the only template types with a page-level image_url of their own.
# category_roundup is deliberately excluded: it has no image_url to export,
# its cards render each linked recipe's own (already-baked) photo live at
# serve time (see main.py's get_page()).
SINGLE_IMAGE_TEMPLATES = [
    "recipe_or_dish",
    "ingredient_hub",
    "howto_technique",
    "definition",
    "comparison",
    "substitute",
    "static_page",
]


def fetch_all_pages(base_url: str, template_type: str) -> list[dict]:
    """The full, unpaginated list for one template_type -- omitting
    limit/offset on GET /pages returns everything, still ordered (see that
    endpoint's own comment)."""
    url = f"{base_url.rstrip('/')}/pages?" + urllib.parse.urlencode({"template_type": template_type})
    with urllib.request.urlopen(url, timeout=120) as resp:
        return json.loads(resp.read())


def build_export(base_url: str) -> dict:
    export: dict = {}
    for template_type in SINGLE_IMAGE_TEMPLATES:
        pages = fetch_all_pages(base_url, template_type)
        with_image = 0
        for page in pages:
            if page.get("image_url"):
                export[page["slug"]] = {
                    "image_url": page["image_url"],
                    "image_attribution": page.get("image_attribution"),
                }
                with_image += 1
        print(f"{template_type}: {len(pages)} page(s), {with_image} with a real image_url.")
    return export


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True, help="Staging backend base URL, e.g. https://tulo-backend-staging.onrender.com")
    parser.add_argument("--token", required=True, help="Staging's ADMIN_TASK_TOKEN")
    parser.add_argument("--no-push", action="store_true", help="Bake locally and leave the change staged/uncommitted -- for local dry runs.")
    args = parser.parse_args()

    export = build_export(args.base_url)
    slugs = sorted(export.keys())
    print(f"\n{len(slugs)} slug(s) across all templates have a real image_url on staging -- baking...")

    bake(args.base_url, args.token, slugs, export=export)

    status = subprocess.run(
        ["git", "status", "--porcelain", str(SEED_TEMPLATES_PATH)],
        cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
    )
    if not status.stdout.strip():
        print("\nNo changes -- seed_templates.py already matched staging's live image state for every slug.")
        return

    if args.no_push:
        print("\n--no-push: seed_templates.py left modified, uncommitted.")
        return

    def run(*cmd_args: str) -> None:
        subprocess.run(cmd_args, cwd=str(REPO_ROOT), check=True)

    run("git", "config", "user.name", "tulo-content-bot")
    run("git", "config", "user.email", "content-bot@users.noreply.github.com")
    run("git", "add", str(SEED_TEMPLATES_PATH))
    message = (
        "Full-site audit: bake every live-on-staging image into seed_templates.py\n\n"
        "One-off catch-up run (see audit_and_bake_all_images.py's own docstring): "
        "closes the gap where a batch's images (batch 8) or a manual "
        "review-queue fix (praline, fenugreek-leaves, and others) were "
        "never baked into git-tracked content, so they had no path to "
        "production despite being correct and already reviewed on staging.\n\n"
        "Staging-only until a human reviews and merges this to main.\n"
    )
    run("git", "commit", "-m", message)
    run("git", "push", "origin", "HEAD:staging")
    print("\nCommitted and pushed to staging.")


if __name__ == "__main__":
    main()
