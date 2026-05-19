// ---------------------------------------------------------
// KREVIEW_EVAL_CPU — Run per-evaluator CPU model evaluation
// ---------------------------------------------------------
// Uses the original `kreview run` command with all collected
// matrices already extracted. With --resume, it skips labeling
// and extraction (if matrices already exist) and proceeds to
// model training (LR, RF, XGBoost), SHAP, and report generation.
//
// This process handles the traditional single-feature evaluation
// pipeline. Multimodal evaluation is handled by KREVIEW_EVAL_GPU.
//
// Inputs:  samplesheets, cBioPortal dir, krewlyzer dir, collected matrices
// Outputs: model_results JSON, eval stats, HTML reports, plots
// ---------------------------------------------------------

process KREVIEW_EVAL_CPU {
    tag "kreview-eval-cpu"
    label 'process_high'

    input:
    path(cancer_sheet,  stageAs: 'cancer_samplesheet.csv')
    path(healthy_xs1,   stageAs: 'healthy_xs1_samplesheet.csv')
    path(healthy_xs2,   stageAs: 'healthy_xs2_samplesheet.csv')
    val cbioportal_dir
    val krewlyzer_results
    path(matrix_files)     // Collected *_matrix.parquet from KREVIEW_EXTRACT

    output:
    path "output/reports/*.html"     , emit: html_reports , optional: true
    path "output/static_plots/*.png" , emit: static_plots , optional: true
    path "output/stats/*.json"       , emit: json_stats
    path "output/kreview_lake.duckdb", emit: duckdb_db    , optional: true

    script:
    def features_flag  = params.features     ? "--features \"${params.features}\""   : ""
    def tier_flag      = params.tier         ? "--tier ${params.tier}"               : ""
    def skip_rpt_flag  = params.skip_report  ? "--skip-report"                       : ""
    def cvd_flag       = params.cvd_safe     ? "--cvd-safe"                          : ""
    def uauc_flag      = params.compute_univariate_auc ? "--compute-univariate-auc"  : ""
    def duckdb_flag    = params.export_duckdb ? "--export-duckdb"                     : ""
    def ch_maf_flag    = params.ch_hotspot_maf ? "--ch-hotspot-maf \"${params.ch_hotspot_maf}\"" : ""
    def persistent_out = params.outdir + "/evaluators"
    """
    set -euo pipefail

    mkdir -p ${persistent_out}
    mkdir -p output/stats output/reports output/static_plots

    # Stage pre-extracted matrices into the persistent output dir
    for f in ${matrix_files}; do
        cp "\${f}" ${persistent_out}/
    done

    # Run full pipeline — with --resume, label + extraction is skipped
    # if matrices already exist; proceeds directly to model evaluation.
    PYTHONUNBUFFERED=1 kreview run \\
        --cancer-samplesheet ${cancer_sheet} \\
        --healthy-xs1-samplesheet ${healthy_xs1} \\
        --healthy-xs2-samplesheet ${healthy_xs2} \\
        --cbioportal-dir "${cbioportal_dir}" \\
        --krewlyzer-dir "${krewlyzer_results}" \\
        --cv-folds ${params.cv_folds ?: 5} \\
        --top-percentile ${params.top_percentile ?: 10.0} \\
        --impute-strategy ${params.impute_strategy ?: 'median'} \\
        --chunk-size ${params.chunk_size} \\
        --shap-samples ${params.shap_samples ?: 500} \\
        --shap-features ${params.shap_features ?: 10} \\
        ${features_flag} \\
        ${tier_flag} \\
        --resume \\
        ${skip_rpt_flag} \\
        ${cvd_flag} \\
        ${uauc_flag} \\
        ${duckdb_flag} \\
        ${ch_maf_flag} \\
        --output ${persistent_out}

    # Collect results for Nextflow publishDir
    cp ${persistent_out}/*_model_results.json output/stats/      2>/dev/null || true
    cp ${persistent_out}/*_eval_stats.parquet  output/stats/     2>/dev/null || true
    cp ${persistent_out}/*.html               output/reports/    2>/dev/null || true
    cp ${persistent_out}/*.png                output/static_plots/ 2>/dev/null || true
    cp ${persistent_out}/*.duckdb             output/            2>/dev/null || true
    """
}
