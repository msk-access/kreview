include { KREVIEW_RUN } from '../modules/local/kreview/run'

workflow KREVIEW_EVAL {
    take:
    ch_cancer_samplesheet
    ch_healthy_xs1_samplesheet
    ch_healthy_xs2_samplesheet
    val_cbioportal_dir
    val_krewlyzer_results

    main:
    // Invoke the primary python execution
    KREVIEW_RUN(
        ch_cancer_samplesheet,
        ch_healthy_xs1_samplesheet,
        ch_healthy_xs2_samplesheet,
        val_cbioportal_dir,
        val_krewlyzer_results
    )

    emit:
    html_reports = KREVIEW_RUN.out.html_reports
    static_plots = KREVIEW_RUN.out.static_plots
    json_stats   = KREVIEW_RUN.out.json_stats
    duckdb_db    = KREVIEW_RUN.out.duckdb_db
}
