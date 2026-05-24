// ---------------------------------------------------------
// KREVIEW_SELECT — Feature scoring + mRMR/hybrid-union selection
// ---------------------------------------------------------
// Reads per-evaluator *_matrix.parquet files (from KREVIEW_EXTRACT),
// scores every feature (univariate AUC + mutual information), and
// applies feature selection (mRMR by default, or top N% AUC ∪ top N% MI).
//
// Produces selected matrices with only the top features, plus
// per-evaluator scoring stats and selection QC metadata.
//
// Data flow:
//   KREVIEW_EXTRACT.out.matrices → KREVIEW_SELECT → selected matrices
//     → KREVIEW_EVAL_CPU  (parallel)
//     → KREVIEW_EVAL_GPU  (parallel)
//     → KREVIEW_FUSE      (parallel)
// ---------------------------------------------------------

process KREVIEW_SELECT {
    tag "kreview-select"
    label 'process_high'

    input:
    path(matrix_files)

    output:
    path "selected/*_matrix.parquet",        emit: matrices
    path "selected/*_eval_stats.parquet",    emit: eval_stats
    path "selected/*_selection_qc.json",     emit: selection_qc

    script:
    def top_pct  = params.top_percentile ?: 10
    def cv_folds = params.cv_folds       ?: 5
    def strategy = params.strategy       ?: "mrmr"
    def impute   = params.impute_strategy ?: "median"
    def auc_flag = params.compute_univariate_auc ? '' : '--no-compute-univariate-auc'
    """
    set -euo pipefail

    mkdir -p matrices selected

    # Stage all input matrices into a single directory
    for f in ${matrix_files}; do
        cp "\${f}" matrices/
    done

    echo "=== KREVIEW_SELECT ==="
    echo "Input matrices: \$(ls matrices/*_matrix.parquet | wc -l)"

    PYTHONUNBUFFERED=1 kreview select \
        --matrices-dir matrices \
        --top-percentile ${top_pct} \
        --strategy ${strategy} \
        --cv-folds ${cv_folds} \
        --impute-strategy ${impute} \
        ${auc_flag} \
        --output selected

    echo "Output matrices: \$(ls selected/*_matrix.parquet | wc -l)"
    echo "=== KREVIEW_SELECT DONE ==="
    """
}
