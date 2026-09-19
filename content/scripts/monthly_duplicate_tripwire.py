"""Cheap, deterministic monthly early-warning scan for duplicate-topic
content -- the low-cost half of the two-tier duplicate-content strategy
agreed after the 2026-09-19 audit (108 confirmed clusters, 116 pages
redirected): a full LLM-semantic re-audit only at milestone triggers
(every +500 pages, or before any future AdSense resubmission), plus this
scan on a monthly cadence in between so a real problem doesn't wait for
the next milestone to even be noticed. No LLM calls, no network access,
no live DB -- pure data crunch over SEED_PAGES, seconds not agents.

Two passes per template_type, both restricted to published pages (an
unpublished page is a resolved duplicate, not a new one -- same scoping
as seed_templates.py's own _check_no_duplicate_titles):

1. Exact-signature groups, via the SAME _normalize_title_for_dedup logic
   daily_batch.py's pipeline guard already enforces at every commit. This
   should always come back empty in a healthy repo -- the import-time
   guard already refuses to let a real collision merge -- so a non-empty
   result here means that guard was somehow bypassed (e.g. hand-edited
   directly against a live DB) and needs investigating as a bug in its
   own right, not just a content fix.

2. Fuzzy title-overlap candidates (Jaccard similarity on a broader,
   separate token set, not the guard's exact-match one), scored by prose
   similarity for a confidence read. This is the actual early-warning
   value: title-normalization alone reliably misses same-topic pages that
   are LLM-paraphrased rather than copy-pasted (different wording, same
   facts) -- exactly the gap the semantic-judgment pass in the original
   audit closed by reading actual page content, not just titles. This
   scan can't replace that judgment, but flags candidates worth a human
   look well before the next scheduled full audit.

Exit code is a signal for the scheduled job to show red when pass 2 finds
anything (1) or clean (0) -- this never blocks a deploy or a content
batch, it's a standalone monthly check, not a gate.

Usage: python3 content/scripts/monthly_duplicate_tripwire.py
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

# A throwaway, never-created sqlite path -- seed_templates.py's own
# import-time guards (including _check_no_duplicate_titles, the exact
# thing this script's pass 1 double-checks) run the moment it's imported,
# needing DATABASE_URL/ADMIN_TASK_TOKEN to be set to *something*, but
# nothing here ever opens a real connection.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ADMIN_TASK_TOKEN", "unused")

# Imported straight from seed_templates.py itself (which owns the
# original definition -- daily_batch.py keeps its own must-stay-in-sync
# mirror for its own reasons, see that file's docstring) rather than
# through daily_batch.py, which would drag in that whole pipeline
# script's own heavier dependency chain (requests, image fetching, batch
# generation) for a scan that only needs this one function. Keeps this
# tripwire's own dependency surface to just backend/requirements.txt.
from app.seed_templates import SEED_PAGES, _normalize_title_for_dedup  # noqa: E402

# Separate from _normalize_title_for_dedup's own stopword list on purpose:
# that list is tuned to be exact-match-safe (see its own comment on
# "crispy"/"fresh"); this one is deliberately broader/looser since pass 2
# is advisory candidate-discovery, not a hard equality check -- a false
# positive here costs a human a few seconds looking at a clearly-unrelated
# pair, not a crashed deploy.
_FUZZY_STOPWORDS = {
    "a", "an", "the", "to", "is", "are", "how", "what", "s", "of", "for",
    "with", "vs", "versus", "difference", "and", "or", "in", "on", "at",
    "still", "good", "quickly", "quick", "fast",
    "make", "making", "makes", "made", "cook", "cooking", "cooked", "cooks",
    "recipe", "recipes", "you", "your", "it", "do", "does", "up", "down",
    "guide", "tips", "best", "for",
}

# Same reasoning as full_dedup_scan.py's own list this was built from --
# real prose lives nested in lists/dicts, and bookkeeping/link fields
# would inflate similarity between two pages that just happen to link to
# the same recipe or share an image, not actually say the same thing.
_NON_PROSE_KEYS = {
    "image_url", "image_attribution", "hero_image_query", "image_alt",
    "unpublished", "related_recipe_slugs", "related_ingredient_slugs",
    "item_a_link", "item_b_link", "recipe_slugs", "hub_slug",
    "featured_recipe_slugs", "category_links", "tool_links",
}

# Calibrated empirically against the current corpus (2026-09-19): 0.5
# (the original audit's own candidate-generation threshold, meant to feed
# an LLM semantic-judgment pass over every candidate) produces 319 hits
# here, the overwhelming majority genuinely distinct pages that just share
# heavy domain vocabulary ("gluten-free-bread" / "gluten-free-pita-bread")
# -- exactly the false-positive pattern this project already learned the
# hard way mechanical title scoring can't reliably separate from a real
# duplicate on its own (see the original audit's own notes on this). Too
# noisy for something meant to be glanced at once a month. 0.7 cuts that
# to 11, each with a reported content_sim near zero confirming they're
# genuinely different pages -- still not proof of a real duplicate, this
# is only ever candidate discovery, but a monthly count that stays small
# and dismissible is the actual point of a *cheap* tripwire; a sudden
# jump in count, or a pair with a real content_sim instead of near-zero,
# is the signal worth escalating early, not a large, unreadable list
# every single month.
_JACCARD_THRESHOLD = 0.7


def _fuzzy_tokenize(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in _FUZZY_STOPWORDS}


def _flatten_strings(value, out: list[str]) -> None:
    if isinstance(value, str):
        if len(value) > 15:
            out.append(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            if k not in _NON_PROSE_KEYS:
                _flatten_strings(v, out)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _flatten_strings(item, out)


def _prose(page: dict) -> str:
    parts: list[str] = []
    _flatten_strings(page.get("content") or {}, parts)
    return " ".join(parts)[:6000]


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main() -> int:
    published = [p for p in SEED_PAGES if not p["content"].get("unpublished")]
    by_type: dict[str, list[dict]] = defaultdict(list)
    for p in published:
        if p["template_type"] not in ("homepage", "static_page", "tool_page"):
            by_type[p["template_type"]].append(p)

    print(f"Scanned {len(published)} published pages across {len(by_type)} content template types.\n")

    # --- Pass 1: exact-signature groups (should always be empty) ---
    exact_findings: list[tuple[str, list[str]]] = []
    for template_type, pages in by_type.items():
        sig_groups: dict[str, list[str]] = defaultdict(list)
        for p in pages:
            sig = _normalize_title_for_dedup(p["title"])
            if sig:
                sig_groups[sig].append(p["slug"])
        for slugs in sig_groups.values():
            if len(slugs) > 1:
                exact_findings.append((template_type, slugs))

    if exact_findings:
        print(f"!! Pass 1 found {len(exact_findings)} exact-signature group(s) -- this should be "
              "IMPOSSIBLE if seed_templates.py's own _check_no_duplicate_titles guard ran normally. "
              "Investigate how this bypassed it (e.g. a live DB edit never reflected back into "
              "seed_templates.py) before treating this as an ordinary content fix:")
        for template_type, slugs in exact_findings:
            print(f"    [{template_type}] {', '.join(slugs)}")
        print()
    else:
        print("Pass 1 (exact-signature groups): clean, as expected.\n")

    # --- Pass 2: fuzzy title-overlap candidates ---
    fuzzy_findings = []
    for template_type, pages in by_type.items():
        token_index: dict[str, list[int]] = defaultdict(list)
        token_sets: list[set] = []
        for i, p in enumerate(pages):
            toks = _fuzzy_tokenize(p["title"])
            token_sets.append(toks)
            for tok in toks:
                token_index[tok].append(i)

        candidate_pairs = set()
        for idxs in token_index.values():
            if len(idxs) < 2 or len(idxs) > 40:
                continue
            for a, b in combinations(idxs, 2):
                candidate_pairs.add((min(a, b), max(a, b)))

        for a, b in candidate_pairs:
            sim = _jaccard(token_sets[a], token_sets[b])
            if sim >= _JACCARD_THRESHOLD:
                prose_a, prose_b = _prose(pages[a]), _prose(pages[b])
                content_sim = SequenceMatcher(None, prose_a, prose_b).ratio() if prose_a and prose_b else 0.0
                fuzzy_findings.append((template_type, sim, content_sim, pages[a]["slug"], pages[a]["title"], pages[b]["slug"], pages[b]["title"]))

    fuzzy_findings.sort(key=lambda f: -f[1])
    print(f"Pass 2 (fuzzy title-overlap candidates, Jaccard >= {_JACCARD_THRESHOLD}): {len(fuzzy_findings)} found.")
    for template_type, sim, content_sim, slug_a, title_a, slug_b, title_b in fuzzy_findings:
        print(f"  [{template_type}] title_jaccard={sim:.2f} content_sim={content_sim:.2f}")
        print(f"    A: {slug_a}  --  {title_a!r}")
        print(f"    B: {slug_b}  --  {title_b!r}")

    if exact_findings or fuzzy_findings:
        print(f"\n{len(exact_findings) + len(fuzzy_findings)} total finding(s) worth a human look -- "
              "not a hard failure, this scan never blocks anything, but a repeated or growing count "
              "month over month is the actual signal to schedule a fuller semantic audit before the "
              "next scheduled milestone.")
        return 1

    print("\nClean -- nothing to review this month.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
