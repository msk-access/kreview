// ---------------------------------------------------------
// KREVIEW_EXTRACT — Extract feature matrix for one evaluator
// ---------------------------------------------------------
// Runs `kreview extract --features <name>` to produce a single
// *_matrix.parquet file. Nextflow scatters across evaluators
// so each runs in parallel on its own node/slot.
//
// NOTE: kreview extract re-runs labeling internally (labels.parquet
// is NOT consumed as input here). This is by design: extract needs
// the full label DataFrame in memory to build the matrix. The label
// step is fast (~30s) so the duplication is acceptable. The separate
// KREVIEW_LABEL process exists for standalone label-only workflows.
//
// Inputs:  samplesheets, cBioPortal dir, krewlyzer dir, evaluator name
// Outputs: *_matrix.parquet
// ---------------------------------------------------------

process KREVIEW_EXTRACT {
    tag "extract-${evaluator_name}"
    label 'process_high'

    input:
    path(cancer_sheet,  stageAs: 'cancer_samplesheet.csv')
    path(healthy_xs1,   stageAs: 'healthy_xs1_samplesheet.csv')
    path(healthy_xs2,   stageAs: 'healthy_xs2_samplesheet.csv')
    val cbioportal_dir
    val krewlyzer_results
    val evaluator_name

    output:
    path "output/*_matrix.parquet", emit: matrices

    script:
    def ch_maf_flag = params.ch_hotspot_maf \
        ? "--ch-hotspot-maf \"${params.ch_hotspot_maf}\"" : ""
    def tier_flag = params.tier \
        ? "--tier ${params.tier}" : ""
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
        ${ch_maf_flag} \\
        ${tier_flag} \\
        --features "${evaluator_name}" \\
        --output output
    """
}
