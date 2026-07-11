#!/usr/bin/env python3
"""PostToolUse / Edit|Write advisory: remind to sync when a GENERATED nbdev module is edited.

kreview is an nbdev project: `kreview/*.py` are generated from `nbs/*.ipynb`. Editing a
generated module directly (a valid refactor workflow) is fine, but forgetting to sync it
back to its notebook is the #1 source of notebook<->.py drift and a stale `_modidx.py`.

This hook does NOT block (editing .py is reversible and a legitimate workflow). It emits a
one-line reminder with the exact sync/verify commands, only when the edited file is a
generated module. Standalone modules (`scoreboard.py`, `feature_cards.py`) have no notebook
and are exempt. Anything outside `kreview/` is ignored.

FAIL-OPEN on any error (never wedge the tool). Wire on PostToolUse / Edit|MultiEdit|Write.
"""
import json
import os
import re
import sys

# Standalone, hand-maintained modules with no notebook source (edit directly, no sync).
EXEMPT = {"scoreboard.py", "feature_cards.py", "_modidx.py", "__init__.py"}


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return

    path = (data.get("tool_input", {}) or {}).get("file_path", "") or ""
    if not path:
        print("{}")
        return

    # Normalize to a repo-relative-ish check: must live under a `kreview/` package dir
    # and be a .py file, excluding the standalone/exempt modules.
    norm = path.replace(os.sep, "/")
    in_pkg = re.search(r"(^|/)kreview/(?!templates/)[^/]*\.py$", norm)
    base = norm.rsplit("/", 1)[-1]

    if in_pkg and base not in EXEMPT:
        module = base
        nb_hint = ""
        # Best-effort: point at the likely notebook if a mapping is obvious.
        stem = module[:-3]
        print(json.dumps({
            "systemMessage": (
                f"nbdev: you edited the generated module kreview/{module}. Before committing, "
                f"sync it back so the notebook stays the source of truth:\n"
                f"  python3 -m nbdev.sync --fname kreview/{module}\n"
                f"  python3 -m nbdev.export   # must produce ZERO git diff (idempotency)\n"
                f"  python3 -m nbdev.doclinks # refresh _modidx.py\n"
                f"Do NOT leave kreview/{module} edited without a matching nbs/ change."
                f"{nb_hint}"
            )
        }))
    else:
        print("{}")


if __name__ == "__main__":
    main()
