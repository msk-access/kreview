// ---------------------------------------------------------
// KREVIEW_EVAL — Multi-stage evaluation pipeline
// ---------------------------------------------------------
//
// DAG (multistage mode):
//
//   KREVIEW_EXTRACT ×N  (scatter across evaluators)
//        |
//   [collect all matrices]
//        |
//     +--------+----------+
//     |        |          |
//   FUSE   EVAL_CPU   EVAL_GPU   (all 3 run in parallel)
//     |        |          |
//     +--------+----------+
//              |
//     EVAL_MULTIMODAL  (needs fuse + cpu + gpu results)
//              |
//          REPORT
//
// The pipeline mode is controlled by params.pipeline_mode:
//   'monolithic' — Original single-process KREVIEW_RUN (backward compat)
//   'multistage' — Decomposed: Extract(×N) → Fuse + Eval → Report
//
// Default: 'monolithic' for backward compatibility.
// ---------------------------------------------------------

include { KREVIEW_RUN      } from '../modules/local/kreview/run'
include { KREVIEW_EXTRACT  } from '../modules/local/kreview/extract'
include { KREVIEW_FUSE     } from '../modules/local/kreview/fuse'
include { KREVIEW_EVAL_CPU } from '../modules/local/kreview/eval_cpu'
include { KREVIEW_EVAL_GPU        } from '../modules/local/kreview/eval_gpu'
include { KREVIEW_EVAL_MULTIMODAL } from '../modules/local/kreview/eval_multimodal'
include { KREVIEW_REPORT           } from '../modules/local/kreview/report'

workflow KREVIEW_EVAL {
    take:
    ch_cancer_samplesheet
    ch_healthy_xs1_samplesheet
    ch_healthy_xs2_samplesheet
    val_cbioportal_dir
    val_krewlyzer_results

    main:
    // Initialize output channels — populated by whichever branch runs
    ch_html_reports = Channel.empty()
    ch_static_plots = Channel.empty()
    ch_json_stats   = Channel.empty()
    ch_duckdb_db    = Channel.empty()

    if (params.pipeline_mode == 'multistage') {
        // ── Multistage mode ──
        // Decompose into: Extract(×N parallel) → Fuse → Eval-CPU + Eval-GPU → Report

        // Step 1: Build evaluator name channel for scatter
        if (params.features) {
            ch_evaluators = Channel.of(params.features.split(','))
                .map { it.trim() }
        } else {
            // Default: all 26 registered evaluators
            ch_evaluators = Channel.of(
                'AtacOnTarget', 'AtacGenomewide',
                'BreakPointMotifOnTarget', 'BreakPointMotifGenomewide',
                'EndMotifOnTarget', 'EndMotif1mer', 'EndMotifGenomewide',
                'FSCOnTarget', 'FSCGenomewide', 'FSC_gene', 'FSC_regions',
                'FsdOnTarget', 'FsdGenomewide',
                'FsrOnTarget', 'FsrGenomewide',
                'MdsOnTarget', 'MDSExon', 'MDSGene', 'MdsGenomewide',
                'OCFOfftarget', 'OCFOntarget',
                'TfbsOnTarget', 'TfbsGenomewide',
                'WPSBackground', 'WPSGenome', 'WPSPanel'
            )
        }

        // Step 2: Parallel extraction — one job per evaluator
        KREVIEW_EXTRACT(
            ch_cancer_samplesheet,
            ch_healthy_xs1_samplesheet,
            ch_healthy_xs2_samplesheet,
            val_cbioportal_dir,
            val_krewlyzer_results,
            ch_evaluators
        )

        // Step 3: Collect all matrices for downstream stages
        ch_all_matrices = KREVIEW_EXTRACT.out.matrices.collect()

        // Step 4a: Fuse into super-matrix (for multimodal eval)
        KREVIEW_FUSE(ch_all_matrices)

        // Step 4b: CPU evaluation on per-evaluator matrices
        KREVIEW_EVAL_CPU(ch_all_matrices)
        ch_json_stats = KREVIEW_EVAL_CPU.out.json_stats

        // Step 5: GPU evaluation on per-evaluator matrices (optional)
        if (params.run_gpu_eval) {
            KREVIEW_EVAL_GPU(ch_all_matrices)
        }

        // Step 6: Multimodal cross-evaluator evaluation (optional)
        if (params.run_multimodal_eval) {
            // Collect per-evaluator JSON results from CPU (and optionally GPU)
            ch_cpu_results = KREVIEW_EVAL_CPU.out.json_stats.collect()
            ch_results = params.run_gpu_eval
                ? ch_cpu_results.mix(KREVIEW_EVAL_GPU.out.gpu_results.collect())
                : ch_cpu_results

            KREVIEW_EVAL_MULTIMODAL(
                KREVIEW_FUSE.out.super_matrix,
                ch_results
            )
        }

        // Step 7: Report generation (optional)
        if (!params.skip_report) {
            KREVIEW_REPORT(ch_all_matrices)
            ch_html_reports = KREVIEW_REPORT.out.html_reports
            ch_static_plots = KREVIEW_REPORT.out.static_plots
        }

    } else {
        // ── Monolithic mode (backward compatible) ──
        // Single process runs label + extract + eval + report
        KREVIEW_RUN(
            ch_cancer_samplesheet,
            ch_healthy_xs1_samplesheet,
            ch_healthy_xs2_samplesheet,
            val_cbioportal_dir,
            val_krewlyzer_results
        )
        ch_html_reports = KREVIEW_RUN.out.html_reports
        ch_static_plots = KREVIEW_RUN.out.static_plots
        ch_json_stats   = KREVIEW_RUN.out.json_stats
        ch_duckdb_db    = KREVIEW_RUN.out.duckdb_db
    }

    emit:
    html_reports = ch_html_reports
    static_plots = ch_static_plots
    json_stats   = ch_json_stats
    duckdb_db    = ch_duckdb_db
}
