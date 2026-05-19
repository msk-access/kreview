// ---------------------------------------------------------
// KREVIEW_EVAL_GPU — Multimodal GPU evaluation on super-matrix
// ---------------------------------------------------------
// Runs `kreview eval-gpu` on the fused super_matrix.parquet.
// Currently supports XGBoost (CPU fallback). Future GPU backends
// (TabICLv2, Real-TabPFN) will be activated when dependencies
// are available in the container.
//
// This process is configured with GPU resource labels so SLURM
// schedules it on GPU-capable nodes when --model-type is set to
// tabicl or tabpfn.
//
// Inputs:  super_matrix.parquet
// Outputs: multimodal_results.json
// ---------------------------------------------------------

process KREVIEW_EVAL_GPU {
    tag "kreview-eval-gpu-${params.gpu_model_type ?: 'xgboost'}"
    label 'process_gpu'

    input:
    path(super_matrix)

    output:
    path "gpu_output/multimodal_results.json", emit: gpu_results

    script:
    """
    set -euo pipefail

    mkdir -p gpu_output

    PYTHONUNBUFFERED=1 kreview eval-gpu \\
        --super-matrix ${super_matrix} \\
        --model-type ${params.gpu_model_type ?: 'xgboost'} \\
        --cv-folds ${params.cv_folds ?: 5} \\
        --impute-strategy ${params.impute_strategy ?: 'median'} \\
        --output gpu_output
    """
}
