// ---------------------------------------------------------
// KREVIEW_REPORT — Render the single-page evaluation report
// ---------------------------------------------------------
// #79: builds ONE self-contained HTML (plotly inlined, no CDN) from the run's
// aggregate artifacts via `kreview report`. No Quarto, no papermill, no render-time
// SHAP — the data layer computes curves from the already-persisted OOF arrays in
// seconds, so the old 64→192 GB memory ladder is gone with it.
//
// Inputs are staged into the canonical outdir layout the report builder consumes
// (labels/, models/cpu, matrices/selected, models/multimodal, ablation/merged).
// Multimodal and ablation inputs are OPTIONAL (NO_* sentinels, #97 pattern): the
// report renders without them and says so, instead of the process starving.
//
// The Nextflow execution trace does not exist until the workflow ends, so the
// run-diagnostics tab stays empty in-pipeline; re-running `kreview report` on the
// published outdir afterwards fills it in.
// ---------------------------------------------------------

process KREVIEW_REPORT {
    tag "kreview-report"
    label 'process_low'
    publishDir "${params.outdir}", mode: 'copy'  // output glob includes reports/ prefix

    input:
    path(labels_file)       // labels.parquet from KREVIEW_LABEL
    path(model_results)     // Collected *_model_results.json + *_gpu_model_results.json
    path(selection_qc)      // Collected *_selection_qc.json from KREVIEW_SELECT_SINGLE
    path(scoreboard_file)   // scoreboard parquet, or NO_SCOREBOARD sentinel
    path(multimodal_jsons)  // Collected multimodal jsons, or NO_MULTIMODAL sentinel
    path(ablation_jsons)    // Collected *_best_subset.json, or NO_MERGED_ABLATION sentinel

    output:
    path "reports/kreview_report.html",  emit: html_report, optional: true
    // #98: the manifest is the loud, machine-readable record of what the report covers
    // (or of the failure) — a missing/partial report is never silent.
    path "reports/report_manifest.json", emit: manifest,    optional: true

    script:
    """
    set -euo pipefail

    # Shared report env centralized in nextflow.config (params.report_env_setup, #58):
    # HOME/TMPDIR/XDG/IPYTHONDIR/MPLCONFIGDIR for read-only-/home HPC nodes.
    ${params.report_env_setup}

    # Stage channel inputs into the canonical outdir layout build_report_data expects.
    mkdir -p outdir/labels outdir/models/cpu outdir/matrices/selected \\
             outdir/models/multimodal outdir/ablation/merged reports
    cp ${labels_file} outdir/labels/labels.parquet
    for f in ${model_results}; do cp "\${f}" outdir/models/cpu/ 2>/dev/null || true; done
    for f in ${selection_qc}; do cp "\${f}" outdir/matrices/selected/ 2>/dev/null || true; done
    if [ "${scoreboard_file}" != "NO_SCOREBOARD" ]; then
        cp ${scoreboard_file} outdir/scoreboard_combined__all.parquet
    fi
    for f in ${multimodal_jsons}; do
        [ "\$f" = "NO_MULTIMODAL" ] || cp "\$f" outdir/models/multimodal/ 2>/dev/null || true
    done
    for f in ${ablation_jsons}; do
        [ "\$f" = "NO_MERGED_ABLATION" ] || cp "\$f" outdir/ablation/merged/ 2>/dev/null || true
    done

    set +e
    PYTHONUNBUFFERED=1 kreview report \\
        --outdir outdir \\
        --out-dir reports \\
        --run-label "kreview v${params.kreview_version}"
    REPORT_EXIT=\$?
    set -e

    # Failure handling — #98, mirroring the #59 GPU wrappers: fail loud first (exit
    # non-zero -> retry ladder), degrade gracefully on the TERMINAL attempt (exit 0 so
    # the manifest — written by the CLI even on failure — publishes and the missing
    # report is recorded, never silent).
    if [ \$REPORT_EXIT -ne 0 ]; then
        if [ ${task.attempt} -le ${task.maxRetries} ]; then
            echo "ERROR: report failed (exit=\$REPORT_EXIT), attempt ${task.attempt}/\$((${task.maxRetries}+1)) — failing to trigger retry" >&2
            exit \$REPORT_EXIT
        fi
        [ -f reports/report_manifest.json ] || \\
            echo '{"error": "kreview report crashed before writing a manifest", "exit_code": '\$REPORT_EXIT'}' > reports/report_manifest.json
        echo "WARNING: report failed (exit=\$REPORT_EXIT) after ${task.maxRetries} retries — publishing report_manifest.json (see error)" >&2
    fi
    """

    // Stub: create declared outputs only — smoke-tests DAG wiring (see issue #80).
    stub:
    """
    mkdir -p reports
    touch reports/kreview_report.html
    echo '{}' > reports/report_manifest.json
    """
}
