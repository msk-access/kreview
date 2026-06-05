// ---------------------------------------------------------
// KREVIEW_MULTIMODAL_ABLATION — Leave-one-evaluator-out
// ---------------------------------------------------------
// Stage 3 of decomposed multimodal pipeline.
// Finds the best stacking model from partial result JSONs,
// then drops each evaluator's columns in turn to measure
// marginal contribution.
//
// Runs on CPU (uses the best stacking model which is always
// a CPU model — rf or xgb).
// ---------------------------------------------------------

process KREVIEW_MULTIMODAL_ABLATION {
    tag "multimodal-ablation"
    label 'process_medium'
    publishDir "${params.outdir}/models/multimodal", mode: 'copy'

    input:
    path(stacking_matrix)     // stacking_matrix.parquet from prep
    path(stacking_results)    // Collected stacking_*_results.json from single

    output:
    path "ablation_out/ablation_results.json", emit: ablation_results

    script:
    def cv_folds = params.cv_folds ?: 5
    """
    set -euo pipefail
    mkdir -p ablation_out stacking_results_dir

    # Stage stacking result JSONs into a directory
    for f in ${stacking_results}; do
        cp "\$f" stacking_results_dir/ 2>/dev/null || true
    done

    PYTHONUNBUFFERED=1 kreview eval multimodal ablation \\
        --stacking-matrix ${stacking_matrix} \\
        --stacking-results-dir stacking_results_dir \\
        --cv-folds ${cv_folds} \\
        --seed ${params.seed ?: 42} \\
        --output ablation_out
    """
}
