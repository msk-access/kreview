// ---------------------------------------------------------
// KREVIEW_REPORT — Generate Quarto HTML dashboards
// ---------------------------------------------------------
// Renders per-evaluator HTML dashboards from *_matrix.parquet
// and *_model_results.json files. Requires BOTH to render
// complete dashboards with ROC curves, SHAP, and model metrics.
//
// In multistage mode, this process starts after ALL CPU/GPU
// eval jobs complete, running in parallel with FUSE + MULTIMODAL.
//
// Inputs:  collected *_matrix.parquet + *_model_results.json files
// Outputs: HTML reports, static plots
// ---------------------------------------------------------

process KREVIEW_REPORT {
    tag "kreview-report"
    label 'process_medium'
    publishDir "${params.outdir}/reports", mode: 'copy'

    input:
    path(matrix_files)     // Collected from KREVIEW_SELECT_SINGLE outputs
    path(model_results)    // Collected from KREVIEW_EVAL_CPU/GPU outputs

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

    # Stage model results alongside matrices
    for f in ${model_results}; do
        cp "\${f}" matrices/ 2>/dev/null || true
    done

    PYTHONUNBUFFERED=1 kreview report \\
        --input-dir matrices \\
        --out-dir reports \\
        --shap-samples ${params.shap_samples ?: 500} \\
        --shap-features ${params.shap_features ?: 10} \\
        ${cvd_flag}
    """
}
