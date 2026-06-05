// ---------------------------------------------------------
// KREVIEW_MULTIMODAL_PREP — Build stacking + raw matrices
// ---------------------------------------------------------
// Stage 1 of decomposed multimodal pipeline.
// Reads per-evaluator *_model_results.json and builds:
//   - stacking_matrix.parquet (OOF probabilities)
//   - raw_features_matrix.parquet (optional, if super_matrix provided)
//   - prep_metadata.json (evaluator summary)
//
// Runs on CPU.  No GPU required.
// ---------------------------------------------------------

process KREVIEW_MULTIMODAL_PREP {
    tag "multimodal-prep"
    label 'process_medium'
    publishDir "${params.outdir}/models/multimodal", mode: 'copy'

    input:
    path(results_jsons)   // Collected *_model_results.json files
    path(super_matrix)    // super_matrix.parquet or NO_SUPER_MATRIX sentinel

    output:
    path "prep_out/stacking_matrix.parquet",       emit: stacking_matrix
    path "prep_out/raw_features_matrix.parquet",   emit: raw_features_matrix, optional: true
    path "prep_out/prep_metadata.json",            emit: prep_metadata

    script:
    def mm_sel      = params.multimodal_selection ?: "mi"
    def top_pct_arg = params.multimodal_top_percentile ?: 10.0
    def super_flag  = super_matrix.name != 'NO_SUPER_MATRIX' ? "--super-matrix ${super_matrix}" : ""
    """
    set -euo pipefail
    mkdir -p prep_out results_dir

    # Stage JSON files into a directory for kreview
    for f in ${results_jsons}; do
        cp "\$f" results_dir/ 2>/dev/null || true
    done

    PYTHONUNBUFFERED=1 kreview eval multimodal prep \\
        --results-dir results_dir \\
        ${super_flag} \\
        --multimodal-selection ${mm_sel} \\
        --top-percentile ${top_pct_arg} \\
        --seed ${params.seed ?: 42} \\
        --output prep_out
    """
}
