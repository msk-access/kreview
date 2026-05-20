// ---------------------------------------------------------
// KREVIEW_EVAL_MULTIMODAL — Cross-evaluator multimodal evaluation
// ---------------------------------------------------------
// Runs `kreview eval multimodal` on the fused super-matrix using
// per-evaluator model results JSONs for stacking and ablation.
//
// This process runs AFTER both EVAL_CPU and EVAL_GPU complete.
//
// Inputs:  super_matrix.parquet, results_dir (with *_model_results.json)
// Outputs: multimodal_results.json
// ---------------------------------------------------------

process KREVIEW_EVAL_MULTIMODAL {
    tag "kreview-eval-multimodal"
    label 'process_high'

    input:
    path(super_matrix)
    path(results_dir)

    output:
    path "multimodal_output/multimodal_results.json", emit: multimodal_results

    script:
    def models_arg = params.multimodal_models ?: 'rf,xgb'
    def top_k_arg = params.multimodal_top_k ?: 50
    """
    set -euo pipefail

    mkdir -p multimodal_output

    PYTHONUNBUFFERED=1 kreview eval multimodal \\
        --super-matrix ${super_matrix} \\
        --results-dir ${results_dir} \\
        --models ${models_arg} \\
        --top-k ${top_k_arg} \\
        --output multimodal_output
    """
}
