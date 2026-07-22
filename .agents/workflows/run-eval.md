---
description: Run full feature evaluation pipeline — labels + extraction + stats + models + reports
---

# /run-eval

## Steps

1. **Run the full pipeline** (Nextflow multistage — the only run path):
   ```bash
   nextflow run nextflow/main.nf \
     --cancer_samplesheet /path/to/samplesheet.csv \
     --healthy_xs1_samplesheet /path/to/xs1/samplesheet.csv \
     --healthy_xs2_samplesheet /path/to/xs2/samplesheet.csv \
     --cbioportal_dir /path/to/msk_solid_heme/ \
     --krewlyzer_dir /path/to/results/ \
     --outdir output/ \
     --min_vaf 0.01 \
     --min_variants 1 \
     -profile docker      # or iris/slurm on HPC
   ```

2. **Restrict to a subset of evaluators**:
   ```bash
   nextflow run nextflow/main.nf --features FSC_gene --min_vaf 0.01 -profile docker
   ```

3. **Debug one stage outside the DAG** (stage subcommands still exist):
   ```bash
   kreview label --cancer-samplesheet ... --output output/
   kreview extract --features FSC_gene --output output/
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
