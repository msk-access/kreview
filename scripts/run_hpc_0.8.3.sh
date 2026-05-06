#!/bin/bash
#SBATCH --job-name=kreview
#SBATCH --partition=cmobic_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=3-00:00:00
#SBATCH --output=kreview_%j.log
#SBATCH --error=kreview_%j.err

# ============================================================================
# kreview Nextflow Pipeline - IRIS SLURM Submission Script
# ============================================================================
# Usage:  sbatch run_hpc_0.8.3.sh
# Resume: sbatch run_hpc_0.8.3.sh --resume
#
# Resource math:
#   - Head process: 4 CPUs + 16GB (Nextflow JVM orchestrating evaluators)
#   - Evaluator job: 8 CPUs + 64GB (process_high, submitted by NF to SLURM)
#   - iris profile auto-tunes: chunk_size=500, cv_folds=10, shap_samples=5000
#   - Multi-partition: cmobic_short(3h), cpu_short(2h), cmobic_cpu(3h+)
#   - Estimated: single monolithic job, ~2-6h depending on feature count
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
MANIFEST="${PWD}/manifest.txt"
cat > "${MANIFEST}" <<EOF
/data1/shahr2/share/krewlyzer/0.8.3/access_12_245
/data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs1
/data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs2
EOF
echo ">>> Manifest written to ${MANIFEST}"

echo ">>> Starting kreview evaluation at $(date)"
echo ">>> Working directory: $PWD"

nextflow run /usersoftware/shahr2/github/kreview/nextflow/main.nf \
  --cancer_samplesheet      /data1/shahr2/share/krewlyzer/0.8.3/access_12_245/samplesheet.csv \
  --healthy_xs1_samplesheet /data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs1/samplesheet.csv \
  --healthy_xs2_samplesheet /data1/shahr2/share/krewlyzer/0.8.3/healthy_controls/xs2/samplesheet.csv \
  --cbioportal_dir          /data1/core006/access/production/resources/cbioportal/current/msk_solid_heme \
  --krewlyzer_dir           "${MANIFEST}" \
  --outdir                  /data1/shahr2/share/kreview/0.8.3_eval \
  --compute_univariate_auc  \
  -profile iris \
  ${RESUME_FLAG}

echo ">>> kreview evaluation completed at $(date)"
