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
    publishDir "${params.outdir}", mode: 'copy'  // output glob includes reports/ prefix

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
    // #98: the manifest names what rendered and what failed (with per-failure Quarto debug
    // logs), so a partially-published reports/ dir is loud, not silently incomplete.
    path "reports/report_manifest.json", emit: manifest,    optional: true
    path "reports/*_render.log",         emit: render_logs, optional: true

    script:
    def cvd_flag = params.cvd_safe ? "--cvd-safe" : ""
    """
    set -euo pipefail

    # Shared report/Quarto env centralized in nextflow.config (params.report_env_setup, #58) —
    # now also sets HOME/TMPDIR/MPLCONFIGDIR for read-only-/home HPC nodes (home writes +
    # matplotlib config dir), which were previously missing here.
    ${params.report_env_setup}

    mkdir -p matrices reports .ipython

    # Stage ALL files into one flat directory (report expects co-located files)
    for f in ${matrix_files}; do cp "\${f}" matrices/; done
    for f in ${model_results}; do cp "\${f}" matrices/ 2>/dev/null || true; done
    for f in ${eval_stats}; do cp "\${f}" matrices/ 2>/dev/null || true; done
    for f in ${selection_qc}; do cp "\${f}" matrices/ 2>/dev/null || true; done
    for f in ${joblib_files}; do cp "\${f}" matrices/ 2>/dev/null || true; done
    cp ${scoreboard_file} matrices/ 2>/dev/null || true

    set +e
    PYTHONUNBUFFERED=1 kreview report \\
        --input-dir matrices \\
        --out-dir reports \\
        --shap-samples ${params.shap_samples ?: 500} \\
        --shap-features ${params.shap_features ?: 10} \\
        ${cvd_flag}
    REPORT_EXIT=\$?
    set -e

    # Failure handling — #98, mirroring the #59 GPU wrappers. `kreview report` exits 1 when
    # ANY dashboard fails (fail-loud, v0.0.28) — but Nextflow only publishes outputs of
    # exit-0 tasks, so on the iris v0.0.29 run 17 successfully rendered dashboards were
    # stranded in the work dir and the published outdir had no reports/ at all. So: FAIL
    # LOUD first (exit non-zero -> the retry ladder gets a chance, an OOM may clear at
    # higher memory), and on the TERMINAL attempt degrade gracefully — exit 0 so everything
    # that rendered publishes, together with report_manifest.json naming the failures and
    # their *_render.log debug logs. A partial reports/ dir is loud, never silently complete.
    if [ \$REPORT_EXIT -ne 0 ]; then
        if [ ${task.attempt} -le ${task.maxRetries} ]; then
            echo "ERROR: report failed (exit=\$REPORT_EXIT), attempt ${task.attempt}/\$((${task.maxRetries}+1)) — failing to trigger retry + memory escalation" >&2
            exit \$REPORT_EXIT
        fi
        # Terminal attempt: guarantee a manifest exists even if the CLI crashed before
        # writing one, then publish whatever rendered.
        [ -f reports/report_manifest.json ] || \\
            echo '{"error": "kreview report crashed before writing a manifest", "exit_code": '\$REPORT_EXIT'}' > reports/report_manifest.json
        echo "WARNING: report failed (exit=\$REPORT_EXIT) after ${task.maxRetries} retries — publishing rendered dashboards + report_manifest.json (see failed_evaluators)" >&2
    fi
    """

    // Stub: create declared outputs only — smoke-tests DAG wiring (see issue #80).
    stub:
    """
    mkdir -p reports
    touch reports/stub_report.html
    touch reports/stub_plot.png
    echo '{}' > reports/report_manifest.json
    """
}
