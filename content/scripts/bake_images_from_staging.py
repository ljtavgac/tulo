"""Bake step: pulls image_url/image_attribution for a batch of slugs from a
running staging backend (via GET /admin/export-images) and writes them into
seed_templates.py as literal data, before that batch's code merges to main.

Why this step exists: image_url only ever lives in a runtime database
(see _RUNTIME_IMAGE_KEYS in seed_templates.py), never in the git-tracked
seed data -- fetch_stock_images.py writes it straight to the DB, and
resync_content() deliberately never touches it. So validating a new
batch's photos on staging and then just merging the *code* to production
would NOT carry those fetched images along: production's seed() would
insert the same pages with no image_url at all, and restart the exact
fetch race (customers seeing placeholder boxes) that the staging pipeline
exists to avoid. Baking the staging-fetched URLs into SEED_PAGES as
literal data means production's seed() inserts each new page already
carrying a real photo, no fetch race, no placeholder window.

Usage:
    python3 content/scripts/bake_images_from_staging.py \\
        --base-url https://tulo-backend-staging.onrender.com \\
        --token <STAGING_ADMIN_TASK_TOKEN> \\
        banana-nut-bread parmesan-crusted-chicken ube-vs-taro-what-s-the-difference

    # or from a file, one slug per line (blank lines and #-comments ignored):
    python3 content/scripts/bake_images_from_staging.py \\
        --base-url https://tulo-backend-staging.onrender.com \\
        --token <STAGING_ADMIN_TASK_TOKEN> \\
        --slugs-file content/scripts/output/pilot_batch_50_slugs.txt

Run this only after: (1) the batch's pages are already in SEED_PAGES (via
integrate_batch_results.py) and merged to the `staging` branch, (2)
staging's own deploy has seeded them and fetch_stock_images.py has
actually run for them (automatic on deploy, or trigger via staging's
GET /admin/fetch-images), and (3) you've manually reviewed the photos on
staging and they look right -- this script has no way to tell a correct
photo from a wrong-subject one, that's what the staging review is for.

Safe to re-run on the same slugs (e.g. after swapping a bad photo on
staging and re-fetching): each run replaces that slug's image_url/
image_attribution in seed_templates.py rather than stacking duplicates.
A slug the export endpoint reports as not-yet-fetched (null image_url)
is skipped with a warning, not written as a null -- so this never
overwrites nothing over something."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from integrate_batch_results import py_literal  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_TEMPLATES_PATH = REPO_ROOT / "backend" / "app" / "seed_templates.py"

# Matches a previously-baked image_attribution dict: opens at 12-space
# indent and its closing brace is the first "            },\n" after it --
# safe because every field this script ever writes into that dict
# (photographer/photographer_url/source, see fetch_stock_images.py's
# _apply_result) is a flat string, so nothing inside it can produce
# another closing brace at this same indentation.
_ATTRIBUTION_RE = re.compile(r'            "image_attribution": \{.*?\n            \},\n', re.DOTALL)
_IMAGE_URL_RE = re.compile(r'            "image_url": .*?,\n')


def fetch_export(base_url: str, token: str, slugs: list[str]) -> dict:
    query = urllib.parse.urlencode({"token": token, "slugs": ",".join(slugs)})
    url = f"{base_url.rstrip('/')}/admin/export-images?{query}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"export-images request failed ({e.code}): {e.read().decode(errors='replace')}") from e


def _patch_entry(entry: str, image_url: str, image_attribution: dict | None) -> str:
    """Strips any previously-baked image_url/image_attribution out of this
    single SEED_PAGES entry, then inserts fresh ones right after the
    "content": { line."""
    entry = _ATTRIBUTION_RE.sub("", entry)
    entry = _IMAGE_URL_RE.sub("", entry)

    content_marker = '"content": {\n'
    insert_at = entry.index(content_marker) + len(content_marker)
    insertion = f'            "image_url": {py_literal(image_url)},\n'
    insertion += f'            "image_attribution": {py_literal(image_attribution, indent=3)},\n'
    return entry[:insert_at] + insertion + entry[insert_at:]


def bake(base_url: str, token: str, slugs: list[str]) -> None:
    export = fetch_export(base_url, token, slugs)

    text = SEED_TEMPLATES_PATH.read_text()
    entry_pattern = re.compile(r'(?=    \{\n        "slug")')
    parts = entry_pattern.split(text)
    header, entries = parts[0], parts[1:]

    entry_by_slug: dict[str, int] = {}
    for i, entry in enumerate(entries):
        m = re.search(r'"slug": "([^"]+)"', entry)
        if m:
            entry_by_slug[m.group(1)] = i

    baked, skipped, missing = [], [], []
    for slug in slugs:
        result = export.get(slug)
        if result is None or "error" in result:
            missing.append((slug, result.get("error") if result else "not in export response"))
            continue
        if not result.get("image_url"):
            skipped.append(slug)
            continue
        if slug not in entry_by_slug:
            missing.append((slug, "not found in SEED_PAGES -- integrate the batch first"))
            continue
        i = entry_by_slug[slug]
        entries[i] = _patch_entry(entries[i], result["image_url"], result.get("image_attribution"))
        baked.append(slug)

    if baked:
        SEED_TEMPLATES_PATH.write_text(header + "".join(entries))

    print(f"Baked {len(baked)} image(s) into {SEED_TEMPLATES_PATH}: {', '.join(baked)}")
    if skipped:
        print(f"Skipped {len(skipped)} slug(s) with no image_url yet on staging (run /admin/fetch-images there first): {', '.join(skipped)}")
    if missing:
        print(f"Could not bake {len(missing)} slug(s):")
        for slug, reason in missing:
            print(f"  {slug}: {reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True, help="Staging backend base URL, e.g. https://tulo-backend-staging.onrender.com")
    parser.add_argument("--token", required=True, help="Staging's ADMIN_TASK_TOKEN")
    parser.add_argument("--slugs-file", help="Path to a file of slugs, one per line")
    parser.add_argument("slugs", nargs="*", help="Slugs to bake, if not using --slugs-file")
    args = parser.parse_args()

    slugs = list(args.slugs)
    if args.slugs_file:
        for line in Path(args.slugs_file).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                slugs.append(line)

    if not slugs:
        parser.error("no slugs given -- pass them as arguments or via --slugs-file")

    bake(args.base_url, args.token, slugs)


if __name__ == "__main__":
    main()
