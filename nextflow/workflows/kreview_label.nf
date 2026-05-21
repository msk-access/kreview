/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    KREVIEW LABEL WORKFLOW — Standalone label generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Runs kreview label to produce a labels.parquet without feature extraction.
    Use this for label QC, label audits, or generating labels ahead of time.

    Usage:
        nextflow run main.nf --workflow label \
            --cancer_samplesheet cancer.csv \
            --healthy_xs1_samplesheet xs1.csv \
            --healthy_xs2_samplesheet xs2.csv \
            --cbioportal_dir /path/to/cBioportal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { KREVIEW_LABEL } from '../modules/local/kreview/label'

workflow KREVIEW_LABEL_WF {

    take:
    ch_cancer       // Channel<Path>: cancer samplesheet CSV
    ch_xs1          // Channel<Path>: healthy XS1 samplesheet CSV
    ch_xs2          // Channel<Path>: healthy XS2 samplesheet CSV
    val_cbio_dir    // String:        cBioPortal directory path

    main:
    KREVIEW_LABEL(
        ch_cancer,
        ch_xs1,
        ch_xs2,
        val_cbio_dir,
    )

    emit:
    labels = KREVIEW_LABEL.out.labels
}
