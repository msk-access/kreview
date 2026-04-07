---
description: One-time project initialization — scaffold nbdev project and install dependencies
---

# /init-project

## Steps

// turbo-all

1. Initialize the nbdev project:
   ```bash
   pip install nbdev quarto-cli typer plotly scikit-learn pandas pyarrow
   ```

2. Create the core notebooks:
   ```bash
   touch nbs/00_core.ipynb nbs/01_labels.ipynb nbs/02_stats.ipynb
   touch nbs/03_modeling.ipynb nbs/04_plots.ipynb nbs/05_report.ipynb
   ```

3. Create the feature notebook directory:
   ```bash
   mkdir -p nbs/features
   ```

4. Create all feature evaluator notebooks from template:
   ```bash
   for f in 10_fsc_gene 11_fsc_binlevel 12_fsc_regions 13_fsd 14_fsr \
            15_ocf_ontarget 16_ocf_offtarget 17_atac 18_tfbs 19_mds \
            20_mds_gene 20b_mds_exon 21_endmotif 22_breakpoint_motif \
            23_endmotif_1mer 24_wps_panel 25_wps_genomewide 26_wps_background; do
     cp nbs/features/_template.ipynb "nbs/features/${f}.ipynb"
   done
   ```

5. Run `nbdev-export` to verify scaffold:
   ```bash
   nbdev-export
   ```
