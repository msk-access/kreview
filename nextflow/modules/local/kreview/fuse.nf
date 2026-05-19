// ---------------------------------------------------------
// KREVIEW_FUSE — Fuse per-evaluator matrices into super_matrix
// ---------------------------------------------------------
// Collects all *_matrix.parquet files from KREVIEW_EXTRACT
// into a single directory, then runs `kreview fuse` to produce
// a unified super_matrix.parquet for multimodal evaluation.
//
// Inputs:  collected matrix parquet files from all evaluators
// Outputs: super_matrix.parquet
// ---------------------------------------------------------

process KREVIEW_FUSE {
    tag "kreview-fuse"
    label 'process_medium'

    input:
    path(matrix_files)     // Collected from all KREVIEW_EXTRACT outputs

    output:
    path "fused/super_matrix.parquet", emit: super_matrix

    script:
    """
    set -euo pipefail

    mkdir -p fused

    # Stage all matrices into the fuse directory
    for f in ${matrix_files}; do
        cp "\${f}" fused/
    done

    PYTHONUNBUFFERED=1 kreview fuse \\
        --output-dir fused \\
        --min-evaluators ${params.min_evaluators ?: 1} \\
        --output-name super_matrix.parquet
    """
}
