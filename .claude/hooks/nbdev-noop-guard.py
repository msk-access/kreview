#!/usr/bin/env python3
"""PreToolUse / Bash guard: block nbdev invocations that silently do nothing.

WHY THIS EXISTS
    `python3 -m nbdev.export` and `python3 -m nbdev.doclinks` exit 0 and write NOTHING.
    They look like they worked. Three PRs in this repo reported "export is idempotent —
    zero diff" on the strength of them, and the diff was empty only because nothing ever
    ran. The CI export-sync gate used the same form, so it passed vacuously too. The real
    drift (a live constant that existed in .py but not the notebook, and a stale _modidx)
    went unnoticed for weeks.

    Underscore aliases (`nbdev_export`) are a second trap: they do not exist in this
    install, so the shell reports "command not found" — which is loud on its own, but
    inside a pipeline (`nbdev_export | tail`) the pipeline's exit status comes from the
    LAST command, so the failure is swallowed and the step appears to succeed.

WHAT IS CORRECT
    Console scripts, hyphenated:  nbdev-export, nbdev-test, nbdev-clean, nbdev-update
    Export must be followed by black, because nbdev 3.0.12 does not implement
    `black_formatting` at all (the key appears nowhere in its source and it never imports
    black), while CI runs `black --check .`:

        nbdev-export && black kreview/

    `python3 -m nbdev.sync --fname <file>` IS functional and is the supported way to push
    .py edits back into a notebook — it is deliberately NOT blocked here.

DECISION: ask, not deny. A `-m` form may legitimately appear inside a longer diagnostic
command, and a hard block on a false positive is worse than one confirmation. The point is
to make the silence impossible to miss.

FAIL-OPEN on any internal error (never wedge Bash). Wire on PreToolUse / Bash.
"""

import json
import re
import sys

# The no-op module forms. `nbdev.sync` is intentionally absent — it works.
NOOP = re.compile(r"python3?\s+-m\s+nbdev\.(export|doclinks)\b")
# Underscore aliases that do not exist as console scripts in this install.
BAD_ALIAS = re.compile(
    r"(?:^|[\s;&|(])nbdev_(export|test|clean|update|doclinks|prepare)\b"
)


def ask(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def main() -> None:
    try:
        data = json.load(sys.stdin)
        cmd = data.get("tool_input", {}).get("command", "") or ""
    except Exception:
        print("{}")  # fail-open: never wedge Bash on a parse error
        return

    m = NOOP.search(cmd)
    if m:
        ask(
            f"nbdev no-op: `python3 -m nbdev.{m.group(1)}` exits 0 and writes NOTHING, so any "
            "'zero diff' check against it proves nothing. Use the console script instead:\n"
            "    nbdev-export && black kreview/\n"
            "(`python3 -m nbdev.sync --fname <file>` is fine — that one works.)"
        )

    m = BAD_ALIAS.search(cmd)
    if m:
        ask(
            f"`nbdev_{m.group(1)}` does not exist in this install (the console scripts are "
            f"hyphenated: `nbdev-{m.group(1)}`). Inside a pipeline the 'command not found' is "
            "hidden, because the pipeline exit status comes from the last command."
        )

    print("{}")


if __name__ == "__main__":
    main()
