---
description: Run full feature evaluation pipeline — labels + extraction + stats + models + reports
---

# /run-eval

## Steps

1. **Run the full pipeline**:
   ```bash
   kreview run \
     --cancer-samplesheet /path/to/samplesheet.csv \
     --healthy-xs1-samplesheet /path/to/xs1/samplesheet.csv \
     --healthy-xs2-samplesheet /path/to/xs2/samplesheet.csv \
     --cbioportal-dir /path/to/msk_solid_heme/ \
     --krewlyzer-dir /path/to/results/ \
     --output output/ \
     --min-vaf 0.01 \
     --min-variants 1
   ```

2. **Run a single feature** (for debugging):
   ```bash
   kreview run --features FSC_gene --min-vaf 0.01
   ```

3. **Run by tier**:
   ```bash
   kreview run --tier 1  # Tier 1 only (FSC, FSD, FSR)
   ```

4. **Check scoreboard**:
   ```python
   import pandas as pd
   sb = pd.read_parquet("output/scoreboard/scoreboard_combined__all.parquet")
   print(sb.sort_values("auc_lr_true_vs_healthy", ascending=False).head(20))
   ```

5. **Re-generate reports** (if needed):
   ```bash
   kreview report --input-dir output/
   ```
