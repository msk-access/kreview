// ---------------------------------------------------------
// KREVIEW_EVAL_MULTIMODAL — Cross-evaluator multimodal evaluation
// ---------------------------------------------------------
// Runs `kreview eval multimodal` with per-evaluator model results
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
    def finetune_flag  = params.gpu_no_finetune ? '--no-finetune' : ''
    def epochs_arg     = params.gpu_finetune_epochs ?: 30
    def lr_arg         = params.gpu_finetune_lr ?: '1e-5'
    // super_matrix is optional — passed if FUSE produced it
    def super_flag = super_matrix.name != 'NO_SUPER_MATRIX' ? "--super-matrix ${super_matrix}" : ""
    // GPU models flag — only add if non-empty
    def gpu_flag = gpu_models_arg ? "--gpu-models ${gpu_models_arg}" : ""
    """
    set -euo pipefail

    mkdir -p multimodal_output

    # Stage JSON results into a flat directory
    mkdir -p results_flat
    for f in ${results_dir}/*_model_results.json; do
        cp "\${f}" results_flat/ 2>/dev/null || true
    done

    PYTHONUNBUFFERED=1 kreview eval multimodal \\
        --results-dir results_flat \\
        ${super_flag} \\
        --models ${models_arg} \\
        ${gpu_flag} \\
        --device ${device_arg} \\
        ${finetune_flag} \\
        --finetune-epochs ${epochs_arg} \\
        --finetune-lr ${lr_arg} \\
        --top-percentile ${top_pct_arg} \\
        --multimodal-selection ${mm_sel} \\
        --cv-folds ${cv_folds} \\
        --output multimodal_output
    """
}
