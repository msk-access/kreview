---
name: nbdev-patterns
description: nbdev cell directives, module export conventions, and testing patterns for notebook-first development.
---

# nbdev Patterns

## When to use this skill
- Creating or editing any notebook in `nbs/`
- Running `nbdev-export`, `nbdev-test`, or `nbdev-docs`
- Troubleshooting export or import issues

## Cell Directive Reference

| Directive | Effect |
|---|---|
| `#\| default_exp core` | Sets module export target for this notebook |
| `#\| export` | Exports the cell's code to the Python module |
| `#\| exporti` | Exports but marks as internal (not in `__all__`) |
| `#\| hide` | Hides cell from docs |
| `#\| test` | Marks cell as a test (run by `nbdev-test`) |

## Import Convention
```python
# In notebooks:
from kreview.core import *

# In exported code (explicit):
from kreview.core import LabelConfig, Paths, load_maf
```

## Common Errors
- `ModuleNotFoundError` → Run `nbdev-export` first
- `AttributeError: module has no attribute` → Cell is missing `#| export`
- Tests fail silently → Check cell has `#| test` directive
