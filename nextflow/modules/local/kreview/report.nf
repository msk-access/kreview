// ---------------------------------------------------------
// KREVIEW_REPORT — Generate Quarto HTML dashboards from matrices
// ---------------------------------------------------------
// Re-renders dashboards from existing *_matrix.parquet files.
// Used in the multi-stage pipeline after extraction + eval
// to produce standalone HTML reports per evaluator.
//
// Inputs:  collected *_matrix.parquet files
// Outputs: HTML reports, static plots
// ---------------------------------------------------------

process KREVIEW_REPORT {
    tag "kreview-report"
    label 'process_medium'

    input:
    path(matrix_files)     // Collected from KREVIEW_EXTRACT outputs

    output:
    path "reports/*.html", emit: html_reports, optional: true
    path "reports/*.png" , emit: static_plots, optional: true

    script:
    def cvd_flag = params.cvd_safe ? "--cvd-safe" : ""
    """
    set -euo pipefail

    mkdir -p matrices reports

    # Stage matrices for report rendering
    for f in ${matrix_files}; do
        cp "\${f}" matrices/
    done

    PYTHONUNBUFFERED=1 kreview report \\
        --input-dir matrices \\
        --out-dir reports \\
        --shap-samples ${params.shap_samples ?: 500} \\
        --shap-features ${params.shap_features ?: 10} \\
        ${cvd_flag}
    """
}
