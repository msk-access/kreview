#!/usr/bin/env python3
"""PreToolUse / Bash hook: run gitleaks before any `git push`, ask before force-push.

Scans the commits actually being pushed for BOTH secrets and PHI/PII, denies the push on
a real finding, and asks (rather than silently passing) when gitleaks is missing, times
out, or fails to run. Force pushes always ask, because the default posture here is no
force push.

kreview is a PUBLIC repo that commits an agent memory store (`.agents/memory/`), so the
PHI rules matter as much as the secret rules. Rules and the placeholder/allowlist policy
live in `.gitleaks.toml` (auto-discovered — no --config flag needed). Verify the rules
still work with `bash scripts/check_phi_guard.sh`.

Two gitleaks blind spots are covered explicitly: it does not scan commit MESSAGES (so the
messages of the commits being pushed are scanned separately here, reusing the same rules),
and it does not scan its own config file (asserted by check_phi_guard.sh instead).

Requires gitleaks on PATH (e.g. `brew install gitleaks`).
Wire it on PreToolUse / Bash. See hooks/README.md.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")

# Match `git push` as the start of any segment (start-of-string, ;, &, |, &&, ||)
is_push = bool(re.search(r"(^|[;&|]|&&|\|\|)\s*git\s+push\b", cmd))
if not is_push:
    print("{}")
    sys.exit(0)

is_force = bool(
    re.search(r"\bgit\s+push\b.*(--force\b|--force-with-lease\b|\s\+)", cmd)
)

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
        capture_output=True,
        text=True,
        timeout=10,
    )
    if up.returncode == 0 and up.stdout.strip():
        log_opts = f"{up.stdout.strip()}..HEAD"
except Exception:
    pass  # any failure -> full-history scan below (conservative)

gitleaks_cmd = [
    "gitleaks",
    "detect",
    "--no-banner",
    "--redact",
    "--exit-code",
    "1",
    "--source",
    ".",
]
if log_opts:
    gitleaks_cmd.append(f"--log-opts={log_opts}")

try:
    res = subprocess.run(gitleaks_cmd, capture_output=True, text=True, timeout=100)
except FileNotFoundError:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": (
                        "gitleaks not on PATH — run a secret scan before pushing. "
                        "Install (`brew install gitleaks`) or confirm to bypass."
                    ),
                }
            }
        )
    )
    sys.exit(0)
except subprocess.TimeoutExpired:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": "gitleaks scan timed out after 100s. Confirm push manually.",
                }
            }
        )
    )
    sys.exit(0)

# gitleaks exit codes: 0 = clean, 1 = findings (we pass --exit-code 1), >=2 = gitleaks
# itself failed (bad .gitleaks.toml, git error). Those are different situations and must
# not report the same way: a broken scanner is NOT "no leaks", and calling it "findings"
# sends people hunting for a secret that does not exist.
if res.returncode == 1:
    body = (res.stdout or res.stderr or "(no output)")[-1500:]
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "gitleaks BLOCKED push: secret or PHI/PII findings before sending "
                        "to remote. This repo is PUBLIC — do not bypass. Rules live in "
                        ".gitleaks.toml; verify them with scripts/check_phi_guard.sh.\n"
                        + body
                    ),
                }
            }
        )
    )
elif res.returncode != 0:
    # Scanner error: we could not verify. Fail loud and ask rather than silently allowing.
    body = (res.stderr or res.stdout or "(no output)")[-1500:]
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": (
                        f"gitleaks FAILED to run (exit {res.returncode}) — the push was NOT "
                        "scanned for secrets or PHI. This is a scanner/config error, not a "
                        "finding. Fix it (check .gitleaks.toml) or confirm to push unscanned.\n"
                        + body
                    ),
                }
            }
        )
    )
else:
    # ── Commit MESSAGE scan ────────────────────────────────────────────────────
    # gitleaks scans diffs, NOT commit messages. A value redacted from a file can still be
    # published by describing the redaction in the message. Scan the messages of commits not
    # yet on any remote: that is exactly what this push would publish, and it avoids
    # re-flagging already-published history we cannot change.
    # Rules are NOT duplicated here — the messages are written to a temp file and run
    # through gitleaks using this repo's own .gitleaks.toml.
    msg_finding = None
    try:
        log = subprocess.run(
            ["git", "log", "HEAD", "--not", "--remotes", "--format=%B"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        messages = log.stdout.strip()
        if messages:
            tmpdir = tempfile.mkdtemp(prefix="kreview-msgscan-")
            try:
                # Deliberately NOT named .gitleaks.toml — gitleaks skips its own config file.
                with open(os.path.join(tmpdir, "commit-messages.txt"), "w") as fh:
                    fh.write(messages)
                mres = subprocess.run(
                    [
                        "gitleaks",
                        "detect",
                        "--no-git",
                        "--no-banner",
                        "--redact",
                        "--exit-code",
                        "1",
                        "--source",
                        tmpdir,
                        "-c",
                        ".gitleaks.toml",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if mres.returncode == 1:
                    msg_finding = (mres.stdout or mres.stderr or "(no output)")[-1200:]
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as exc:  # noqa: BLE001 - surface the failure, never silently skip
        msg_finding = f"commit-message scan could not run: {exc}"

    if msg_finding:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            "gitleaks BLOCKED push: a COMMIT MESSAGE contains a secret or "
                            "PHI/PII value. Messages are published and cannot be edited "
                            "after push without rewriting history. Reword it (refer to a "
                            "commit by SHA, never by identifier) and amend.\n"
                            + msg_finding
                        ),
                    }
                }
            )
        )
    elif is_force:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "ask",
                        "permissionDecisionReason": (
                            "Force push detected. Force push is off by default here. "
                            "Confirm explicitly to proceed."
                        ),
                    }
                }
            )
        )
    else:
        print("{}")
