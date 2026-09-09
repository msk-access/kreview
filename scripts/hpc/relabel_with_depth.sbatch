#!/bin/bash
#SBATCH --job-name=kreview-relabel-depth
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#
# CONTINUITY item D2 — re-label with true per-sample depth.
#
# Why this job exists: `total_fragments_pf` is populated from krewlyzer QC files via
# `kreview label --krewlyzer-dir`. A v0.0.32 output directory predates that column
# (#122), so the depth question behind F7 cannot be settled from existing outputs —
# the depth re-checks on #121 fall back to coverage-derived proxies. This is also the
# cheapest job on the register and four items sit behind it: CH subtraction, the
# chart-review protocol, and the blinded chart review itself.
#
# Everything below is supplied at submit time; nothing cluster-specific is committed.
#
#   export KREVIEW_CANCER_SAMPLESHEET=/path/to/cancer_samplesheet.csv
#   export KREVIEW_CBIOPORTAL_DIR=/path/to/cbioportal
#   export KREVIEW_KREWLYZER_DIRS="/path/to/krewlyzer_run1 /path/to/krewlyzer_run2"
#   export KREVIEW_HEALTHY_XS=/path/to/healthy_samplesheet.csv     # optional
#   export KREVIEW_LABEL_OUT=/path/to/relabel_out
#   sbatch scripts/hpc/relabel_with_depth.sbatch
#
# Runs in the CPU container, so the shipped kreview version is the one that labelled
# production — no local environment drift.
set -euo pipefail

: "${KREVIEW_CANCER_SAMPLESHEET:?set KREVIEW_CANCER_SAMPLESHEET}"
: "${KREVIEW_CBIOPORTAL_DIR:?set KREVIEW_CBIOPORTAL_DIR}"
: "${KREVIEW_KREWLYZER_DIRS:?set KREVIEW_KREWLYZER_DIRS (space-separated)}"
: "${KREVIEW_LABEL_OUT:?set KREVIEW_LABEL_OUT}"

VERSION="${KREVIEW_VERSION:-0.0.33}"
IMAGE="docker://ghcr.io/msk-access/kreview:v${VERSION}"
SIF_DIR="${KREVIEW_SIF_DIR:-$PWD/.singularity}"
mkdir -p logs "$SIF_DIR" "$(dirname "$KREVIEW_LABEL_OUT")"

# one --krewlyzer-dir per directory; the flag is repeatable
KRW_ARGS=()
for d in $KREVIEW_KREWLYZER_DIRS; do
    [ -d "$d" ] || { echo "FATAL: krewlyzer dir not found: $d" >&2; exit 1; }
    KRW_ARGS+=(--krewlyzer-dir "$d")
done

HEALTHY_ARGS=()
[ -n "${KREVIEW_HEALTHY_XS:-}" ] && HEALTHY_ARGS+=(--healthy-xs "$KREVIEW_HEALTHY_XS")

echo "host    : $(hostname)"
echo "image   : $IMAGE"
echo "krewlyzer dirs: ${KREVIEW_KREWLYZER_DIRS}"
echo "output  : $KREVIEW_LABEL_OUT"

export SINGULARITYENV_HOME="$PWD/.home"
export SINGULARITYENV_TMPDIR="$PWD/tmp"
export SINGULARITYENV_XDG_CACHE_HOME="$PWD/.cache"
export SINGULARITY_CACHEDIR="$SIF_DIR"
mkdir -p "$PWD/.home" "$PWD/tmp" "$PWD/.cache"

singularity exec \
    --bind "$PWD:$PWD" --pwd "$PWD" \
    "$IMAGE" \
    kreview label \
        --cancer-samplesheet "$KREVIEW_CANCER_SAMPLESHEET" \
        --cbioportal-dir "$KREVIEW_CBIOPORTAL_DIR" \
        "${KRW_ARGS[@]}" \
        "${HEALTHY_ARGS[@]}" \
        --output "$KREVIEW_LABEL_OUT"

# The whole point of the job: prove the column arrived and is populated.
echo "── verifying total_fragments_pf ──"
singularity exec --bind "$PWD:$PWD" --pwd "$PWD" "$IMAGE" python3 -c "
import pandas as pd, sys
lb = pd.read_parquet('${KREVIEW_LABEL_OUT}')
if 'total_fragments_pf' not in lb.columns:
    sys.exit('FATAL: total_fragments_pf absent — --krewlyzer-dir did not take effect')
n, ok = len(lb), int(lb['total_fragments_pf'].notna().sum())
print(f'  {ok:,}/{n:,} samples have depth ({ok/n:.1%})')
print(f'  median {lb[\"total_fragments_pf\"].median():,.0f}')
if ok == 0:
    sys.exit('FATAL: column present but entirely NaN — QC files did not match sample ids')
if ok < 0.8 * n:
    print('  WARNING: under 80% coverage — check that every krewlyzer run was passed')
"
