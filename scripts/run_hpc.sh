#!/bin/bash
#SBATCH --job-name=kreview_0.0.15
#SBATCH --partition=cmobic_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=24:00:00
#SBATCH --output=kreview_%j.log
#SBATCH --error=kreview_%j.err

# ============================================================================
# kreview Nextflow Pipeline - IRIS SLURM Submission Script (v0.0.15)
# ============================================================================
# Usage:  sbatch run_hpc.sh
# Resume: sbatch run_hpc.sh --resume
#
# Head job: cmobic_cpu (24h) — Nextflow JVM orchestrator only.
# Child jobs are submitted by Nextflow to cmobic_short/gpu partitions
# with per-process resource specs defined in nextflow.config.
#
# TabPFN Authentication:
#   TabPFN requires a one-time license acceptance + API key.
#   1. Register at https://ux.priorlabs.ai
#   2. Accept the license on the Licenses tab
#   3. Copy your API key from https://ux.priorlabs.ai/account
#   4. Set TABPFN_TOKEN below (or leave blank to skip TabPFN)
#
# Resource math (Multistage DAG — all stages run in parallel within DAG):
#   - Head process: 4 CPUs + 16GB (Nextflow JVM orchestrator — lightweight)
#   - Extraction (×N): 4 CPUs + 24GB×attempt, maxRetries=5 (DuckDB streaming)
#   - Select (×N):     4 CPUs + 16GB, max 2.5h (mRMR selection)
#   - CPU Eval (×N):   4 CPUs + 32GB, max 2.5h (LR, RF, XGB)
#   - GPU Eval (×N):   4 CPUs + 32GB + 1 GPU, max 2h (TabPFN, TabICL)
#   - Fuse:            2 CPUs + 16GB, max 2.5h (pandas join)
#   - Scoreboard:      4 CPUs + 16GB (scoreboard aggregation)
#   - Multimodal:      8 CPUs + 64GB + 1 GPU, max 2.5h (Stacking + GPU)
#   - Report:          4 CPUs + 32GB, max 2.5h (Quarto render)
#   - iris profile auto-tunes: chunk_size=auto, cv_folds=10, shap_samples=5000
#
# Typical wall-clock: ~1-2h (extraction/eval stages scatter in parallel).
# Head job has 24h budget — ample for GPU queue waits and retries.
# ============================================================================

set -euo pipefail

# ── TabPFN API Token ──────────────────────────────────────────────────────────
# Set your token here, or leave empty to run with TabICL only.
TABPFN_TOKEN="${TABPFN_TOKEN:-}"

# Activate Nextflow environment
eval "$(micromamba shell hook --shell bash)"
micromamba activate nf-env

# ── Singularity Cache ─────────────────────────────────────────────────────────
# Override defaults ($HOME/.singularity) to avoid quota issues and use fast
# local storage. CACHEDIR stores pulled .img files; TMPDIR is used during build.
export SINGULARITY_CACHEDIR="$PWD/.singularity_cache"
export SINGULARITY_TMPDIR="$PWD/.singularity_tmp"
mkdir -p "${SINGULARITY_CACHEDIR}" "${SINGULARITY_TMPDIR}"

# Optional: pass -resume if provided as argument (recommended)
RESUME_FLAG=""
if [[ "${1:-}" == "--resume" ]]; then
    RESUME_FLAG="-resume"
    echo ">>> Resuming previous run..."
fi

# --- Build manifest.txt listing all krewlyzer result directories ---
MANIFEST="${PWD}/manifest_v0.0.15.txt"
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

# Build TabPFN token flag (only pass if set)
TABPFN_FLAG=""
if [[ -n "${TABPFN_TOKEN}" ]]; then
    TABPFN_FLAG="--tabpfn_token ${TABPFN_TOKEN}"
    echo ">>> TabPFN token provided — TabPFN + TabICL models enabled"
else
    echo ">>> No TabPFN token — running TabICL only (set TABPFN_TOKEN to enable)"
fi

nextflow run "${KREVIEW_REPO}" \
  --cancer_samplesheet      /data1/shahr2/share/krewlyzer/0.8.3/access_12_245/samplesheet.csv \
  --healthy_xs1_samplesheet /data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs1/samplesheet.csv \
  --healthy_xs2_samplesheet /data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs2/samplesheet.csv \
  --cbioportal_dir          /data1/core006/access/production/resources/cbioportal/current/msk_solid_heme \
  --krewlyzer_dir           "${MANIFEST}" \
  --outdir                  $PWD/v0.0.15_eval \
  --pipeline_mode           multistage \
  --run_gpu_eval            true \
  --gpu_models              "tabpfn,tabicl" \
  --run_multimodal_eval     true \
  --multimodal_selection    boruta_shap \
  --multimodal_gpu_models   "tabpfn,tabicl" \
  --top_percentile          10.0 \
  --ch_hotspot_maf          /data1/core006/cch/production/resources/cmo-ch/versions/v1.0/regions_of_interest/versions/v1.0/hotspot-list-ch-pd-v1.maf \
  --compute_univariate_auc  \
  --seed                    42 \
  --no-deterministic        \
  ${TABPFN_FLAG} \
  -profile iris \
  ${RESUME_FLAG}

echo ">>> kreview evaluation completed at $(date)"
