---
description: Step-by-step guide to add a new feature evaluator notebook to kreview
---

# /add-feature

## Steps

1. **Copy the template**:
   ```bash
   cp nbs/features/_template.ipynb nbs/features/27_new_feature.ipynb
   ```

2. **Implement the evaluator** in the notebook:
   - Set `#| default_exp features.new_feature`
   - Subclass `FeatureEvaluator`
   - Set `source_file` to the exact parquet suffix from §4 of the implementation plan
   - Implement `extract(df) -> dict[str, float]`

3. **Add exploration cells** (NOT exported):
   - Load a real sample's parquet file
   - Visualize the data (distributions, correlations)
   - Document what the feature measures biologically

4. **Add test cells** (`#| test`):
   - Verify `extract()` returns expected keys
   - Verify values are finite and within expected ranges

5. **Export and test**:
   ```bash
   nbdev-export
   nbdev-test --path nbs/features/27_new_feature.ipynb
   ```

## Guardrails
- ❌ Never load `.tsv.gz` or `.features.json` — parquet only
- ❌ Never edit files in `kreview/` directly — edit notebooks
- ❌ Never hardcode sample paths — use `load_sample_feature()` from core
- ❌ Never use mutation data for features — mutations are for labeling only
