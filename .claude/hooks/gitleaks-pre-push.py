#!/usr/bin/env python3
"""PreToolUse / Bash hook: run gitleaks before any `git push`, ask before force-push.

Scans the commits actually being pushed for secrets, denies the push on a real
finding, and asks (rather than silently passing) when gitleaks is not installed.
Force pushes always ask, because the default posture here is no force push.

Requires gitleaks on PATH (e.g. `brew install gitleaks`).
Wire it on PreToolUse / Bash. See hooks/README.md.
"""
import json
import re
import subprocess
import sys

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")

# Match `git push` as the start of any segment (start-of-string, ;, &, |, &&, ||)
is_push = bool(re.search(r"(^|[;&|]|&&|\|\|)\s*git\s+push\b", cmd))
if not is_push:
    print("{}")
    sys.exit(0)

is_force = bool(re.search(r"\bgit\s+push\b.*(--force\b|--force-with-lease\b|\s\+)", cmd))

# Scan git-tracked content, NOT the raw working tree. A `--no-git` filesystem
# scan flags gitignored, never-pushed files (.env.local, build dirs,
# node_modules) — false positives, since none of that reaches the remote.
# Git-mode scans commits instead. Scope to the commits actually being pushed
# (the range the upstream is behind HEAD): fast on big repos, and it won't
# re-nag a secret already in pushed history. No upstream yet (first push of a
# new branch) -> scan full history, which is correct for a first push.
log_opts = None
try:
    up = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        capture_output=True, text=True, timeout=10,
    )
    if up.returncode == 0 and up.stdout.strip():
        log_opts = f"{up.stdout.strip()}..HEAD"
except Exception:
    pass  # any failure -> full-history scan below (conservative)

gitleaks_cmd = ["gitleaks", "detect", "--no-banner", "--redact",
                "--exit-code", "1", "--source", "."]
if log_opts:
    gitleaks_cmd.append(f"--log-opts={log_opts}")

try:
    res = subprocess.run(gitleaks_cmd, capture_output=True, text=True, timeout=45)
except FileNotFoundError:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                "gitleaks not on PATH — run a secret scan before pushing. "
                "Install (`brew install gitleaks`) or confirm to bypass."
            ),
        }
    }))
    sys.exit(0)
except subprocess.TimeoutExpired:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": "gitleaks scan timed out after 45s. Confirm push manually.",
        }
    }))
    sys.exit(0)

if res.returncode != 0:
    body = (res.stdout or res.stderr or "(no output)")[-1500:]
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "gitleaks BLOCKED push: secret findings before sending to remote.\n"
                + body
            ),
        }
    }))
elif is_force:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                "Force push detected. Force push is off by default here. "
                "Confirm explicitly to proceed."
            ),
        }
    }))
else:
    print("{}")
