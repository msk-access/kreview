---
description: Generate ctDNA labels without feature evaluation
---

# /run-labels

## Steps

1. **Generate labels**:
   ```bash
   kreview label \
     --cancer-samplesheet /path/to/access_12_245/samplesheet.csv \
     --healthy-xs1-samplesheet /path/to/healthy_controls/xs1/samplesheet.csv \
     --healthy-xs2-samplesheet /path/to/healthy_controls/xs2/samplesheet.csv \
     --cbioportal-dir /Users/shahr2/Documents/Github/msk-impact/msk_solid_heme/ \
     --output labels.parquet \
     --min-vaf 0.01 \
     --min-variants 1
   ```

2. **Verify label counts**:
   ```python
   import pandas as pd
   labels = pd.read_parquet("labels.parquet")
   print(labels["label"].value_counts())
   # Expected: ~40% True/Possible ctDNA+, ~40-50% Possible ctDNA−, 68 Healthy
   ```

3. **Spot-check** 5 True ctDNA+ samples on cBioPortal web UI
