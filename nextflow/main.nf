#!/usr/bin/env nextflow

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    KREVIEW NF-CORE PIPELINE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Standalone evaluation wrapper for kreview.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

nextflow.enable.dsl = 2

include { KREVIEW_EVAL }     from './workflows/kreview_eval'
include { KREVIEW_LABEL_WF } from './workflows/kreview_label'

def helpMessage() {
    log.info """
    ================================================================
     K R E V I E W   P I P E L I N E  (v${workflow.manifest.version})
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
     --krewlyzer_dir            Absolute path to parquet results (eval workflow only)

     Workflow Selection:
     --workflow                 'eval' (default) or 'label'
                                eval  = Label → Extract → Select → Eval → Report
                                label = Label only (no feature extraction required)

     Pipeline Mode (eval workflow only):
     --pipeline_mode            'monolithic' (default) or 'multistage'
                                multistage = Label → Extract(×N) → Fuse → Eval → Report

     ML Engine:
     --outdir                   Output directory (default: ./results)
     --cv_folds                 Cross Validation folds (default: 5, slurm: 10)
     --top_percentile           Top X% features per metric for model training (default: 10)
     --chunk_size               DuckDB batch size: 'auto' probes row density (default: auto)
     --impute_strategy          Imputation method (default: median)

     Labeling Engine:
     --min_vaf                  Min VAF for Possible ctDNA+ (default: 0.01)
     --min_fragments            Min fragments PF for Depth QC (default: 2000)
     --min_variants             Min variants passing VAF (default: 1)
     --ch_hotspot_maf           TSV of CH hotspot variants for CH-only demotion (default: null)

     SHAP Explainability:
     --shap_samples             Max samples for SHAP computation (default: 500, slurm: 5000)
     --shap_features            Max features displayed in SHAP plots (default: 10, slurm: 20)

     Execution Control:
     --resume_eval              Skip evaluators with existing results (default: false)
     --skip_report              Skip Quarto dashboard generation (default: false)
     --cvd_safe                 Use colorblind-safe palette (default: false)
     --compute_univariate_auc   Compute per-feature univariate AUC (default: false)

     Multistage Options (--pipeline_mode multistage):
     --run_gpu_eval             Enable GPU evaluation step (default: false)
     --gpu_models               Comma-separated GPU models: tabpfn,tabicl (default: tabpfn,tabicl)
     --min_evaluators           Min evaluators per sample for fuse (default: 1)
     --gpu_partition            SLURM partition for GPU jobs (default: gpu; iris: gpushort)
     --run_multimodal_eval      Enable cross-evaluator multimodal stacking (default: false)

     Targeted Execution:
     --features                 Comma-separated list of evaluators (e.g. "AtacOnTarget,FSCOnTarget")
     --tier                     Run only a specific tier level (e.g. 1 or 2)

     Profiles:
     -profile docker            Run locally leveraging GHCR Docker
     -profile slurm             Run on HPC clusters leveraging Singularity
     -profile iris              IRIS HPC: cmobic_cpu + gpushort GPU partition
    ================================================================
    """.stripIndent()
}

workflow NFCORE_KREVIEW {
    // Assert required (common to all workflows)
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

    ch_cancer = Channel.value(file(params.cancer_samplesheet, checkIfExists: true))
    ch_xs1    = Channel.value(file(params.healthy_xs1_samplesheet, checkIfExists: true))
    ch_xs2    = Channel.value(file(params.healthy_xs2_samplesheet, checkIfExists: true))

    // URIs passed down directly to prevent local `work/` symlink staging explosion
    val_cbioportal_dir = params.cbioportal_dir

    // ── Workflow routing ──
    def wf = params.workflow ?: 'eval'

    if (wf == 'label') {
        // Label-only: does NOT require krewlyzer_dir
        log.info "Running LABEL-ONLY workflow (no feature extraction)"
        KREVIEW_LABEL_WF(
            ch_cancer,
            ch_xs1,
            ch_xs2,
            val_cbioportal_dir,
        )
    } else if (wf == 'eval') {
        // Full eval pipeline: requires krewlyzer_dir
        if (!params.krewlyzer_dir) {
            log.error "ERROR: --krewlyzer_dir is required for the eval workflow"
            helpMessage()
            System.exit(1)
        }
        val_krewlyzer_dir = params.krewlyzer_dir

        KREVIEW_EVAL(
            ch_cancer,
            ch_xs1,
            ch_xs2,
            val_cbioportal_dir,
            val_krewlyzer_dir,
        )
    } else {
        log.error "ERROR: Unknown --workflow '${wf}'. Use 'eval' (default) or 'label'."
        helpMessage()
        System.exit(1)
    }
}

workflow {
    if (params.help) {
        helpMessage()
        System.exit(0)
    }
    
    NFCORE_KREVIEW()
}
