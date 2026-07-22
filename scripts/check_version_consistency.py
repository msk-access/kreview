#!/usr/bin/env python3
"""Assert the kreview version string is identical across all files that hardcode it.

The version lives in three places that are hand-synced:
  - settings.ini            version = X            (nbdev source of truth)
  - kreview/__init__.py      __version__ = "X"     (generated from settings.ini)
  - nextflow/nextflow.config params.kreview_version = 'X'  (drives container image tags)

nextflow.config pins container tags to `ghcr.io/msk-access/kreview:v${params.kreview_version}`,
so a lagging version silently pulls a nonexistent/stale image on HPC. This check fails CI on any
drift. On release, pass --tag "$GITHUB_REF_NAME" to also assert the git tag matches.

Note: `manifest.version` reads back `params.kreview_version` rather than holding its own
literal, because `manifest` is not resolvable from `process`/`profiles` scope on Nextflow 24+
(issue #80). The param is therefore the single literal, and the pattern below anchors to it by
name so renaming it fails this check loudly instead of silently matching another version-like
string elsewhere in the file.

Usage:
    python3 scripts/check_version_consistency.py            # compare the three files
    python3 scripts/check_version_consistency.py --tag v0.0.29   # also compare the release tag

Exit 0 if all agree, 1 otherwise. Stdlib only.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _search(path: Path, pattern: str) -> str | None:
    try:
        text = path.read_text()
    except OSError:
        return None
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1) if m else None


def collect() -> dict[str, str | None]:
    return {
        "settings.ini": _search(
            ROOT / "settings.ini", r"^version\s*=\s*([0-9][^\s#]*)"
        ),
        "kreview/__init__.py": _search(
            ROOT / "kreview" / "__init__.py", r'__version__\s*=\s*["\']([^"\']+)["\']'
        ),
        "nextflow/nextflow.config": _search(
            ROOT / "nextflow" / "nextflow.config",
            r"^params\.kreview_version\s*=\s*['\"]([0-9][^'\"]*)['\"]",
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--tag",
        default=None,
        help="Release tag to also compare (a leading 'v' is stripped), e.g. v0.0.29.",
    )
    args = ap.parse_args()

    versions = collect()
    if args.tag is not None:
        versions["git tag (--tag)"] = args.tag.lstrip("v")

    width = max(len(k) for k in versions)
    for name, val in versions.items():
        print(f"  {name:<{width}} : {val if val is not None else '<NOT FOUND>'}")

    missing = [k for k, v in versions.items() if v is None]
    if missing:
        print(
            f"\nFAIL: could not find a version in: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    distinct = set(versions.values())
    if len(distinct) != 1:
        print(
            f"\nFAIL: version strings disagree: {sorted(distinct)}. "
            "Update every file to the same version.",
            file=sys.stderr,
        )
        return 1

    print(f"\nOK: version is consistent ({distinct.pop()}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
