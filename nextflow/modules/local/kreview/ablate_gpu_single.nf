// ---------------------------------------------------------
// KREVIEW_ABLATE_GPU_SINGLE — Per-evaluator GPU feature ablation
// ---------------------------------------------------------
// Runs nested CV feature group ablation using TabPFN/TabICL
// for a SINGLE evaluator matrix.
//
// Uses ZERO-SHOT inference only (no fine-tuning in inner loop).
// Output consumed by MERGE_ABLATION → EVAL_GPU_SINGLE.
//
// Container: Uses the GPU container via 'process_gpu' label.
// SLURM:     Routed to gpushort partition with --gres=gpu:1.
// ---------------------------------------------------------

process KREVIEW_ABLATE_GPU_SINGLE {
    tag "ablate-gpu-${matrix.baseName.replace('_matrix', '')}"
    label 'process_gpu'
    publishDir "${params.outdir}/ablation/gpu", mode: 'copy'

    input:
    path(matrix)       // Single selected *_matrix.parquet
    path(eval_stats)   // Matching *_eval_stats.parquet for feature capping

    output:
    path "*_ablation_gpu.json", emit: ablation_json

    script:
    def evaluator        = matrix.baseName.replace('_matrix', '')
    def models_arg       = params.gpu_models          ?: 'tabpfn,tabicl'
    def device_arg       = params.gpu_device          ?: 'cuda'
    def outer_folds      = params.cv_folds            ?: 5
    def inner_folds      = params.ablation_inner_folds ?: 3
    def max_gpu_feat_arg = params.max_gpu_features    ?: 150
    def seed             = params.seed                ?: 42
    """
    set -euo pipefail

    echo "=== KREVIEW_ABLATE_GPU_SINGLE: ${evaluator} ==="
    echo "Models: ${models_arg}, Device: ${device_arg}"

    # Singularity env setup (same as eval_gpu_single.nf)
    export HOME=\${PWD}/.home && mkdir -p \$HOME
    export TMPDIR=\${PWD}/tmp && mkdir -p \$TMPDIR
    export XDG_CACHE_HOME=\${PWD}/.cache && mkdir -p \$XDG_CACHE_HOME
    export HF_HOME=\${XDG_CACHE_HOME}/huggingface
    export TABPFN_DATA_DIR=\${XDG_CACHE_HOME}/tabpfn
    export TABPFN_MODEL_CACHE_DIR=\${XDG_CACHE_HOME}/tabpfn
    export TABPFN_NO_BROWSER=true
    export NUMBA_CACHE_DIR=\${PWD}/.numba_cache && mkdir -p \$NUMBA_CACHE_DIR
    ${params.tabpfn_token ? "export TABPFN_TOKEN=\"${params.tabpfn_token}\"" : "# TABPFN_TOKEN not set"}

    # Build eval-stats flag
    EVAL_STATS_FLAG=""
    if [ -f "${eval_stats}" ] && [ "${eval_stats}" != "NO_EVAL_STATS" ]; then
        EVAL_STATS_FLAG="--eval-stats ${eval_stats}"
    fi

    # Run GPU ablation — capture exit code for graceful failure
    set +e
    PYTHONUNBUFFERED=1 kreview eval ablate gpu \\
        --matrix ${matrix} \\
        --models ${models_arg} \\
        --device ${device_arg} \\
        --n-outer-folds ${outer_folds} \\
        --n-inner-folds ${inner_folds} \\
        --max-gpu-features ${max_gpu_feat_arg} \\
        --seed ${seed} \\
        \$EVAL_STATS_FLAG \\
        --output .
    GPU_EXIT=\$?
    set -e

    # Failure handling — see #59 and the collect() deadlock history (commits 698c72e /
    # dcfe356). Fail loud first (exit non-zero) so errorStrategy='retry' climbs the
    # memory/partition ladder; degrade gracefully (error-JSON + exit 0) only once retries
    # are exhausted, keeping the channel-closing invariant so collect() cannot deadlock.
    if ! ls *_ablation_gpu.json 1>/dev/null 2>&1; then
        if [ ${task.attempt} -le ${task.maxRetries} ]; then
            RETRY_CODE=\$GPU_EXIT; [ "\$RETRY_CODE" -eq 0 ] && RETRY_CODE=1
            echo "ERROR: GPU ablation failed for ${evaluator} (exit=\$GPU_EXIT), attempt ${task.attempt}/\$((${task.maxRetries}+1)) — failing to trigger retry + memory/partition escalation" >&2
            exit \$RETRY_CODE
        fi
        echo "WARNING: GPU ablation failed for ${evaluator} (exit=\$GPU_EXIT) after ${task.maxRetries} retries — emitting error JSON and continuing" >&2
        echo '{"evaluator": "${evaluator}", "error": "gpu_ablation_failed", "exit_code": '\$GPU_EXIT'}' \
            > "${evaluator}_ablation_gpu.json"
    fi

    echo "Output: \$(ls *_ablation_gpu.json)"
    echo "=== KREVIEW_ABLATE_GPU_SINGLE: ${evaluator} DONE ==="
    """

    // Stub: create declared outputs only — smoke-tests DAG wiring (see issue #80).
    stub:
    def evaluator = matrix.baseName.replace('_matrix', '')
    """
    echo '{}' > ${evaluator}_ablation_gpu.json
    """
}
