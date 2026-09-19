"""Recall check for monthly_duplicate_tripwire.py's Jaccard threshold,
requested after tightening it from 0.5 (319 findings/month) to 0.7 (11
findings/month): does 0.7 still catch the site's own REAL, confirmed
duplicate pairs, or was it tuned purely against false positives?

Ground truth: the 122 pages from the 2026-09-19 audit's 108 confirmed
duplicate clusters are still in SEED_PAGES, unpublished, each carrying
content["redirect_to"] pointing at the surviving page it duplicated (see
main.py's /redirects docstring) -- this is real, human-confirmed
duplicate-content ground truth, not a synthetic test case.

For every (duplicate, survivor) pair, computes the exact same
_fuzzy_tokenize Jaccard score monthly_duplicate_tripwire.py itself uses,
and reports how many would be caught at 0.7 vs. missed vs. missed even at
the original 0.5 (meaning title overlap was never how the ORIGINAL audit
found that pair -- it read actual page content, not just titles; a miss
here is not new information, just confirmation that this tripwire's pass
2 was never meant to replace that reading, only flag additional
candidates worth a look between audits)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ADMIN_TASK_TOKEN", "unused")

from app.seed_templates import SEED_PAGES  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from monthly_duplicate_tripwire import _fuzzy_tokenize, _jaccard, _JACCARD_THRESHOLD  # noqa: E402


def main() -> None:
    by_slug = {p["slug"]: p for p in SEED_PAGES}
    pairs = []
    for p in SEED_PAGES:
        target_slug = p["content"].get("redirect_to")
        if not target_slug:
            continue
        target = by_slug.get(target_slug)
        if target is None:
            continue
        pairs.append((p, target))

    print(f"Ground truth: {len(pairs)} real, human-confirmed duplicate (page -> redirect_to survivor) pairs found in SEED_PAGES.\n")
    if not pairs:
        print("No redirect_to pairs found -- can't validate recall against real ground truth.")
        sys.exit(1)

    caught_07, missed_07_caught_05, missed_at_05 = [], [], []
    for dup, survivor in pairs:
        sim = _jaccard(_fuzzy_tokenize(dup["title"]), _fuzzy_tokenize(survivor["title"]))
        row = (sim, dup["slug"], dup["title"], survivor["slug"], survivor["title"])
        if sim >= _JACCARD_THRESHOLD:
            caught_07.append(row)
        elif sim >= 0.5:
            missed_07_caught_05.append(row)
        else:
            missed_at_05.append(row)

    print(f"Caught at current threshold ({_JACCARD_THRESHOLD}): {len(caught_07)}/{len(pairs)}")
    print(f"Would be caught at 0.5 but MISSED at {_JACCARD_THRESHOLD} (real recall lost by tightening): {len(missed_07_caught_05)}/{len(pairs)}")
    print(f"Missed even at 0.5 (title-Jaccard alone was never how these were found -- confirms pass 2 is a supplement, not a replacement, for the semantic audit): {len(missed_at_05)}/{len(pairs)}\n")

    if missed_07_caught_05:
        print(f"--- {len(missed_07_caught_05)} pair(s) the 0.5 -> 0.7 tightening actually lost ---")
        for sim, dup_slug, dup_title, surv_slug, surv_title in sorted(missed_07_caught_05, reverse=True):
            print(f"  jaccard={sim:.2f}  {dup_slug!r} ({dup_title!r})  ->  {surv_slug!r} ({surv_title!r})")
        print()

    print("--- sample of pairs missed even at 0.5 (title-only can't catch these; needs the semantic pass) ---")
    for sim, dup_slug, dup_title, surv_slug, surv_title in sorted(missed_at_05, reverse=True)[:10]:
        print(f"  jaccard={sim:.2f}  {dup_slug!r} ({dup_title!r})  ->  {surv_slug!r} ({surv_title!r})")


if __name__ == "__main__":
    main()
