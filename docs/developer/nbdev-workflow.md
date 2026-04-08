# The nbdev Ecosystem

`kreview` is built completely using the notebook-first philosophy of **[nbdev](https://nbdev.fast.ai/)**. This allows our data scientists to natively write ML models, generate interactive graphs, and run statistical tables interactively while simultaneously publishing the codebase.

---

## ⛔ The Golden Rule

!!! danger "Never manually edit the `.py` files!"
    Every Python file inside `kreview/*.py` is **auto-generated**. If you modify `kreview/eval_engine.py` using VS Code, nano, or vi, your changes will be permanently evaporated and scrubbed during the next GitHub CI sync. 

**The Source of Truth** for the entire codebase resides exclusively inside the `nbs/` directory.

---

## 🛠️ Typical Development Flow

If you need to change logic in the dashboard generating code, here is how you do it:

1. Launch standard `jupyter lab`.
2. Open `nbs/05_report.ipynb`.
3. Locate the cell where the logic exists. (Notice the top of the cell has a `#| export` tag? This binds it to the output!).
4. Rewrite your logic and execute the cells dynamically.

When you are ready to publish:

```bash
# Deletes kreview/*.py, builds them perfectly from nbs/
nbdev_export

# Cleans your Jupyter Notebook cell metadata so GitHub doesn't explode
nbdev_clean 
```

### Fixing Accidental Python Edits (`nbdev_update`)
If you broke the Golden Rule and edited `kreview/core.py` directly, do NOT panic. 

You can run `nbdev_update` from the command line. This acts "in reverse", reading the source code from the raw `.py` module and aggressively injecting it BACK over the standard cells inside the corresponding Jupyter Notebook in `nbs/`!

### Installing Git Hooks
To force your environment to safely strip notebook metadata automatically prior to creating git commits, make sure you ran the hook generation string!
```bash
nbdev_install_hooks
```
