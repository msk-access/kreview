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
    publishDir "${params.outdir}/models/multimodal", mode: 'copy'

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
}


process KREVIEW_MULTIMODAL_SINGLE_GPU {
    tag "multimodal-single-gpu-${model_name}"
    label 'process_gpu'
    publishDir "${params.outdir}/models/multimodal", mode: 'copy'

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

    # Singularity --no-home workarounds
    export HOME=\${PWD}/.home && mkdir -p \$HOME
    export TMPDIR=\${PWD}/tmp && mkdir -p \$TMPDIR
    export XDG_CACHE_HOME=\${PWD}/.cache && mkdir -p \$XDG_CACHE_HOME
    export HF_HOME=\${XDG_CACHE_HOME}/huggingface
    export TABPFN_DATA_DIR=\${XDG_CACHE_HOME}/tabpfn
    export TABPFN_MODEL_CACHE_DIR=\${XDG_CACHE_HOME}/tabpfn
    export TABPFN_NO_BROWSER=true
    export NUMBA_CACHE_DIR=\${PWD}/.numba_cache && mkdir -p \$NUMBA_CACHE_DIR
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

    # Always produce output JSON — even on total failure.
    if [ ! -f single_out/stacking_${model_name}_results.json ]; then
        echo "WARNING: Multimodal GPU eval failed for ${model_name} (exit=\$GPU_EXIT), emitting error JSON" >&2
        echo '{"model": "${model_name}", "error": "gpu_eval_failed", "exit_code": '\$GPU_EXIT'}' > "single_out/stacking_${model_name}_results.json"
    fi

    echo "=== KREVIEW_MULTIMODAL_SINGLE_GPU: ${model_name} DONE ==="
    """
}
