#!/usr/bin/env nextflow

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    KREVIEW NF-CORE PIPELINE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Standalone evaluation wrapper for kreview.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

nextflow.enable.dsl = 2

include { KREVIEW_EVAL } from './workflows/kreview_eval'

def helpMessage() {
    log.info """
    ================================================================
     K R E W I E W   P I P E L I N E  (v${workflow.manifest.version})
    ================================================================
     Usage:
     nextflow run main.nf --cancer_samplesheet cancer.csv \\
                          --healthy_xs1_samplesheet xs1.csv \\
                          --healthy_xs2_samplesheet xs2.csv \\
                          --cbioportal_dir /path/to/cBioportal \\
                          --krewlyzer_dir /path/to/parquets [options]

     Required:
     --cancer_samplesheet       CSV of cancer samples
     --healthy_xs1_samplesheet  CSV of healthy controls (XS1)
     --healthy_xs2_samplesheet  CSV of healthy controls (XS2)
     --cbioportal_dir           Absolute path to MSK cBioPortal sync directory
     --krewlyzer_dir            Absolute path to parquet results (or manifest.txt file)

     ML Engine:
     --outdir                   Output directory (default: ./results)
     --cv_folds                 Cross Validation folds (default: 5, slurm: 10)
     --top_n                    Max features for model training (default: 50)
     --chunk_size               DuckDB maxfile limit  (default: 50 local, 500 slurm)
     --impute_strategy          Imputation method (default: median)

     SHAP Explainability:
     --shap_samples             Max samples for SHAP computation (default: 500, slurm: 5000)
     --shap_features            Max features displayed in SHAP plots (default: 10, slurm: 20)

     Execution Control:
     --resume_eval              Skip evaluators with existing results (default: false)
     --skip_report              Skip Quarto dashboard generation (default: false)
     --cvd_safe                 Use colorblind-safe palette (default: false)

     Targeted Execution:
     --features                 Comma-separated list of evaluators (e.g. "AtacOnTarget,FSCOnTarget")
     --tier                     Run only a specific tier level (e.g. 1 or 2)

     Profiles:
     -profile docker            Run locally leveraging GHCR Docker
     -profile slurm             Run on HPC clusters leveraging Singularity
    ================================================================
    """.stripIndent()
}

workflow NFCORE_KREVIEW {
    // Assert required
    if (!params.cancer_samplesheet) {
        log.error "ERROR: --cancer_samplesheet is required"
        helpMessage()
        System.exit(1)
    }
    if (!params.cbioportal_dir) {
        log.error "ERROR: --cbioportal_dir is required"
        helpMessage()
        System.exit(1)
    }
    if (!params.krewlyzer_dir) {
        log.error "ERROR: --krewlyzer_dir is required"
        helpMessage()
        System.exit(1)
    }

    ch_cancer = Channel.value(file(params.cancer_samplesheet, checkIfExists: true))
    ch_xs1    = Channel.value(file(params.healthy_xs1_samplesheet, checkIfExists: true))
    ch_xs2    = Channel.value(file(params.healthy_xs2_samplesheet, checkIfExists: true))

    // URIs passed down directly to prevent local `work/` symlink staging explosion
    val_cbioportal_dir = params.cbioportal_dir
    val_krewlyzer_dir  = params.krewlyzer_dir

    KREVIEW_EVAL(
        ch_cancer,
        ch_xs1,
        ch_xs2,
        val_cbioportal_dir,
        val_krewlyzer_dir
    )
}

workflow {
    if (params.help) {
        helpMessage()
        System.exit(0)
    }
    
    NFCORE_KREVIEW()
}
