// ---------------------------------------------------------
// KREVIEW_MULTIMODAL_SINGLE — Train one model on stacking matrix
// ---------------------------------------------------------
// Stage 2 of decomposed multimodal pipeline.
// Trains a single model (rf, xgb, tabpfn_ft, etc.) on the
// stacking matrix and optionally the raw features matrix.
//
// Designed for scatter: Nextflow runs N instances in parallel,
// one per model.  CPU models run on process_medium, GPU models
// on process_gpu.
//
// Label selection:  Caller must set the label ('process_gpu'
//                   or 'process_medium') via NF's dynamic
//                   resource directive or by splitting CPU/GPU
//                   model channels in the workflow.
// ---------------------------------------------------------

process KREVIEW_MULTIMODAL_SINGLE_CPU {
    tag "multimodal-single-${model_name}"
    label 'process_medium'
    // #84: saveAs flattens the working-dir prefix (single_out/).
    publishDir "${params.outdir}/models/multimodal", mode: 'copy', saveAs: { fn -> file(fn).name }

    input:
    val(model_name)
    path(stacking_matrix)
    path(raw_features_matrix)
    path(prep_metadata)

    output:
    path "single_out/stacking_${model_name}_results.json", emit: single_result

    script:
    def cv_folds       = params.cv_folds ?: 5
    def raw_flag       = raw_features_matrix.name != 'NO_RAW_FEATURES' ? "--raw-features-matrix ${raw_features_matrix}" : ""
    def best_auc_flag  = ""
    """
    set -euo pipefail
    mkdir -p single_out

    # Extract best_single_auc from prep_metadata for delta computation.
    # Use grep instead of python3 — Singularity env strips container PATH,
    # so bare 'python3' may not be found (see v0.0.26 exit 127 bug).
    BEST_AUC=\$(grep -o '"best_single_auc": *[0-9.]*' ${prep_metadata} | grep -o '[0-9.]*\$' || echo "0.0")

    PYTHONUNBUFFERED=1 kreview eval multimodal single \\
        --stacking-matrix ${stacking_matrix} \\
        --model ${model_name} \\
        ${raw_flag} \\
        --cv-folds ${cv_folds} \\
        --best-single-auc \$BEST_AUC \\
        --seed ${params.seed ?: 42} \\
        ${params.deterministic ? '--deterministic' : '--no-deterministic'} \\
        --output single_out
    """

    // Stub: create declared outputs only — smoke-tests DAG wiring (see issue #80).
    stub:
    """
    mkdir -p single_out
    echo '{}' > single_out/stacking_${model_name}_results.json
    """
}


process KREVIEW_MULTIMODAL_SINGLE_GPU {
    tag "multimodal-single-gpu-${model_name}"
    label 'process_gpu'
    // #84: saveAs flattens the working-dir prefix (single_out/).
    publishDir "${params.outdir}/models/multimodal", mode: 'copy', saveAs: { fn -> file(fn).name }

    input:
    val(model_name)
    path(stacking_matrix)
    path(raw_features_matrix)
    path(prep_metadata)

    output:
    path "single_out/stacking_${model_name}_results.json", emit: single_result

    script:
    def cv_folds   = params.cv_folds ?: 5
    def device_arg = params.gpu_device ?: 'cuda'
    def epochs_arg = params.gpu_finetune_epochs ?: 50
    def lr_arg     = params.gpu_finetune_lr ?: '1e-5'
    def raw_flag   = raw_features_matrix.name != 'NO_RAW_FEATURES' ? "--raw-features-matrix ${raw_features_matrix}" : ""
    """
    set -euo pipefail
    mkdir -p single_out

    # Shared GPU env centralized in nextflow.config (params.gpu_env_setup, #58) — includes the
    # PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA-OOM guard.
    ${params.gpu_env_setup}
    ${params.tabpfn_token ? "export TABPFN_TOKEN=\"${params.tabpfn_token}\"" : "# TABPFN_TOKEN not set"}

    # Debug: verify environment is functional
    echo "=== KREVIEW_MULTIMODAL_SINGLE_GPU: ${model_name} ==="
    echo "Working dir: \$(pwd)"
    echo "kreview path: \$(which kreview 2>/dev/null || echo 'NOT FOUND')"
    ls -la ${stacking_matrix} ${prep_metadata} 2>/dev/null || echo "WARNING: input files missing"

    # Extract best_single_auc from prep_metadata for delta computation.
    # Use grep instead of python3 — Singularity env strips container PATH,
    # so bare 'python3' is not found in the GPU container (v0.0.26 exit 127 bug).
    BEST_AUC=\$(grep -o '"best_single_auc": *[0-9.]*' ${prep_metadata} | grep -o '[0-9.]*\$' || echo "0.0")

    # Run GPU eval — capture exit code instead of failing on error
    set +e
    PYTHONUNBUFFERED=1 kreview eval multimodal single \\
        --stacking-matrix ${stacking_matrix} \\
        --model ${model_name} \\
        ${raw_flag} \\
        --cv-folds ${cv_folds} \\
        --device ${device_arg} \\
        --finetune-epochs ${epochs_arg} \\
        --finetune-lr ${lr_arg} \\
        --best-single-auc \$BEST_AUC \\
        --seed ${params.seed ?: 42} \\
        ${params.deterministic ? '--deterministic' : '--no-deterministic'} \\
        --output single_out
    GPU_EXIT=\$?
    set -e

    # Failure handling — see #59 and the collect() deadlock history (commits 698c72e /
    # dcfe356). Fail loud first (exit non-zero) so errorStrategy='retry' climbs the
    # memory/partition ladder; degrade gracefully (error-JSON + exit 0) only once retries
    # are exhausted, keeping the channel-closing invariant so collect() cannot deadlock.
    if [ ! -f single_out/stacking_${model_name}_results.json ]; then
        if [ ${task.attempt} -le ${task.maxRetries} ]; then
            RETRY_CODE=\$GPU_EXIT; [ "\$RETRY_CODE" -eq 0 ] && RETRY_CODE=1
            echo "ERROR: Multimodal GPU eval failed for ${model_name} (exit=\$GPU_EXIT), attempt ${task.attempt}/\$((${task.maxRetries}+1)) — failing to trigger retry + memory/partition escalation" >&2
            exit \$RETRY_CODE
        fi
        echo "WARNING: Multimodal GPU eval failed for ${model_name} (exit=\$GPU_EXIT) after ${task.maxRetries} retries — emitting error JSON and continuing" >&2
        echo '{"model": "${model_name}", "error": "gpu_eval_failed", "exit_code": '\$GPU_EXIT'}' > "single_out/stacking_${model_name}_results.json"
    fi

    echo "=== KREVIEW_MULTIMODAL_SINGLE_GPU: ${model_name} DONE ==="
    """

    // Stub: create declared outputs only — smoke-tests DAG wiring (see issue #80).
    stub:
    """
    mkdir -p single_out
    echo '{}' > single_out/stacking_${model_name}_results.json
    """
}
