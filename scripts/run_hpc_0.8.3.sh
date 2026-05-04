#!/bin/bash
# ============================================================================
#  kreview HPC runner — Full evaluation on v0.8.3 krewlyzer outputs
#  Queue: cmobic_cpu (IRIS)
#  Profile: slurm (Singularity + auto-tuned chunk_size=500, cv_folds=10)
# ============================================================================
set -euo pipefail

# --- Paths ---
NF_MAIN="/data1/shahr2/share/kreview/nextflow/main.nf"

CANCER_SS="/data1/shahr2/share/krewlyzer/0.8.3/access_12_245/samplesheet.csv"
HEALTHY_XS1_SS="/data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs1/samplesheet.csv"
HEALTHY_XS2_SS="/data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs2/samplesheet.csv"

CBIOPORTAL_DIR="/data1/core006/access/production/resources/cbioportal/current/msk_solid_heme"
KREWLYZER_DIR="/data1/shahr2/share/krewlyzer/0.8.3"

OUTDIR="/data1/shahr2/share/kreview/0.8.3_eval"

# --- Run ---
nextflow run "${NF_MAIN}" \
  --cancer_samplesheet      "${CANCER_SS}" \
  --healthy_xs1_samplesheet "${HEALTHY_XS1_SS}" \
  --healthy_xs2_samplesheet "${HEALTHY_XS2_SS}" \
  --cbioportal_dir          "${CBIOPORTAL_DIR}" \
  --krewlyzer_dir           "${KREWLYZER_DIR}" \
  --outdir                  "${OUTDIR}" \
  --compute_univariate_auc  \
  -profile slurm \
  -resume
