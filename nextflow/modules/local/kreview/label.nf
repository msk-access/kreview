// ---------------------------------------------------------
// KREVIEW_LABEL — Generate ctDNA labels from cBioPortal data
// ---------------------------------------------------------
// Produces a single labels.parquet file that maps every sample
// to its 5-tier ctDNA classification. Downstream processes
// (KREVIEW_EXTRACT, KREVIEW_EVAL_CPU) consume this as input.
//
// Inputs:  samplesheets (cancer, healthy XS1, healthy XS2), cBioPortal dir
// Outputs: labels.parquet
// ---------------------------------------------------------

process KREVIEW_LABEL {
    tag "kreview-label"
    label 'process_medium'
    publishDir "${params.outdir}/labels", mode: 'copy'

    input:
    path(cancer_sheet,  stageAs: 'cancer_samplesheet.csv')
    path(healthy_xs1,   stageAs: 'healthy_xs1_samplesheet.csv')
    path(healthy_xs2,   stageAs: 'healthy_xs2_samplesheet.csv')
    val cbioportal_dir

    output:
    path "labels.parquet", emit: labels

    script:
    def ch_maf_flag = params.ch_hotspot_maf \
        ? "--ch-hotspot-maf \"${params.ch_hotspot_maf}\"" : ""
    """
    set -euo pipefail

    PYTHONUNBUFFERED=1 kreview label \\
        --cancer-samplesheet ${cancer_sheet} \\
        --healthy-xs1-samplesheet ${healthy_xs1} \\
        --healthy-xs2-samplesheet ${healthy_xs2} \\
        --cbioportal-dir "${cbioportal_dir}" \\
        --min-vaf ${params.min_vaf ?: 0.01} \\
        --min-fragments ${params.min_fragments ?: 2000} \\
        --min-variants ${params.min_variants ?: 1} \\
        ${ch_maf_flag} \\
        --output labels.parquet
    """
}
