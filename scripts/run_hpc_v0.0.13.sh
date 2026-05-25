#!/bin/bash
#SBATCH --job-name=kreview_0.0.13
#SBATCH --partition=cmobic_short
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=2:59:00
#SBATCH --output=kreview_%j.log
#SBATCH --error=kreview_%j.err

# ============================================================================
# kreview Nextflow Pipeline - IRIS SLURM Submission Script (v0.0.13)
# ============================================================================
# Usage:  sbatch run_hpc_v0.0.13.sh
# Resume: sbatch run_hpc_v0.0.13.sh --resume
#
# Head job: cmobic_short (2.5h) — Nextflow JVM orchestrator only.
# Child jobs are submitted by Nextflow to cmobic_short with per-process
# resource specs defined in nextflow.config.
#
# What's new in v0.0.13:
#   - TabPFN v8.0.3 + TabICL v2.1 (new import paths)
#   - shapiq for GPU model SHAP values
#   - Unified joblib model persistence (CPU + GPU)
#   - Boruta-SHAP + MI reducer (>500 features → top percentile)
#   - --top-percentile replaces --top-k
#   - Multimodal GPU models via --multimodal-gpu-models
#   - SLURM hardening: cache='lenient', scratch=false on LABEL + GPU_SINGLE
#
# Resource math (Multistage DAG):
#   - Head process: 2 CPUs + 8GB (Nextflow JVM orchestrator — lightweight)
#   - Extraction (×N): 4 CPUs + 16GB, max 2.5h (DuckDB streaming)
#   - Select (×N):     4 CPUs + 16GB, max 2.5h (mRMR selection)
#   - CPU Eval (×N):   4 CPUs + 32GB, max 2.5h (LR, RF, XGB)
#   - GPU Eval (×N):   4 CPUs + 32GB + 1 GPU, max 2h (TabPFN on gpushort)
#   - Fuse:            2 CPUs + 16GB, max 2.5h (pandas join)
#   - Multimodal:      8 CPUs + 64GB + 1 GPU, max 2.5h (Stacking + GPU)
#   - Report:          4 CPUs + 32GB, max 2.5h (Quarto render)
#   - iris profile auto-tunes: chunk_size=auto, cv_folds=10, shap_samples=5000
#
# Typical wall-clock: ~30-45 min (all stages run in parallel within DAG).
# Head job has 2.5h budget — ample for scheduling delays and retries.
# ============================================================================

set -euo pipefail

# Activate Nextflow environment
eval "$(micromamba shell hook --shell bash)"
micromamba activate nf-env

# Optional: pass -resume if provided as argument (recommended)
RESUME_FLAG=""
if [[ "${1:-}" == "--resume" ]]; then
    RESUME_FLAG="-resume"
    echo ">>> Resuming previous run..."
fi

# --- Build manifest.txt listing all krewlyzer result directories ---
MANIFEST="${PWD}/manifest_v0.0.13.txt"
cat > "${MANIFEST}" <<EOF
/data1/shahr2/share/krewlyzer/0.8.3/access_12_245
/data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs1
/data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs2
EOF
echo ">>> Manifest written to ${MANIFEST}"

echo ">>> Starting kreview evaluation at $(date)"
echo ">>> Working directory: $PWD"

# Use local clone instead of GitHub remote (-r flag requires internet access
# on compute nodes, which IRIS SLURM workers do not have).
KREVIEW_REPO="/usersoftware/shahr2/github/kreview/nextflow/main.nf"

nextflow run "${KREVIEW_REPO}" \
  --cancer_samplesheet      /data1/shahr2/share/krewlyzer/0.8.3/access_12_245/samplesheet.csv \
  --healthy_xs1_samplesheet /data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs1/samplesheet.csv \
  --healthy_xs2_samplesheet /data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs2/samplesheet.csv \
  --cbioportal_dir          /data1/core006/access/production/resources/cbioportal/current/msk_solid_heme \
  --krewlyzer_dir           "${MANIFEST}" \
  --outdir                  /data1/shahr2/share/kreview/v0.0.13_eval \
  --pipeline_mode           multistage \
  --run_gpu_eval            true \
  --gpu_models              "tabpfn,tabicl" \
  --run_multimodal_eval     true \
  --multimodal_selection    boruta_shap \
  --multimodal_gpu_models   "tabpfn,tabicl" \
  --top_percentile          10.0 \
  --ch_hotspot_maf          /data1/core006/cch/production/resources/cmo-ch/versions/v1.0/regions_of_interest/versions/v1.0/hotspot-list-ch-pd-v1.maf \
  --compute_univariate_auc  \
  -profile iris \
  ${RESUME_FLAG}

echo ">>> kreview evaluation completed at $(date)"
