#!/usr/bin/env bash
# Nextflow stub smoke test — validates that the DAG parses, compiles and wires end to end.
#
# What this DOES cover:
#   - nextflow.config parses on the installed Nextflow (the #80 regression class)
#   - every profile resolves (stub/docker/slurm/iris)
#   - main.nf + all workflows + all 17 modules compile and their includes resolve
#   - channel wiring: every process' declared outputs satisfy its consumers' inputs
#   - both workflow branches (--workflow eval and --workflow label)
#
# What this does NOT cover: any real computation. Every process runs its `stub:` block,
# which only creates the files it declares. This is a wiring test, not a correctness test.
# A full nf-test harness is explicitly out of scope (maintainer decision, 2026-07-21).
#
# Usage:  bash scripts/nextflow_stub_test.sh [path-to-nextflow]
# Exit 0 if the DAG wires, 1 otherwise.

set -euo pipefail

NF="${1:-nextflow}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIN="$REPO/nextflow/main.nf"

if ! command -v "$NF" >/dev/null 2>&1 && [ ! -x "$NF" ]; then
    echo "ERROR: nextflow not found (tried '$NF'). Pass the path as \$1." >&2
    exit 1
fi

export NXF_ANSI_LOG=false
echo "== Nextflow: $("$NF" -v 2>&1)"

# --- 1. config parses, and every profile resolves ------------------------------------
# `nextflow config` is the cheapest gate and catches the #80 class (try/catch, ${HOME},
# manifest refs) before any process is scheduled.
for profile in "" stub docker slurm iris; do
    label="${profile:-<default>}"
    if [ -z "$profile" ]; then
        "$NF" config "$REPO/nextflow" >/dev/null
    else
        "$NF" config "$REPO/nextflow" -profile "$profile" >/dev/null
    fi
    echo "   config OK: profile=$label"
done

# --- 2. fixtures ---------------------------------------------------------------------
# Stub blocks never read their inputs, so these only need to exist with the right shape.
# Left in place on purpose rather than cleaned up in a trap: the repo forbids recursive
# deletes in committed code, and keeping the dir means a CI failure still has its logs.
# It is under $TMPDIR, so the OS/runner reclaims it.
WORK="$(mktemp -d)"
echo "== scratch: $WORK"
mkdir -p "$WORK/cbioportal" "$WORK/krewlyzer"
printf 'sample_id,bam\nP-0000000-T01-XS1,/dev/null\n' > "$WORK/cancer.csv"
cp "$WORK/cancer.csv" "$WORK/healthy_xs1.csv"
cp "$WORK/cancer.csv" "$WORK/healthy_xs2.csv"
touch "$WORK/krewlyzer/manifest.txt"

# Run from the scratch dir so Nextflow's `work/` and `.nextflow/` land there instead of
# littering the repo checkout (they are gitignored, but a clean tree keeps CI honest).
cd "$WORK"

common=(
    -stub-run -profile stub
    --cancer_samplesheet      "$WORK/cancer.csv"
    --healthy_xs1_samplesheet "$WORK/healthy_xs1.csv"
    --healthy_xs2_samplesheet "$WORK/healthy_xs2.csv"
    --cbioportal_dir          "$WORK/cbioportal"
)

# --- 3. eval workflow, every optional stage ON so all 17 processes are exercised ------
echo "== eval workflow (gpu + ablation + multimodal enabled)"
"$NF" -log "$WORK/eval.log" run "$MAIN" "${common[@]}" \
    --krewlyzer_dir "$WORK/krewlyzer" \
    --outdir "$WORK/out_eval" \
    --features "ATAC,FSC" \
    --run_gpu_eval true --run_ablation true --run_multimodal_eval true \
    --multimodal_gpu_models "tabpfn" \
    > "$WORK/eval.out" 2>&1 || { echo "FAILED — eval workflow:"; tail -40 "$WORK/eval.out"; exit 1; }

# --- 4. label-only workflow ----------------------------------------------------------
echo "== label workflow"
"$NF" -log "$WORK/label.log" run "$MAIN" "${common[@]}" \
    --workflow label \
    --outdir "$WORK/out_label" \
    > "$WORK/label.out" 2>&1 || { echo "FAILED — label workflow:"; tail -40 "$WORK/label.out"; exit 1; }

