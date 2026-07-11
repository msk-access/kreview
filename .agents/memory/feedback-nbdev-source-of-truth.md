---
name: feedback-nbdev-source-of-truth
description: nbdev — notebooks are canonical; never leave kreview/*.py edited without syncing back; end with a zero-diff export.
metadata:
  type: feedback
---

`kreview/*.py` are generated from `nbs/*.ipynb`. Never hand-edit a generated module and
consider the job done. Edit the notebook then `nbdev_export`, or edit the `.py` then
`nbdev_update`; always end with `nbdev_export` producing **zero git diff** and regenerate
`_modidx.py`. Standalone exceptions: `scoreboard.py`, `feature_cards.py`.

**Why:** As of the 2026-07 review the committed `.py` tree was black-formatted against
`black_formatting = False`, so a fresh `nbdev_export` reverted every module; `_modidx.py` was
~7 weeks stale (39 missing symbols incl. a whole class). This drift is invisible to CI (no
export-sync check) and ships stale code to PyPI and the containers.

**How to apply:**
1. Resolve the formatting policy first (set `black_formatting = True` in `settings.ini` so
   export emits black-clean `.py`), then re-export once to normalize the tree.
2. After any change touching `.py` or `.ipynb`: `nbdev_export` twice — the second run must
   produce no git diff. Run `nbdev.doclinks` to refresh `_modidx.py`.
3. Add `nbdev_export --check` (or export + `git diff --exit-code`) to CI so drift fails a PR.

See [[feedback-parallel-paths-one-impl]].
