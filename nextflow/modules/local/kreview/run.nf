process KREVIEW_RUN {
    tag "kreview-eval-${params.chunk_size}"
    label 'process_high'

    // The container is governed dynamically by nextflow.config
    // For large runs, singularity.autoMounts is required.

    input:
    path(cancer_sheet, stageAs: 'cancer_samplesheet.csv')
    path(healthy_xs1,  stageAs: 'healthy_xs1_samplesheet.csv')
    path(healthy_xs2,  stageAs: 'healthy_xs2_samplesheet.csv')
    val cbioportal_dir          // URI STRINGS: Passed as val to avoid symlinking
    val krewlyzer_results       // URI STRINGS: Prevents staging 14000 parquets natively into work/

    output:
    path "output/reports/*.html"     , emit: html_reports, optional: true
    path "output/static_plots/*.png" , emit: static_plots, optional: true
    path "output/stats/*.json"       , emit: json_stats
    path "output/kreview_lake.duckdb", emit: duckdb_db   , optional: true

    script:
    def features_flag = params.features     ? "--features \"${params.features}\"" : ""
    def tier_flag     = params.tier         ? "--tier ${params.tier}"             : ""
    def skip_rpt_flag = params.skip_report  ? "--skip-report"                     : ""
    def cvd_flag      = params.cvd_safe     ? "--cvd-safe"                        : ""
    def uauc_flag     = params.compute_univariate_auc ? "--compute-univariate-auc" : ""
    def duckdb_flag   = params.export_duckdb ? "--export-duckdb"                   : ""
    // Use persistent output dir so --resume finds results across Nextflow retries
    def persistent_out = params.outdir + "/evaluators"
    
    """
    # 1. Ensure output skeleton exists (persistent dir + local dir for Nextflow outputs)
    mkdir -p ${persistent_out}
    mkdir -p output/stats output/reports output/static_plots
    
    # 2. Execute primary evaluation loop
    # Use persistent_out so results survive Nextflow work/ directory changes on retry.
    # --resume always enabled: skips evaluators with existing model_results.json
    PYTHONUNBUFFERED=1 kreview run \\
        --cancer-samplesheet ${cancer_sheet} \\
        --healthy-xs1-samplesheet ${healthy_xs1} \\
        --healthy-xs2-samplesheet ${healthy_xs2} \\
        --cbioportal-dir "${cbioportal_dir}" \\
        --krewlyzer-dir "${krewlyzer_results}" \\
        --cv-folds ${params.cv_folds ?: 5} \\
        --top-n ${params.top_n ?: 50} \\
        --impute-strategy ${params.impute_strategy ?: 'median'} \\
        --chunk-size ${params.chunk_size} \\
        --shap-samples ${params.shap_samples ?: 500} \\
        --shap-features ${params.shap_features ?: 10} \\
        --workers ${task.cpus} \\
        ${features_flag} \\
        ${tier_flag} \\
        --resume \\
        ${skip_rpt_flag} \\
        ${cvd_flag} \\
        ${uauc_flag} \\
        ${duckdb_flag} \\
        --output ${persistent_out}
    
    # 3. Copy results to output/ for Nextflow publishDir collection
    cp ${persistent_out}/*_model_results.json output/stats/     2>/dev/null || true
    cp ${persistent_out}/*_eval_stats.parquet  output/stats/     2>/dev/null || true
    cp ${persistent_out}/*.html               output/reports/   2>/dev/null || true
    cp ${persistent_out}/*.png                output/static_plots/ 2>/dev/null || true
    cp ${persistent_out}/*.duckdb             output/           2>/dev/null || true
    """
}
