"""Reads an /admin/image-audit JSON response from stdin and prints
whatever it says about a fixed list of slugs (passed as argv) -- whether
each appears in missing/broken, and if neither, that the row has a valid
image_url the audit didn't flag. Doesn't itself say whether a slug's row
exists at all (a deleted row just never appears anywhere in the audit),
only what the audit found for a page that does exist."""

import json
import sys

data = json.load(sys.stdin)
target_slugs = set(sys.argv[1:])

for category in ("missing", "broken", "dead"):
    for entry in data.get(category) or []:
        if entry.get("slug") in target_slugs:
            print(f"{category}: {entry}")

found_in_any = {
    entry.get("slug")
    for category in ("missing", "broken", "dead")
    for entry in (data.get(category) or [])
}
for slug in target_slugs:
    if slug not in found_in_any:
        print(f"not flagged by audit (has a real image_url, or its template_type isn't audited): {slug}")
