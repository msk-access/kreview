process KREVIEW_RUN {
    tag "kreview-eval-${params.chunk_size}"
    label 'process_high'

    // The container is governed dynamically by nextflow.config
    // For large runs, singularity.autoMounts is required.

    input:
    path cancer_sheet
    path healthy_xs1
    path healthy_xs2
    val cbioportal_dir          // URI STRINGS: Passed as val to avoid symlinking
    val krewlyzer_results       // URI STRINGS: Prevents staging 14000 parquets natively into work/

    output:
    path "output/reports/*.html"     , emit: html_reports, optional: true
    path "output/static_plots/*.png" , emit: static_plots, optional: true
    path "output/stats/*.json"       , emit: json_stats
    path "output/kreview_lake.duckdb", emit: duckdb_db   , optional: true

    script:
    def features_flag = params.features ? "--features \"${params.features}\"" : ""
    def tier_flag     = params.tier     ? "--tier ${params.tier}"             : ""
    
    """
    # 1. Ensure output skeleton exists
    mkdir -p output/
    
    # 2. Execute primary evaluation loop
    # We use PYTHONUNBUFFERED=1 to ensure Nextflow logs the structlog outputs in realtime
    PYTHONUNBUFFERED=1 kreview run \\
        --cancer-samplesheet ${cancer_sheet} \\
        --healthy-xs1-samplesheet ${healthy_xs1} \\
        --healthy-xs2-samplesheet ${healthy_xs2} \\
        --cbioportal-dir "${cbioportal_dir}" \\
        --krewlyzer-dir "${krewlyzer_results}" \\
        --cv-folds ${params.cv_folds ?: 5} \\
        --impute-strategy ${params.impute_strategy ?: 'median'} \\
        --chunk-size ${params.chunk_size} \\
        --workers ${task.cpus} \\
        ${features_flag} \\
        ${tier_flag} \\
        --export-duckdb \\
        --output output/
    """
}
