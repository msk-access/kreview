#!/usr/bin/env python3
"""PreToolUse / Bash hard-deny for `rm -rf` (house rule: use a `trash` command).

Matches `rm` invoked AS A COMMAND (at a command boundary) with recursive+force
flags. Anchoring on command position is the whole point: a naive substring
check (`'rm -rf' in command`) hard-DENIES any command that merely *contains*
the text "rm -rf" — `grep "rm -rf"`, `echo "...rm -rf..."`, a heredoc or a
learnings note discussing it — none of which delete anything. This version
still blocks real invocations (rm -rf, rm -fr, rm -Rf, sudo rm -rf, `&& rm -rf`,
rm -r -f, rm --recursive --force, find | xargs rm -rf) while letting string
mentions pass.

FAIL-OPEN on parse error (never wedge Bash). This is the hard-deny layer;
injection-guard.py is the ask-layer sibling.

Wire it on PreToolUse / Bash. See hooks/README.md.
"""

import json
import re
import sys

try:
    data = json.load(sys.stdin)
    command = data.get("tool_input", {}).get("command", "") or ""
except Exception:
    sys.exit(0)  # fail-open

# Command boundary: start-of-string, newline, or after ; & | ( (covers && ||).
# Optional benign prefixes (sudo / xargs[-flags]). Then rm with recursive+force
# in any of the common spellings.
RM_RF = re.compile(
    r"(?:^|[\n;&|(])\s*"
    r"(?:sudo\s+)?(?:xargs\s+(?:-\S+\s+)*)?(?:sudo\s+)?"
    r"\brm\s+"
    r"(?:"
    r"-[a-z]*r[a-z]*f[a-z]*"  # -rf, -Rf, -rfv, -vrf ...
    r"|-[a-z]*f[a-z]*r[a-z]*"  # -fr, -vfr ...
    r"|-r[a-z]*\s+-[a-z]*f"  # -r -f  (separate)
    r"|-f[a-z]*\s+-[a-z]*r"  # -f -r  (separate)
    r"|--recursive\b[^\n;&|]*?--force\b"  # --recursive ... --force
    r"|--force\b[^\n;&|]*?--recursive\b"  # --force ... --recursive
    r")",
    re.I,
)

if RM_RF.search(command):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "rm -rf is not allowed. Use the `trash` command instead for "
                        "safe, recoverable deletion."
                    ),
                }
            }
        )
    )
    sys.exit(2)

sys.exit(0)
