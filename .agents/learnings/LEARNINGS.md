<!--
Work-order log for the learning loop. When a correction lands, append an entry here that
names the ROOT CAUSE and the exact PROMOTION TARGET (which file + what to change), so the
fix lands at the source, not just as a sticky note.

Attribution (name the cause before touching anything):
  skill-body       right skill fired, instructions wrong/stale  -> edit the SKILL.md body
  skill-trigger    wrong skill fired / right one silent          -> edit the description: triggers
  skill-permission wrong tool/model access                       -> edit allowed-tools / model
  environment      skill+trigger fine, failure external          -> log to ERRORS.md, no skill edit

Newest at top. Before promoting, grep REJECTED.md. Promote by delta edit, never a rewrite.
-->

## [LRN-20260711-001] project | Harness must ENFORCE the review fixes, not just document them
- **Status:** promoted
- **Cause:** skill-body
- **Summary:** The 0.0.24–0.0.28 release churn recurred because the guidance existed
  (`.agents/skills/nbdev-patterns` documents the idempotency + dedup rules) but nothing ran
  it. Standing context persuades; hooks enforce. Encoded the invariants as protected AGENTS.md
  rules + a PostToolUse nbdev-sync-guard hook.
- **Promotion target:** DONE: `AGENTS.md` load-bearing invariants (protected block) +
  `.claude/hooks/nbdev-sync-guard.py` + `.claude/settings.json`.
- **Related:** `.agents/memory/feedback-nbdev-source-of-truth.md`
