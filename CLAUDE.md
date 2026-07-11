# kreview — Claude Code entry

> Canonical standing context is `AGENTS.md` (cross-tool). This file imports it so
> Claude Code loads the same rules every other tool reads. Keep Claude-only notes
> below the import; put shared rules in `AGENTS.md`.

@AGENTS.md

## Claude-only notes

- **Skills** load from `.claude/skills/` (a symlink to `.agents/skills/`).
- **Hooks:** `.claude/settings.json` wires the `.claude/hooks/` guards
  (`block-rm-rf.py`, `block-env-edits.py`, `injection-guard.py`, `gitleaks-pre-push.py`,
  `nbdev-sync-guard.py`) plus current-time injection and policy-aware format-on-save.
- **Memory** auto-recall reads `.agents/memory/` (symlink it from the Claude project
  memory dir if you want built-in recall).

### graphify (knowledge graph, advisory)

A code knowledge graph lives in `graphify-out/`. For codebase questions, prefer
`graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"`
over raw grep — they return a scoped subgraph. Use `graphify-out/wiki/index.md` for broad
navigation and `GRAPH_REPORT.md` only for architecture review. After changing code, run
`graphify update .` (AST-only, no API cost) to keep it current. This is guidance, not an
enforced gate — use it when it helps, skip it for edits, unrelated files, and quick lookups.
