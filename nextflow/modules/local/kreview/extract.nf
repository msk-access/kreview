// ---------------------------------------------------------
// KREVIEW_EXTRACT — Extract feature matrix for one evaluator
// ---------------------------------------------------------
// Runs `kreview extract --features <name>` to produce a single
// *_matrix.parquet file. Nextflow scatters across evaluators
// so each runs in parallel on its own node/slot.
//
// In multistage mode, a pre-computed labels.parquet is passed
// from the upstream KREVIEW_LABEL process via --labels, avoiding
// redundant re-labeling across all N evaluator jobs.
//
// Inputs:  samplesheets, cBioPortal dir, krewlyzer dir,
//          evaluator name, labels.parquet (optional)
// Outputs: *_matrix.parquet
// ---------------------------------------------------------

process KREVIEW_EXTRACT {
    tag "extract-${evaluator_name}"
    label 'process_high'
    publishDir "${params.outdir}/matrices/raw", mode: 'copy', pattern: 'output/*_matrix.parquet'

    input:
    path(cancer_sheet,  stageAs: 'cancer_samplesheet.csv')
    path(healthy_xs1,   stageAs: 'healthy_xs1_samplesheet.csv')
    path(healthy_xs2,   stageAs: 'healthy_xs2_samplesheet.csv')
    val cbioportal_dir
    val krewlyzer_results
    val evaluator_name
    path labels_file    // Pre-computed labels.parquet from KREVIEW_LABEL

    output:
    path "output/*_matrix.parquet", emit: matrices

    script:
    def ch_maf_flag = params.ch_hotspot_maf \
        ? "--ch-hotspot-maf \"${params.ch_hotspot_maf}\"" : ""
    def tier_flag = params.tier \
        ? "--tier ${params.tier}" : ""
    def labels_flag = labels_file.name != 'NO_LABELS' \
        ? "--labels ${labels_file}" : ""
    """
    set -euo pipefail

    mkdir -p output

    PYTHONUNBUFFERED=1 kreview extract \\
        --cancer-samplesheet ${cancer_sheet} \\
        --healthy-xs1-samplesheet ${healthy_xs1} \\
        --healthy-xs2-samplesheet ${healthy_xs2} \\
        --cbioportal-dir "${cbioportal_dir}" \\
        --krewlyzer-dir "${krewlyzer_results}" \\
        --min-vaf ${params.min_vaf ?: 0.01} \\
        --min-fragments ${params.min_fragments ?: 2000} \\
        --min-variants ${params.min_variants ?: 1} \\
        --chunk-size ${params.chunk_size} \\
        --duckdb-threads ${params.duckdb_threads ?: 8} \\
        --duckdb-memory "${params.duckdb_memory ?: '32GB'}" \\
        ${ch_maf_flag} \\
        ${tier_flag} \\
        ${labels_flag} \\
        --features "${evaluator_name}" \\
        --output output
    """
}
