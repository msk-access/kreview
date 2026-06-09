// ---------------------------------------------------------
// KREVIEW_EVAL_CPU_SINGLE — Per-evaluator CPU model evaluation
// ---------------------------------------------------------
// Trains LR, RF, and XGBoost via stratified cross-validation
// for a SINGLE evaluator matrix.
//
// When best_subset is provided (from ablation), uses nested CV
// with per-fold feature subsets instead of all features.
//
// Used in multistage mode to scatter CPU evaluation across
// evaluators in parallel (×N jobs instead of 1 serial loop).
//
// Data flow (multistage):
//   KREVIEW_SELECT_SINGLE.out.matrix (per-evaluator)
//     → [optional: ABLATE → MERGE_ABLATION]
//     → KREVIEW_EVAL_CPU_SINGLE ×N (parallel)
//     → collect → KREVIEW_MULTIMODAL_PREP → ... → KREVIEW_MULTIMODAL_MERGE
// ---------------------------------------------------------

process KREVIEW_EVAL_CPU_SINGLE {
    tag "eval-cpu-${matrix.baseName.replace('_matrix', '')}"
    label 'process_medium'
    publishDir "${params.outdir}/models/cpu", mode: 'copy'

    input:
    path(matrix)        // Single selected *_matrix.parquet
    path(best_subset)   // *_best_subset.json (or NO_BEST_SUBSET sentinel)

    output:
    path "*_model_results.json", emit: json_stats
    path "*_model.joblib",       emit: joblib_models, optional: true

    script:
    def evaluator = matrix.baseName.replace('_matrix', '')
    def cv_folds  = params.cv_folds ?: 5
    def seed      = params.seed ?: 42
    """
    set -euo pipefail

    # Stage single matrix into directory (kreview eval cpu expects --matrices-dir)
    mkdir -p matrices
    cp ${matrix} matrices/

    echo "=== KREVIEW_EVAL_CPU_SINGLE: ${evaluator} ==="
    echo "Input: ${matrix}"

    # Build best-subset flag
    BEST_SUBSET_FLAG=""
    if [ -f "${best_subset}" ] && [ "${best_subset}" != "NO_BEST_SUBSET" ]; then
        BEST_SUBSET_FLAG="--best-subset ${best_subset}"
        echo "Using best_subset: ${best_subset}"
    fi

    PYTHONUNBUFFERED=1 kreview eval cpu \\
        --matrices-dir matrices \\
        --cv-folds ${cv_folds} \\
        --seed ${seed} \\
        ${params.deterministic ? '--deterministic' : '--no-deterministic'} \\
        \$BEST_SUBSET_FLAG \\
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
