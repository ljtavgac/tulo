"""Duplicate/near-duplicate topic detector for CONTENT_QUEUE.csv, run
against the full ~12,425-row queue before ever building a real batch.

Built in direct response to two collisions found by chance in the 50-row
pilot sample (see PILOT_BATCH_STATUS.md):
- `corn-starch` (queue row, `not_started`) turned out to be the exact same
  topic as an already-published page, just spelled differently ("corn
  starch" vs. "Cornstarch") -- a naive slug/title string comparison misses
  this because "corn starch" and "Cornstarch" produce different slugs
  (`corn-starch` vs `cornstarch`) even though they're clearly the same
  ingredient. This script normalizes by stripping ALL non-alphanumeric
  characters (not just replacing them with hyphens) specifically to catch
  that class of collision.
- Two *different* queue rows independently led the model to generate the
  same specific dish ("Flourless Chocolate Cake"). That collision is
  emergent from generation, not visible in the queue's own title text
  (the two rows had genuinely different topic titles) -- it can't be
  caught here. It's instead caught post-generation, in
  validate_batch_results.py's duplicate-title-within-batch check.

This script only catches the first class: two *queue rows* (or a queue row
and an already-published page) that are mechanically the same topic
before any generation happens. Read-only, no network calls, no repo writes.

Usage:
    python3 content/scripts/check_queue_duplicates.py
    python3 content/scripts/check_queue_duplicates.py content/pilot_batch_50.csv
Exits non-zero if any exact collision is found (near-duplicates are
reported but don't fail the run -- they need a human judgment call, not
an automatic exclusion).
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_batch_requests import SEED_TEMPLATES_PATH  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUEUE_PATH = REPO_ROOT / "content" / "CONTENT_QUEUE.csv"

PAGE_PATTERN = re.compile(
    r'"slug":\s*"([^"]+)",\s*\n\s*"template_type":\s*"([^"]+)",\s*\n\s*"title":\s*"([^"]+)"'
)


def normalize_topic(title: str) -> str:
    """Strips ALL non-alphanumeric characters (no hyphen/space separator
    kept) and lowercases -- "corn starch", "Corn-Starch", and "Cornstarch"
    all collapse to the same key. Deliberately more aggressive than
    build_batch_requests.slugify(), which keeps hyphens and would treat
    "corn-starch" and "cornstarch" as different strings."""
    return re.sub(r"[^a-z0-9]", "", title.lower())


def normalize_topic_singular(title: str) -> str:
    """A looser key on top of normalize_topic() that also strips one
    trailing 's' -- catches "brownie" vs "brownies"-type near-duplicates.
    Reported separately as lower-confidence: this also collapses some
    genuinely-different words (e.g. "hummus" vs "hummu"), so it's for a
    human to look at, not to auto-exclude on."""
    key = normalize_topic(title)
    return key[:-1] if key.endswith("s") and len(key) > 3 else key


def load_existing_page_titles() -> list[tuple[str, str, str]]:
    """Returns (slug, template_type, title) for every page already in
    SEED_PAGES, regardless of status -- these are live on the site, so any
    queue row matching one of these is a duplicate no matter what the CSV's
    own `status` column says."""
    text = SEED_TEMPLATES_PATH.read_text()
    return list(PAGE_PATTERN.findall(text))


def load_queue_rows(csv_path: Path) -> list[dict]:
    with csv_path.open(newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_QUEUE_PATH
    rows = load_queue_rows(csv_path)
    existing_pages = load_existing_page_titles()

    # Only rows not yet generated are worth checking -- a `published` row
    # is either one of these already-live pages or was already resolved
    # (kept/excluded) by a prior pilot's dedup pass.
    candidates = [r for r in rows if r.get("status") == "not_started" and r.get("title")]

    exact_key_to_rows: dict[str, list[dict]] = defaultdict(list)
    near_key_to_rows: dict[str, list[dict]] = defaultdict(list)
    for row in candidates:
        exact_key_to_rows[normalize_topic(row["title"])].append(row)
        near_key_to_rows[normalize_topic_singular(row["title"])].append(row)

    existing_by_exact_key: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for slug, template_type, title in existing_pages:
        existing_by_exact_key[normalize_topic(title)].append((slug, template_type, title))

    def row_label(row: dict) -> str:
        return f"row(batch={row.get('batch_number')}, type={row.get('template_type')}): {row['title']!r}"

    blocking_collisions: list[str] = []

    # Queue row vs. queue row, exact topic match.
    for key, rows_with_key in exact_key_to_rows.items():
        if len(rows_with_key) > 1:
            labels = "; ".join(row_label(r) for r in rows_with_key)
            blocking_collisions.append(f"queue/queue collision on {key!r}: {labels}")

    # Queue row vs. already-published page, exact topic match.
    for key, rows_with_key in exact_key_to_rows.items():
        matches = existing_by_exact_key.get(key)
        if matches:
            for slug, template_type, title in matches:
                for row in rows_with_key:
                    blocking_collisions.append(
                        f"queue/published collision on {key!r}: {row_label(row)} "
                        f"<-> already-published {template_type} {slug!r} ({title!r})"
                    )

    near_duplicates: list[str] = []
    for key, rows_with_key in near_key_to_rows.items():
        distinct_titles = {r["title"] for r in rows_with_key}
        if len(distinct_titles) > 1:
            labels = "; ".join(row_label(r) for r in rows_with_key)
            near_duplicates.append(f"possible near-duplicate on {key!r}: {labels}")

    print(f"Checked {len(candidates)} not_started row(s) from {csv_path} "
          f"against each other and {len(existing_pages)} already-published page(s).")
    print()
    print(f"Exact collisions (must exclude/merge before this batch runs): {len(blocking_collisions)}")
    for c in blocking_collisions:
        print(f"  - {c}")
    print()
    print(f"Near-duplicates (human judgment call, not auto-excluded): {len(near_duplicates)}")
    for c in near_duplicates:
        print(f"  - {c}")

    if blocking_collisions:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
