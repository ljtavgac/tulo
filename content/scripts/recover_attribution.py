"""Calls the new /admin/lookup-recovered-attribution (report) or
/admin/apply-recovered-attribution (apply) endpoints against a real
backend, batching slugs to stay under a reasonable query-string length.
Never touches image_url -- see main.py's _lookup_recovered_attribution
and apply_recovered_attribution docstrings for the mechanism.

Usage:
    BACKEND_BASE_URL=... ADMIN_TASK_TOKEN=... \\
    python3 content/scripts/recover_attribution.py report slug-one slug-two ...

    BACKEND_BASE_URL=... ADMIN_TASK_TOKEN=... \\
    python3 content/scripts/recover_attribution.py apply --dry-run slug-one ...

    BACKEND_BASE_URL=... ADMIN_TASK_TOKEN=... \\
    python3 content/scripts/recover_attribution.py apply --write slug-one ...
"""

import os
import sys

import requests

BATCH_SIZE = 30


def chunks(items, n):
    for i in range(0, len(items), n):
        yield items[i : i + n]


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]
    rest = sys.argv[2:]
    dry_run = True
    if mode == "apply":
        if rest[0] == "--write":
            dry_run = False
            rest = rest[1:]
        elif rest[0] == "--dry-run":
            rest = rest[1:]

    slugs = rest
    base = os.environ["BACKEND_BASE_URL"].rstrip("/")
    token = os.environ["ADMIN_TASK_TOKEN"]

    endpoint = "lookup-recovered-attribution" if mode == "report" else "apply-recovered-attribution"

    recovered, unrecoverable, errors = [], [], []
    for batch in chunks(slugs, BATCH_SIZE):
        params = {"token": token, "slugs": ",".join(batch)}
        if mode == "apply":
            params["dry_run"] = "true" if dry_run else "false"
        r = requests.get(f"{base}/admin/{endpoint}", params=params, timeout=120)
        r.raise_for_status()
        result = r.json()
        for slug, info in result.items():
            print(f"{slug}: {info}")
            if info.get("recoverable") or info.get("written") or info.get("would_write"):
                recovered.append(slug)
            elif "error" in info:
                errors.append((slug, info["error"]))
            else:
                unrecoverable.append((slug, info.get("reason", info)))

    print()
    print(f"Total: {len(slugs)}  recovered/would-recover: {len(recovered)}  unrecoverable: {len(unrecoverable)}  errors: {len(errors)}")


if __name__ == "__main__":
    main()
