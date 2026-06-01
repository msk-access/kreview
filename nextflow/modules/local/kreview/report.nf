// ---------------------------------------------------------
// KREVIEW_REPORT — Generate Quarto HTML dashboards
// ---------------------------------------------------------
// Renders per-evaluator HTML dashboards from *_matrix.parquet
// and *_model_results.json files. Requires BOTH to render
// complete dashboards with ROC curves, SHAP, and model metrics.
//
// In multistage mode, this process starts after ALL CPU/GPU
// eval jobs complete and the SCOREBOARD has been built.
//
// Inputs:  collected matrices, JSONs, eval_stats, selection_qc,
//          joblib models, and the scoreboard parquet.
// Outputs: HTML reports, static plots
// ---------------------------------------------------------

process KREVIEW_REPORT {
    tag "kreview-report"
    label 'process_medium'
    publishDir "${params.outdir}/reports", mode: 'copy'

    input:
    path(matrix_files)     // Collected from KREVIEW_SELECT_SINGLE outputs
    path(model_results)    // Collected from KREVIEW_EVAL_CPU/GPU outputs
    path(eval_stats)       // Collected from KREVIEW_SELECT_SINGLE
    path(selection_qc)     // Collected from KREVIEW_SELECT_SINGLE
    path(joblib_files)     // Collected from KREVIEW_EVAL_CPU + GPU
    path(scoreboard_file)  // From KREVIEW_SCOREBOARD

    output:
    path "reports/*.html", emit: html_reports, optional: true
    path "reports/*.png" , emit: static_plots, optional: true

    script:
    def cvd_flag = params.cvd_safe ? "--cvd-safe" : ""
    """
    set -euo pipefail

    mkdir -p matrices reports

    # Stage ALL files into one flat directory (report expects co-located files)
    for f in ${matrix_files}; do cp "\${f}" matrices/; done
    for f in ${model_results}; do cp "\${f}" matrices/ 2>/dev/null || true; done
    for f in ${eval_stats}; do cp "\${f}" matrices/ 2>/dev/null || true; done
    for f in ${selection_qc}; do cp "\${f}" matrices/ 2>/dev/null || true; done
    for f in ${joblib_files}; do cp "\${f}" matrices/ 2>/dev/null || true; done
    cp ${scoreboard_file} matrices/ 2>/dev/null || true

    PYTHONUNBUFFERED=1 kreview report \\
        --input-dir matrices \\
        --out-dir reports \\
        --shap-samples ${params.shap_samples ?: 500} \\
        --shap-features ${params.shap_features ?: 10} \\
        ${cvd_flag}
    """
}
