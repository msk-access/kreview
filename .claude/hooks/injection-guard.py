#!/usr/bin/env python3
"""
PreToolUse / Bash injection-and-exfil guard.

Defense-in-depth for an autonomous, broad-allow harness (Bash(*) + mcp__* +
auto-accepted edits + live web browsing). Targets ONLY the genuinely anomalous
shapes an injected instruction (web page, repo file, MCP response) would use to
exfiltrate secrets or run remote code. Everything else passes.

Design choices:
  - Returns 'ask' (human confirm), never a hard deny. Rare-but-legit cases
    (a known `curl ... | sh` installer) stay possible behind one confirm.
  - FAIL-OPEN: any parse/internal error allows the command. This is one layer,
    not the only one; a crashing guard that blocked all Bash would be worse
    than the narrow risk it covers. (block-rm-rf.py is the hard-deny layer.)
  - Tuned NOT to fire on the legitimate daily flow: a curl to your own gateway,
    sourcing a local env file, reading /proc/<pid>/environ, authenticated
    ssh/scp/rsync. Only a SECRET source + an OUTBOUND sink in the SAME command
    trips it.

SCRUB BEFORE SHARING: the only host-specific lines are the allow-heuristics in
section 2 (the `local` test). Replace the gateway/tailnet hints with your own,
or drop them — but keep the four detection shapes and the ask-not-deny posture.

Rollback: unregister from settings.json (or restore a settings.json backup)
and/or delete this file. No other state.
"""

import json
import re
import sys


def allow():
    sys.exit(0)


def ask(reason):
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


try:
    data = json.load(sys.stdin)
    cmd = data.get("tool_input", {}).get("command", "") or ""
except Exception:
    allow()  # fail-open: never wedge Bash on a parse error

low = cmd.lower()

# 1a. Remote content piped straight into a SHELL (the classic installer /
#     injection shape). curl ... | sh   |   wget ... | sudo bash
if re.search(r"\b(curl|wget|fetch)\b[^|]*\|\s*(sudo\s+)?" r"(sh|bash|zsh|fish)\b", low):
    ask(
        "Injection guard: remote content is piped into a shell "
        "(curl/wget | sh). Confirm this is a trusted installer and not an "
        "injected instruction."
    )

# 1b. Remote content piped into an INTERPRETER that executes it as code —
#     i.e. the interpreter is BARE (curl | python3) or reads stdin (… | python3 -).
#     NOT fired when a fixed program is given (-c/-e/-m flag or a script path):
#     there the piped bytes are DATA (json parse, etc.), which is the daily flow.
#     The negative lookahead excludes a lettered flag (-c/-m/-e/-p) or a filename
#     token immediately after the interpreter, while still catching bare `-`.
if re.search(
    r"\b(curl|wget|fetch)\b[^|]*\|\s*(sudo\s+)?"
    r"(python3?|node|ruby|perl)\b(?!\s+(-[A-Za-z]|[^\s|;&-]))",
    low,
):
    ask(
        "Injection guard: remote content is piped into a bare interpreter that "
        "would execute it as code (curl | python3 / | python3 -). Confirm this "
        "is intentional and not an injected instruction."
    )

# 2. ANTHROPIC_BASE_URL set inline to an EXTERNAL literal URL (an API-key
#    exfiltration vector). The legit flow — routing `claude -p` children through
#    your own LLM gateway — assigns it a config reference ($GATEWAY) or a
#    local/tailnet gateway URL, so those are allowed. Only a hardcoded NON-local
#    http(s) host is anomalous.
#    SCRUB: tune the `local` test to your own gateway naming.
m = re.search(r"\banthropic_base_url\s*=\s*['\"]?(https?://[^\s'\"]+)", low)
if m:
    host = re.sub(r"^https?://", "", m.group(1)).split("/")[0].split(":")[0]
    local = (
        host in ("localhost", "127.0.0.1", "0.0.0.0")
        or host.startswith("100.")  # tailscale CGNAT range
        or host.endswith(".ts.net")  # tailnet hostnames
        or "gateway" in host
    )  # your own gateway naming
    if not local:
        ask(
            "Injection guard: ANTHROPIC_BASE_URL is set inline to an external "
            "URL (API-key exfiltration vector). Confirm this is intentional "
            "and not an injected redirect."
        )

# 3. A high-value SECRET source AND an OUTBOUND network sink in the SAME command
#    (the exfiltration shape). Reading a secret alone is fine; piping it out is
#    not. .env / /environ are deliberately EXCLUDED here (too common in the
#    daily flow) — only private keys, the password store, and cloud creds count.
SECRET_STRICT = re.compile(
    r"(~/\.ssh/|/\.ssh/id_|id_(rsa|ed25519|ecdsa)\b|"
    r"\.password-store|(^|\s)pass\s+show\b|"
    r"\.aws/credentials|\.gcp|\.pem\b|\.p12\b|private[_-]?key)",
    re.I,
)
# Outbound sinks: anonymous exfil channels only. ssh/scp/sftp/rsync are
# EXCLUDED — they are authenticated, point-to-point ops you run daily.
NET_SINK = re.compile(
    r"\b(curl|wget|nc|ncat|netcat|telnet|"
    r"requests\.(post|put|get)|urllib|http\.client)\b",
    re.I,
)

if SECRET_STRICT.search(cmd) and NET_SINK.search(cmd):
    ask(
        "Injection guard: a private key / credential source and an outbound "
        "network command appear in the same command (exfiltration shape). "
        "Confirm this is intentional."
    )

allow()
