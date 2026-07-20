---
name: project-kreview-harness
description: "kreview uses a gbcms-style cross-tool agent harness — AGENTS.md canonical, CLAUDE.md imports it, .claude/skills symlinks .agents/skills, enforcement hooks in .claude/hooks."
metadata:
  type: project
---

kreview has a cross-tool agent harness (built 2026-07-11), modeled on the `msk-access/gbcms`
layout. Paths below are repo-relative.

- **`AGENTS.md`** — canonical standing context (read by Codex, Antigravity, Cursor, Copilot).
  Holds protected load-bearing invariants that encode the review's root causes.
- **`CLAUDE.md`** — thin wrapper: `@AGENTS.md` import + Claude-only notes. Not a symlink.
- **`.claude/skills` → `../.agents/skills`** (symlink) — the 10 existing skills. A session
  started *before* the symlink existed cannot invoke them via the Skill tool; a fresh
  session discovers them normally.
- **`.claude/hooks/`** — block-rm-rf, block-env-edits, injection-guard, gitleaks-pre-push
  (from claudelicious) + `nbdev-sync-guard.py` (kreview-specific PostToolUse reminder).
- **`.claude/settings.json`** — wires the hooks + time injection + read-only allowlist. The
  old graphify `hook-guard` PreToolUse gate was REMOVED (it nagged on every Bash/Read);
  graphify is now advisory guidance in CLAUDE.md.
- **`.agents/learnings/`** (LEARNINGS/ERRORS/REJECTED) + **`.agents/memory/`** (four-tier) +
  **`CONTINUITY.md`** — the learning loop and durable state.

**This memory store is committed to a PUBLIC repo.** Never write PHI, patient identifiers,
or personal paths here — see the hard default in [[AGENTS]] and the enforced rules in
`.gitleaks.toml`.

Review findings and the hardening issue drafts live in `.agents/HARDENING_ISSUES.md`; the
issues are tracked on GitHub under milestone `v0.0.29 hardening` (tracking issue + children).
Harness reference: `github.com/BioInfo/claudelicious`.
