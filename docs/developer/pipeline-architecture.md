# Pipeline Architecture

This document describes the decomposed pipeline architecture of `kreview`, how commands share code, and how to add a new pipeline stage.

---

## Overview

The `kreview` pipeline is decomposed into independent stages that can run either sequentially (`kreview run`) or in parallel (Nextflow / HPC):

```
Label → Extract ×N → Select → ┬─ Eval CPU ──┐
                               ├─ Eval GPU ──┤→ Eval Multimodal → Report
                               └─ Fuse ──────┘
```

Each stage has a corresponding CLI command:

| Stage | Command | Module |
|-------|---------|--------|
| Label | `kreview label` | `cli.py:label()` |
| Extract | `kreview extract` | `cli.py:extract()` |
| Select | `kreview select` | `cli_select.py:select()` |
| Eval CPU | `kreview eval cpu` | `cli_eval.py:eval_cpu()` |
| Eval GPU | `kreview eval gpu` | `cli_eval.py:eval_gpu()` |
| Fuse | `kreview fuse` | `cli.py:fuse()` |
| Eval Multimodal | `kreview eval multimodal` | `cli_eval.py:eval_multimodal()` |
| Report | `kreview report` | `cli.py:report()` |

---

## Shared Code Principle

**`kreview run` is an orchestrator** that calls the same shared functions as the standalone commands:

```python
# selection.py — used by BOTH kreview run AND kreview select
from kreview.selection import score_features, select_features, build_binary_target, _impute

# eval_engine.py — used by BOTH kreview run AND kreview eval cpu/gpu
from kreview.eval_engine import cpu_models, gpu_models
```

This guarantees that local runs and HPC runs produce **identical results** given the same inputs.

### Key Shared Modules

| Module | Functions | Used By |
|--------|-----------|---------|
| `selection.py` | `score_features()`, `select_features()`, `build_binary_target()` | `kreview run`, `kreview select` |
| `eval_engine.py` | `cpu_models()`, `gpu_models()`, `univariate_auc()`, `mutual_info_score()` | `kreview run`, `kreview eval cpu/gpu`, `selection.py` |
| `core.py` | `LABEL_META_COLS`, `fuse_matrices()` | All commands |

---

## Parallelism

After feature selection, three stages are **independent** and can run in parallel:

1. **Eval CPU** — per-evaluator LR, RF, XGBoost models
2. **Eval GPU** — per-evaluator TabPFN, TabICL models  
3. **Fuse** — join all selected matrices → `super_matrix.parquet`

All three converge at **Eval Multimodal**, which needs:
- OOF predictions from Eval CPU/GPU
- The super-matrix from Fuse

In `kreview run`, these stages execute sequentially but are logically independent. In Nextflow, they run truly in parallel.

---

## Data Flow

Each stage communicates through **parquet files**:

```
Extract:  → {evaluator}_matrix.parquet (full features)
Select:   → {evaluator}_matrix.parquet (selected features, overwrites)
          → {evaluator}_eval_stats.parquet (all feature scores)
          → {evaluator}_selection_qc.json (audit trail)
Eval:     → {evaluator}_model_results.json (AUCs, OOF probs)
          → {evaluator}_{model}_model.joblib (trained models)
Fuse:     → super_matrix.parquet (wide join on SAMPLE_ID)
```

---

## Adding a New Pipeline Stage

1. Create a shared library module (e.g., `kreview/new_stage.py`) with pure-logic functions
2. Create a CLI wrapper (e.g., `kreview/cli_new_stage.py`) that calls the shared functions
3. Register in `cli.py` via `app.command(name="new-stage")(new_stage_cmd)`
4. Update `kreview run` to call the shared functions at the appropriate point
5. Create a Nextflow process in `nextflow/modules/local/kreview/new_stage.nf`
6. Wire into `nextflow/workflows/kreview_eval.nf`
7. Add tests in `tests/test_new_stage.py`
8. Update this document and `pipeline-cli.md`
