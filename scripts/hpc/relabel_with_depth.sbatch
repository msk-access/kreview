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
# Inputs default to the production values in scripts/run_hpc.sh — that script is the
# source of truth for where the cohort lives, and these are the same four resources it
# passes. Override any of them by exporting before sbatch:
#
#   KREVIEW_CANCER_SAMPLESHEET  KREVIEW_HEALTHY_XS1  KREVIEW_HEALTHY_XS2
#   KREVIEW_CBIOPORTAL_DIR      KREVIEW_KREWLYZER    KREVIEW_LABEL_OUT
#
#   sbatch scripts/hpc/relabel_with_depth.sbatch
#
# KREVIEW_KREWLYZER accepts either a directory or a manifest .txt listing one directory
# per line — `Paths.__post_init__` expands the manifest form, which is what the pipeline
# itself passes. Repeat-by-space is also supported here.
#
# Runs in the CPU container, so the kreview doing the labelling is the released one
# rather than whatever a login node happens to have.
set -euo pipefail

KRW_ROOT=/data1/shahr2/share/krewlyzer/0.8.3
CANCER_SS="${KREVIEW_CANCER_SAMPLESHEET:-$KRW_ROOT/access_12_245/samplesheet.csv}"
HEALTHY_XS1="${KREVIEW_HEALTHY_XS1:-$KRW_ROOT/healthy_controls/xs1/samplesheet.csv}"
HEALTHY_XS2="${KREVIEW_HEALTHY_XS2:-$KRW_ROOT/healthy_controls/xs2/samplesheet.csv}"
CBIO="${KREVIEW_CBIOPORTAL_DIR:-/data1/core006/access/production/resources/cbioportal/current/msk_solid_heme}"
KREWLYZER="${KREVIEW_KREWLYZER:-$KRW_ROOT/access_12_245 $KRW_ROOT/healthy_controls/xs1 $KRW_ROOT/healthy_controls/xs2}"
OUT="${KREVIEW_LABEL_OUT:-$PWD/relabel_depth/labels.parquet}"
CH_MAF="${KREVIEW_CH_HOTSPOT_MAF:-/data1/core006/cch/production/resources/cmo-ch/versions/v1.0/regions_of_interest/versions/v1.0/hotspot-list-ch-pd-v1.maf}"

VERSION="${KREVIEW_VERSION:-0.0.33}"
IMAGE="docker://ghcr.io/msk-access/kreview:v${VERSION}"
SIF_DIR="${KREVIEW_SIF_DIR:-$PWD/.singularity}"
mkdir -p logs "$SIF_DIR" "$(dirname "$OUT")"

# Fail here rather than 40 minutes in: every input is checked before the container
# starts, and a missing one is named.
for f in "$CANCER_SS" "$HEALTHY_XS1" "$HEALTHY_XS2"; do
    [ -f "$f" ] || { echo "FATAL: samplesheet not found: $f" >&2; exit 1; }
done
[ -d "$CBIO" ] || { echo "FATAL: cbioportal dir not found: $CBIO" >&2; exit 1; }

# --krewlyzer-dir is repeatable and also accepts a manifest .txt
KRW_ARGS=()
for d in $KREWLYZER; do
    [ -e "$d" ] || { echo "FATAL: krewlyzer path not found: $d" >&2; exit 1; }
    KRW_ARGS+=(--krewlyzer-dir "$d")
done

CH_ARGS=()
[ -f "$CH_MAF" ] && CH_ARGS+=(--ch-hotspot-maf "$CH_MAF") \
  || echo "NOTE: CH hotspot MAF not found, running without CH demotion: $CH_MAF"

echo "host      : $(hostname)"
echo "image     : $IMAGE"
echo "krewlyzer : ${KREWLYZER}"
echo "output    : $OUT"

export SINGULARITYENV_HOME="$PWD/.home"
export SINGULARITYENV_TMPDIR="$PWD/tmp"
export SINGULARITYENV_XDG_CACHE_HOME="$PWD/.cache"
export SINGULARITY_CACHEDIR="$SIF_DIR"
mkdir -p "$PWD/.home" "$PWD/tmp" "$PWD/.cache"

singularity exec \
    --bind "$PWD:$PWD" --pwd "$PWD" \
    "$IMAGE" \
    kreview label \
        --cancer-samplesheet "$CANCER_SS" \
        --healthy-xs1-samplesheet "$HEALTHY_XS1" \
        --healthy-xs2-samplesheet "$HEALTHY_XS2" \
        --cbioportal-dir "$CBIO" \
        "${KRW_ARGS[@]}" \
        "${CH_ARGS[@]}" \
        --output "$OUT"

# The whole point of the job: prove the column arrived and is populated.
echo "── verifying total_fragments_pf ──"
singularity exec --bind "$PWD:$PWD" --pwd "$PWD" "$IMAGE" python3 -c "
import pandas as pd, sys
lb = pd.read_parquet('${OUT}')
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
