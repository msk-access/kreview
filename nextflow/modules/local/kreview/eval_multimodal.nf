// ---------------------------------------------------------
// KREVIEW_EVAL_MULTIMODAL — Cross-evaluator multimodal evaluation
// ---------------------------------------------------------
// Runs `kreview eval multimodal` with per-evaluator model results
// JSONs for stacking and ablation.  Optionally uses the fused
// super_matrix.parquet for raw-feature evaluation.
//
// This process runs AFTER both EVAL_CPU and EVAL_GPU complete.
//
// Inputs:  super_matrix.parquet, results_dir (with *_model_results.json)
// Outputs: multimodal_results.json
// ---------------------------------------------------------

process KREVIEW_EVAL_MULTIMODAL {
    tag "kreview-eval-multimodal"
    label 'process_high'
    publishDir "${params.outdir}/models/multimodal", mode: 'copy'

    input:
    path(super_matrix)
    path(results_dir)

    output:
    path "multimodal_output/multimodal_results.json", emit: multimodal_results

    script:
    def models_arg = params.multimodal_models ?: 'rf,xgb'
    def top_k_arg = params.multimodal_top_k ?: 50
    def mm_sel = params.multimodal_selection ?: "mi"
    def cv_folds = params.cv_folds ?: 5
    // super_matrix is optional — passed if FUSE produced it
    def super_flag = super_matrix.name != 'NO_SUPER_MATRIX' ? "--super-matrix ${super_matrix}" : ""
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
        --top-k ${top_k_arg} \\
        --multimodal-selection ${mm_sel} \\
        --cv-folds ${cv_folds} \\
        --output multimodal_output
    """
}
