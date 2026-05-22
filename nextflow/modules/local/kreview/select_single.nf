// ---------------------------------------------------------
// KREVIEW_SELECT_SINGLE — Per-evaluator feature selection
// ---------------------------------------------------------
// Scores and selects features for a SINGLE evaluator matrix.
// Used in multistage mode to scatter feature selection across
// evaluators in parallel (×N jobs instead of 1 serial loop).
//
// Data flow (multistage):
//   KREVIEW_EXTRACT.out.matrices.flatten()
//     → KREVIEW_SELECT_SINGLE ×N (parallel)
//     → KREVIEW_EVAL_CPU_SINGLE ×N
//     → KREVIEW_EVAL_GPU_SINGLE ×N
// ---------------------------------------------------------

process KREVIEW_SELECT_SINGLE {
    tag "select-${matrix.baseName.replace('_matrix', '')}"
    label 'process_medium'

    input:
    path(matrix)  // Single *_matrix.parquet file

    output:
    path "selected/*_matrix.parquet",     emit: matrix
    path "selected/*_eval_stats.parquet", emit: eval_stats
    path "selected/*_selection_qc.json",  emit: selection_qc

    script:
    def evaluator = matrix.baseName.replace('_matrix', '')
    def top_pct   = params.top_percentile ?: 10
    def cv_folds  = params.cv_folds       ?: 5
    def impute    = params.impute_strategy ?: "median"
    def auc_flag  = params.compute_univariate_auc ? '' : '--no-compute-univariate-auc'
    """
    set -euo pipefail

    mkdir -p matrices selected

    # Stage single matrix into matrices/ directory (kreview select expects a dir)
    cp ${matrix} matrices/

    echo "=== KREVIEW_SELECT_SINGLE: ${evaluator} ==="
    echo "Input: ${matrix}"

    PYTHONUNBUFFERED=1 kreview select \\
        --matrices-dir matrices \\
        --top-percentile ${top_pct} \\
        --cv-folds ${cv_folds} \\
        --impute-strategy ${impute} \\
        ${auc_flag} \\
        --output selected

    # Verify outputs exist (fail loudly, not silently)
    if [ ! -f selected/*_matrix.parquet ]; then
        echo "ERROR: No selected matrix produced for ${evaluator}" >&2
        exit 1
    fi

    echo "Output: \$(ls selected/*_matrix.parquet)"
    echo "=== KREVIEW_SELECT_SINGLE: ${evaluator} DONE ==="
    """
}
