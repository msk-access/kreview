// ---------------------------------------------------------
// KREVIEW_EVAL_CPU — Per-evaluator CPU model evaluation
// ---------------------------------------------------------
// Uses `kreview eval cpu --matrices-dir` on pre-extracted
// matrices from KREVIEW_EXTRACT. This avoids re-running
// the labeling and extraction steps.
//
// Trains LR, RF, and XGBoost via stratified cross-validation.
//
// Inputs:  collected *_matrix.parquet files from KREVIEW_EXTRACT
// Outputs: *_model_results.json per evaluator
// ---------------------------------------------------------

process KREVIEW_EVAL_CPU {
    tag "kreview-eval-cpu"
    label 'process_high'

    input:
    path(matrix_files)     // Collected *_matrix.parquet from KREVIEW_EXTRACT

    output:
    path "cpu_output/*_model_results.json", emit: json_stats

    script:
    def cv_folds = params.cv_folds ?: 5
    def resume_flag = params.resume ? '--resume' : ''
    """
    set -euo pipefail

    # Stage matrices into a single directory for --matrices-dir
    mkdir -p matrices cpu_output
    for f in ${matrix_files}; do
        cp "\${f}" matrices/
    done

    PYTHONUNBUFFERED=1 kreview eval cpu \\
        --matrices-dir matrices \\
        --cv-folds ${cv_folds} \\
        ${resume_flag} \\
        --output cpu_output
    """
}
