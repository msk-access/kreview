// ---------------------------------------------------------
// KREVIEW_REPORT_MULTIMODAL — Render multimodal stacking dashboard
// ---------------------------------------------------------
// Runs `kreview report --multimodal` to generate the cross-evaluator
// multimodal dashboard HTML from multimodal_results.json.
//
// This process runs AFTER KREVIEW_EVAL_MULTIMODAL completes.
//
// Inputs:  multimodal_results.json, super_matrix.parquet
// Outputs: *_dashboard.html report files
// ---------------------------------------------------------

process KREVIEW_REPORT_MULTIMODAL {
    tag "kreview-report-multimodal"
    label 'process_medium'
    publishDir "${params.outdir}/reports", mode: 'copy'

    input:
    path(multimodal_json)    // multimodal_results.json from KREVIEW_EVAL_MULTIMODAL
    path(super_matrix)       // super_matrix.parquet from KREVIEW_FUSE

    output:
    path "reports/*_dashboard.html", emit: html_reports, optional: true

    script:
    def cvd_flag = params.cvd_safe ? "--cvd-safe" : ""
    def shap_samples_arg = params.shap_samples ?: 500
    def shap_features_arg = params.shap_features ?: 10
    """
    set -euo pipefail
    mkdir -p matrices reports

    # Stage super-matrix and multimodal results into expected directory layout
    cp ${super_matrix} matrices/
    cp ${multimodal_json} matrices/multimodal_model_results.json

    PYTHONUNBUFFERED=1 kreview report \\
        --input-dir matrices \\
        --out-dir reports \\
        --multimodal \\
        --shap-samples ${shap_samples_arg} \\
        --shap-features ${shap_features_arg} \\
        ${cvd_flag}
    """
}
