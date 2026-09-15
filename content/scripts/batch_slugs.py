"""Prints every slug under a given batch_number in seed_templates.py, one
per line. Built for merge-approved-batch.yml's post-cherry-pick bake step
(see that workflow's own comment for why it exists), but generically
useful anywhere else a plain slug list for one batch is needed.

Matches daily_batch.py's own _PAGE_HEADER_RE / _slugs_for_batch exactly --
not imported from there since daily_batch.py isn't written to be imported
(reads sys.argv, calls sys.exit() on error) and pulls in requests/smtplib/
other deps this doesn't need.

Usage:
    python3 content/scripts/batch_slugs.py <batch_number>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_TEMPLATES_PATH = REPO_ROOT / "backend" / "app" / "seed_templates.py"

_PAGE_HEADER_RE = re.compile(
    r'"slug":\s*"([^"]+)",\s*\n\s*"template_type":\s*"[^"]+",\s*\n'
    r'\s*"title":\s*"(?:[^"\\]|\\.)*",\s*\n\s*"batch_number":\s*(\d+),'
)


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <batch_number>", file=sys.stderr)
        raise SystemExit(1)
    batch_number = int(sys.argv[1])
    text = SEED_TEMPLATES_PATH.read_text()
    for m in _PAGE_HEADER_RE.finditer(text):
        if int(m.group(2)) == batch_number:
            print(m.group(1))


if __name__ == "__main__":
    main()
