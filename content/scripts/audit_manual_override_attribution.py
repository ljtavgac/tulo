"""Full-corpus audit: every published page whose image_attribution has no
photographer (photographer is None/missing), broken out by host
(pexels vs unsplash vs other/unknown). Supersedes the earlier
Unsplash-only audit -- the user wants consistent attribution regardless
of whether the host legally requires it, so this reports both.

Read-only, no network calls -- reads straight from SEED_PAGES via AST
parsing, same pattern used throughout this project's other audits."""

import sys
from pathlib import Path

import argparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.seed_templates import SEED_PAGES  # noqa: E402


def host_of(image_url: str | None) -> str:
    if not image_url:
        return "none"
    if "images.pexels.com" in image_url:
        return "pexels"
    if "images.unsplash.com" in image_url:
        return "unsplash"
    return "other"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Print only a single comma-joined line of every pexels/unsplash slug missing attribution (for scripting/CI), no other output.",
    )
    args = parser.parse_args()

    by_host_missing: dict[str, list[str]] = {"pexels": [], "unsplash": [], "other": [], "none": []}
    total_with_image = 0

    for page in SEED_PAGES:
        content = page.get("content", {})
        if content.get("unpublished"):
            continue
        image_url = content.get("image_url")
        if not image_url:
            continue
        total_with_image += 1
        attribution = content.get("image_attribution") or {}
        photographer = attribution.get("photographer")
        if photographer:
            continue
        by_host_missing[host_of(image_url)].append(page["slug"])

    if args.csv:
        print(",".join(by_host_missing["pexels"] + by_host_missing["unsplash"]))
        return

    print(f"Published pages with an image_url: {total_with_image}")
    print()
    for host in ("pexels", "unsplash", "other", "none"):
        slugs = by_host_missing[host]
        print(f"{host}: {len(slugs)} missing photographer attribution")
    print()
    for host in ("pexels", "unsplash", "other"):
        slugs = by_host_missing[host]
        if slugs:
            print(f"--- {host} ({len(slugs)}) ---")
            print(",".join(slugs))
            print()


if __name__ == "__main__":
    main()