# --- 5. assertions -------------------------------------------------------------------
# Nextflow can exit 0 with zero work done, so assert the DAG actually ran rather than
# trusting the exit status alone (fail loud, not to a vacuous pass).
#
# These read execution_trace.txt rather than scraping stdout on purpose: the console format
# is version-specific (v26 prints "[SUCCESS] completed=N", v25 does not), so a stdout-based
# check reports a false failure on v25. The trace columns are stable across both.
#   column 4 = fully-qualified process name, column 7 = task status
fail=0

assert_trace () {  # $1=label  $2=outdir  $3=minimum distinct processes
    local label="$1" trace="$2/pipeline_info/execution_trace.txt" min="$3"

    if [ ! -f "$trace" ]; then
        echo "FAILED: $label produced no execution trace at $trace" >&2
        fail=1; return
    fi

    local bad
    bad="$(awk -F'\t' 'NR>1 && $7 != "COMPLETED" {print $4" -> "$7}' "$trace")"
    if [ -n "$bad" ]; then
        echo "FAILED: $label had tasks that did not complete:" >&2
        echo "$bad" | sed 's/^/    /' >&2
        fail=1
    fi

    local ran
    ran="$(awk -F'\t' 'NR>1 {n=split($4,a,":"); print a[n]}' "$trace" | sort -u | wc -l | tr -d ' ')"
    if [ "$ran" -lt "$min" ]; then
        echo "FAILED: $label ran $ran distinct processes, expected >= $min" >&2
        awk -F'\t' 'NR>1 {n=split($4,a,":"); print a[n]}' "$trace" | sort -u | sed 's/^/    ran: /' >&2
        fail=1
    else
        echo "   $label: $ran distinct processes, all COMPLETED"
    fi
}

# 17 = every process in nextflow/modules/local/kreview. If a process is added without being
# reachable from the DAG, this count stays put and the test fails — which is the point.
assert_trace "eval workflow"  "$WORK/out_eval"  17
assert_trace "label workflow" "$WORK/out_label" 1

# A stale `withName:` selector (one naming a deleted process) is silent config rot — it was
# how the removed Gen-1 bulk modules lingered in nextflow.config until #80. Treat it as fatal.
if grep -q 'no process matching config selector' "$WORK/eval.out"; then
    echo "FAILED: nextflow.config has a selector naming a process that does not exist:" >&2
    grep 'no process matching config selector' "$WORK/eval.out" | sed 's/^/    /' >&2
    fail=1
fi

# --- 6. #60 regression: the matrix<->best_subset pairing must not drop an evaluator -----
# A standalone channel-logic test (feeds 3 matrices + 2 best_subsets, asserts all 3 survive
# with a NO_BEST_SUBSET fallback). Guards against a revert to combine(by:0).
echo "== #60 drop-guard (channel join keeps evaluators)"
if "$NF" -log "$WORK/join.log" run "$REPO/scripts/test_nextflow_join_dropguard.nf" \
        > "$WORK/join.out" 2>&1; then
    echo "   $(grep -o 'PASS (#60):.*' "$WORK/join.out" | head -1)"
else
    echo "FAILED: #60 drop-guard — an evaluator was dropped or mis-paired:" >&2
    grep -iE 'DROP BUG|FALLBACK|PAIRING|assert' "$WORK/join.out" | head -3 | sed 's/^/    /' >&2
    fail=1
fi

# --- 7. #59 structural: GPU wrappers must keep the retry-then-degrade guard -------------
# Behaviour can't be exercised by a stub (stubs always succeed), so assert the guard is
# present: each GPU wrapper must fail (exit non-zero) before its retries are exhausted, so
# errorStrategy='retry' actually climbs the memory ladder instead of the old always-exit-0.
echo "== #59 structural (GPU wrappers engage the retry ladder)"
for m in eval_gpu_single ablate_gpu_single multimodal_single; do
    f="$REPO/nextflow/modules/local/kreview/$m.nf"
    if ! grep -q 'task.attempt.*-le.*task.maxRetries' "$f"; then
        echo "FAILED: $m.nf lost the '[ \${task.attempt} -le \${task.maxRetries} ]' retry guard (#59)" >&2
        fail=1
    fi
done
[ "$fail" -eq 0 ] && echo "   all GPU wrappers retain the retry-then-degrade guard"

[ "$fail" -eq 0 ] || exit 1

echo "OK: DAG wires end to end on $("$NF" -v 2>&1) (eval + label workflows; #59/#60 guards pass)."
