#!/bin/bash
#SBATCH --job-name=kreview_0.0.10
#SBATCH --partition=cmobic_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=3-00:00:00
#SBATCH --output=kreview_%j.log
#SBATCH --error=kreview_%j.err

# ============================================================================
# kreview Nextflow Pipeline - IRIS SLURM Submission Script (v0.0.10)
# ============================================================================
# Usage:  sbatch run_hpc_v0.0.10.sh
# Resume: sbatch run_hpc_v0.0.10.sh --resume
#
# Resource math (Multistage DAG):
#   - Head process: 4 CPUs + 16GB (Nextflow JVM orchestrator)
#   - Extraction (×N): 4 CPUs + 16GB (DuckDB streaming)
#   - CPU Eval: 8 CPUs + 64GB (LR, RF, XGB)
#   - GPU Eval: 4 CPUs + 32GB + 1 GPU (TabPFN, TabICL on gpushort queue)
#   - Multimodal: 8 CPUs + 64GB (Stacking Models)
#   - iris profile auto-tunes: chunk_size=auto, cv_folds=10, shap_samples=5000
# ============================================================================

set -euo pipefail

# Activate Nextflow environment
eval "$(micromamba shell hook --shell bash)"
micromamba activate nf-env

# Optional: pass -resume if provided as argument
RESUME_FLAG=""
if [[ "${1:-}" == "--resume" ]]; then
    RESUME_FLAG="-resume"
    echo ">>> Resuming previous run..."
fi

# --- Build manifest.txt listing all krewlyzer result directories ---
MANIFEST="${PWD}/manifest_v0.0.10.txt"
cat > "${MANIFEST}" <<EOF
/data1/shahr2/share/krewlyzer/0.8.3/access_12_245
/data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs1
/data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs2
EOF
echo ">>> Manifest written to ${MANIFEST}"

echo ">>> Starting kreview evaluation at $(date)"
echo ">>> Working directory: $PWD"

# Use the official v0.0.10 release from GitHub
nextflow run msk-access/kreview -r v0.0.10 \
  --cancer_samplesheet      /data1/shahr2/share/krewlyzer/0.8.3/access_12_245/samplesheet.csv \
  --healthy_xs1_samplesheet /data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs1/samplesheet.csv \
  --healthy_xs2_samplesheet /data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs2/samplesheet.csv \
  --cbioportal_dir          /data1/core006/access/production/resources/cbioportal/current/msk_solid_heme \
  --krewlyzer_dir           "${MANIFEST}" \
  --outdir                  /data1/shahr2/share/kreview/v0.0.10_eval \
  --pipeline_mode           multistage \
  --run_gpu_eval            true \
  --gpu_models              "tabpfn,tabicl" \
  --run_multimodal_eval     true \
  --top_percentile          10.0 \
  --ch_hotspot_maf          /data1/core006/access/production/resources/ch_hotspots/hotspots.maf \
  --compute_univariate_auc  \
  -profile iris \
  ${RESUME_FLAG}

echo ">>> kreview evaluation completed at $(date)"
