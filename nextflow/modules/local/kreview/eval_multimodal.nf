// ---------------------------------------------------------
// KREVIEW_EVAL_MULTIMODAL — Cross-evaluator multimodal evaluation
// ---------------------------------------------------------
// Runs `kreview eval multimodal run` with per-evaluator model results
// JSONs for stacking and ablation.  Optionally uses the fused
// super_matrix.parquet for raw-feature evaluation.
//
// This process runs AFTER both EVAL_CPU and EVAL_GPU complete.
// When GPU models are requested, runs on GPU node for TabPFN/TabICL.
//
// Inputs:  super_matrix.parquet, results_dir (with *_model_results.json)
// Outputs: multimodal_results.json
// ---------------------------------------------------------

process KREVIEW_EVAL_MULTIMODAL {
    tag "kreview-eval-multimodal"
    label 'process_gpu'
    publishDir "${params.outdir}/models/multimodal", mode: 'copy'

    input:
    path(super_matrix)
    path(results_dir)

    output:
    path "multimodal_output/multimodal_results.json", emit: multimodal_json

    script:
    def models_arg     = params.multimodal_models ?: 'rf,xgb'
    def gpu_models_arg = params.multimodal_gpu_models ?: ''
    def top_pct_arg    = params.multimodal_top_percentile ?: 10.0
    def mm_sel         = params.multimodal_selection ?: "mi"
    def cv_folds       = params.cv_folds ?: 5
    def device_arg     = params.gpu_device ?: 'cuda'
    def epochs_arg     = params.gpu_finetune_epochs ?: 50
    def lr_arg         = params.gpu_finetune_lr ?: '1e-5'
    // super_matrix is optional — passed if FUSE produced it
    def super_flag = super_matrix.name != 'NO_SUPER_MATRIX' ? "--super-matrix ${super_matrix}" : ""
    // GPU models flag — only add if non-empty
    def gpu_flag = gpu_models_arg ? "--gpu-models ${gpu_models_arg}" : ""
    """
    set -euo pipefail

    mkdir -p multimodal_output

    # Singularity --no-home makes \$HOME read-only.
    # Redirect all cache/data dirs to the writable work directory.
    export HOME=\${PWD}/.home && mkdir -p \$HOME
    export TMPDIR=\${PWD}/tmp && mkdir -p \$TMPDIR
    export XDG_CACHE_HOME=\${PWD}/.cache && mkdir -p \$XDG_CACHE_HOME
    export HF_HOME=\${XDG_CACHE_HOME}/huggingface
    export TABPFN_DATA_DIR=\${XDG_CACHE_HOME}/tabpfn
    export TABPFN_MODEL_CACHE_DIR=\${XDG_CACHE_HOME}/tabpfn
    export TABPFN_NO_BROWSER=true
    export NUMBA_CACHE_DIR=\${PWD}/.numba_cache && mkdir -p \$NUMBA_CACHE_DIR
    ${params.tabpfn_token ? "export TABPFN_TOKEN=\"${params.tabpfn_token}\"" : "# TABPFN_TOKEN not set"}

    # All *_model_results.json and *_gpu_model_results.json files are
    # symlinked in the work directory by Nextflow's collect() operator.
    # Python load_all_model_results() natively handles both naming patterns.

    PYTHONUNBUFFERED=1 kreview eval multimodal run \\
        --results-dir . \\
        ${super_flag} \\
        --models ${models_arg} \\
        ${gpu_flag} \\
        --device ${device_arg} \\
        --finetune-epochs ${epochs_arg} \\
        --finetune-lr ${lr_arg} \\
        --top-percentile ${top_pct_arg} \\
        --multimodal-selection ${mm_sel} \\
        --cv-folds ${cv_folds} \\
        --seed ${params.seed ?: 42} \\
        ${params.deterministic ? '--deterministic' : '--no-deterministic'} \\
        --output multimodal_output
    """
}
