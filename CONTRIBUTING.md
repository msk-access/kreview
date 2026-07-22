# Contributing to kreview

Thank you for your interest in contributing! Please see our full [Contributing Guide](https://msk-access.github.io/kreview/developer/contributing/) for detailed instructions on:

- Git branching model and commit conventions
- Development setup and the nbdev workflow
- Pull request checklist and code review standards
- Pre-commit hooks and linting configuration

## Quick Start

```bash
git clone https://github.com/msk-access/kreview.git
cd kreview
pip install -e '.[dev,test,docs]'
nbdev-install-hooks
pre-commit install
```

## Important

**Never edit generated `.py` files directly.** All code changes must be made in the Jupyter
notebooks under `nbs/`, then exported with `nbdev-export`. After exporting, `nbdev-export` must
produce **zero git diff** (idempotency) — CI enforces this.

**Exception — standalone modules** (hand-maintained, no notebook; edit them directly and exclude
them from `nbdev-update`/`nbdev.sync`): `kreview/scoreboard.py`, `kreview/feature_cards.py`,
`kreview/reproducibility.py`.

## No PHI or secrets — this repository is PUBLIC

`kreview` is public and also commits an agent memory store (`.agents/memory/`) and learning
logs (`.agents/learnings/`). Anything written there is published.

**Never commit** patient identifiers (MSK DMP ids, MRN, SSN, DOB), clinical data, credentials,
or personal absolute paths. In documentation, use the placeholder sample id
`P-0000000-T01-XS1` — any other 7-digit DMP id is treated as real and blocked.

This is enforced, not just requested:

- `.gitleaks.toml` defines the secret + PHI rules (auto-discovered by gitleaks).
- `.claude/hooks/gitleaks-pre-push.py` **denies** `git push` on a finding.
- CI re-scans every push/PR, so the rule holds even without local hooks.
- `bash scripts/check_phi_guard.sh` verifies the rules still fire (run it after editing rules).

## Agent harness setup (optional, for Claude Code / Codex / Cursor users)

```bash
brew install gitleaks          # required by the pre-push secret/PHI hook
bash scripts/check_phi_guard.sh   # confirm the guard is healthy
```

Claude Code loads `AGENTS.md`/`CLAUDE.md`, `.claude/hooks/`, and `.claude/skills/`
automatically (it will ask once to trust the project hooks). To have agent memory read and
write the shared in-repo store, point your local memory directory at it:

```bash
ln -s "$PWD/.agents/memory" ~/.claude/projects/<encoded-repo-path>/memory
```
