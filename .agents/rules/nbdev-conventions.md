# nbdev Conventions for kreview

## Cell Directives
- `#| default_exp module.name` — MUST be the first cell of every notebook
- `#| export` — marks a cell for export to the Python module
- `#| test` — marks a cell as a test (run by `nbdev-test`)
- Exploration cells (no directive) are documentation — they are NOT exported

## Source of Truth
- **Notebooks in `nbs/`** are the source of truth. NEVER edit files in `kreview/` directly.
- After editing notebooks, run `nbdev-export` to regenerate Python modules.

## Import Pattern
- Use `from kreview.core import *` within notebooks (nbdev convention).
- In exported code, use explicit imports.

## Testing
- Tests live inside notebooks as `#| test` cells, NOT in a separate `tests/` directory.
- Run `nbdev-test --n_workers 4` to run all tests in parallel.
- Run `nbdev-test --path nbs/features/10_fsc_gene.ipynb` for a single notebook.

## Documentation
- Non-exported cells ARE the documentation. Include plots, explanations, examples.
- `nbdev-docs` generates a Quarto docs site from notebooks.
