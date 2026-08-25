#!/bin/bash
#SBATCH --job-name=kreview-gpu-research
#SBATCH --partition=gpushort
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#
# Run one research script inside the kreview GPU container.
#
# For research analyses that need a GPU but are NOT part of the Nextflow DAG — the
# tabicl_ft leakage arm (CONTINUITY item D1) is the reason this exists. Stage work
# inside the DAG belongs in a module, not here.
#
#   sbatch scripts/hpc/run_gpu_research.sbatch \
#       scripts/research_analyses/tabicl_grouped_cv.py --n 8000 --epochs 50
#
# Overridable by exporting before sbatch:
#   KREVIEW_VERSION   container tag           (default: the installed kreview version)
#   KREVIEW_OUTDIR    pipeline output dir     (default: $PWD/results)
#   KREVIEW_SIF_DIR   singularity image cache (default: $PWD/.singularity)
#
# Partition/time mirror `withLabel: process_gpu` in nextflow/nextflow.config: gpushort
# caps at 2h. Longer runs need `--partition=gpu --time=06:00:00` on the sbatch line.
set -euo pipefail

SCRIPT="${1:?usage: sbatch run_gpu_research.sbatch <script.py> [args...]}"
shift || true

VERSION="${KREVIEW_VERSION:-$(python3 -c 'import kreview; print(kreview.__version__)' 2>/dev/null || echo latest)}"
OUTDIR="${KREVIEW_OUTDIR:-$PWD/results}"
SIF_DIR="${KREVIEW_SIF_DIR:-$PWD/.singularity}"
IMAGE="docker://ghcr.io/msk-access/kreview:v${VERSION}-gpu"

mkdir -p logs "$SIF_DIR"

echo "host      : $(hostname)"
echo "image     : $IMAGE"
echo "script    : $SCRIPT $*"
echo "outdir    : $OUTDIR"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || {
    echo "FATAL: no GPU visible — the job landed on a node without one, or --gres was dropped" >&2
    exit 1
}

# The same hardening the pipeline applies to every GPU process (params.gpu_env_setup):
# /home is read-only on the compute nodes, so every cache has to be redirected into the
# job directory or the libraries fail at import time rather than at use time.
export SINGULARITYENV_HOME="$PWD/.home"
export SINGULARITYENV_TMPDIR="$PWD/tmp"
export SINGULARITYENV_XDG_CACHE_HOME="$PWD/.cache"
export SINGULARITYENV_IPYTHONDIR="$PWD/.ipython"
export SINGULARITYENV_HF_HOME="$PWD/.cache/huggingface"
export SINGULARITYENV_NUMBA_CACHE_DIR="$PWD/.numba_cache"
export SINGULARITYENV_PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"
export SINGULARITY_CACHEDIR="$SIF_DIR"
mkdir -p "$PWD/.home" "$PWD/tmp" "$PWD/.cache" "$PWD/.ipython" "$PWD/.numba_cache"

# --nv exposes the driver; without it torch sees no CUDA device and silently uses CPU,
# which for these workloads means a job that times out instead of one that fails.
singularity exec --nv \
    --bind "$OUTDIR:$OUTDIR" \
    --bind "$PWD:$PWD" \
    --pwd "$PWD" \
    "$IMAGE" \
    python3 -u "$SCRIPT" "$@"
