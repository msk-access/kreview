// ---------------------------------------------------------
// KREVIEW_EVAL_CPU_SINGLE — Per-evaluator CPU model evaluation
// ---------------------------------------------------------
// Trains LR, RF, and XGBoost via stratified cross-validation
// for a SINGLE evaluator matrix.
//
// Used in multistage mode to scatter CPU evaluation across
// evaluators in parallel (×N jobs instead of 1 serial loop).
//
// Data flow (multistage):
//   KREVIEW_SELECT_SINGLE.out.matrix (per-evaluator)
//     → KREVIEW_EVAL_CPU_SINGLE ×N (parallel)
//     → collect → KREVIEW_EVAL_MULTIMODAL
// ---------------------------------------------------------

process KREVIEW_EVAL_CPU_SINGLE {
    tag "eval-cpu-${matrix.baseName.replace('_matrix', '')}"
    label 'process_medium'
    publishDir "${params.outdir}/models/cpu", mode: 'copy'

    input:
    path(matrix)  // Single selected *_matrix.parquet

    output:
    path "*_model_results.json", emit: json_stats

    script:
    def evaluator = matrix.baseName.replace('_matrix', '')
    def cv_folds  = params.cv_folds ?: 5
    """
    set -euo pipefail

    # Stage single matrix into directory (kreview eval cpu expects --matrices-dir)
    mkdir -p matrices
    cp ${matrix} matrices/

    echo "=== KREVIEW_EVAL_CPU_SINGLE: ${evaluator} ==="
    echo "Input: ${matrix}"

    PYTHONUNBUFFERED=1 kreview eval cpu \\
        --matrices-dir matrices \\
        --cv-folds ${cv_folds} \\
        --seed ${params.seed ?: 42} \\
        ${params.deterministic ? '--deterministic' : '--no-deterministic'} \\
        --output .

    # Verify output exists (fail loudly, not silently)
    if [ ! -f *_model_results.json ]; then
        echo "ERROR: No model results produced for ${evaluator}" >&2
        exit 1
    fi

    echo "Output: \$(ls *_model_results.json)"
    echo "=== KREVIEW_EVAL_CPU_SINGLE: ${evaluator} DONE ==="
    """
}
