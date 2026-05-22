// ---------------------------------------------------------
// KREVIEW_EVAL — Multi-stage evaluation pipeline
// ---------------------------------------------------------
//
// DAG (multistage mode — per-evaluator parallel):
//
//   KREVIEW_EXTRACT ×N          (scatter across evaluators)
//        |
//   KREVIEW_SELECT_SINGLE ×N   (per-evaluator feature selection)
//        |
//     +---+---+---+
//     |       |   |
//  EVAL_CPU  FUSE EVAL_GPU     (CPU ×N parallel, GPU ×N on gpushort)
//  (×N)      (1)  (×N)
//     |       |   |
//     +---+---+---+
//         |
//    EVAL_MULTIMODAL           (cross-evaluator stacking, 1 job)
//         |
//       REPORT
//
// The pipeline mode is controlled by params.pipeline_mode:
//   'monolithic' — Original single-process KREVIEW_RUN (backward compat)
//   'multistage' — Decomposed per-evaluator parallelism
//
// Default: 'monolithic' for backward compatibility.
//
// Selective evaluators:
//   --features "AtacOnTarget,FSCOnTarget" limits all stages to N=2.
// ---------------------------------------------------------

// ── Module imports ──
// Monolithic
include { KREVIEW_RUN } from '../modules/local/kreview/run'

// Multistage — bulk modules (kept for backward compat, used by monolithic)
include { KREVIEW_EXTRACT } from '../modules/local/kreview/extract'
include { KREVIEW_FUSE    } from '../modules/local/kreview/fuse'
include { KREVIEW_REPORT  } from '../modules/local/kreview/report'

// Multistage — per-evaluator scatter modules
include { KREVIEW_SELECT_SINGLE   } from '../modules/local/kreview/select_single'
include { KREVIEW_EVAL_CPU_SINGLE } from '../modules/local/kreview/eval_cpu_single'
include { KREVIEW_EVAL_GPU_SINGLE } from '../modules/local/kreview/eval_gpu_single'

// Multistage — collect-only modules (need all evaluator results)
include { KREVIEW_EVAL_MULTIMODAL } from '../modules/local/kreview/eval_multimodal'

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
        // ── Multistage mode (per-evaluator parallelism) ──

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

        // Step 2: Parallel extraction — one job per evaluator (×N)
        KREVIEW_EXTRACT(
            ch_cancer_samplesheet,
            ch_healthy_xs1_samplesheet,
            ch_healthy_xs2_samplesheet,
            val_cbioportal_dir,
            val_krewlyzer_results,
            ch_evaluators
        )

        // Step 3: Per-evaluator feature selection (×N, parallel)
        // .flatten() converts collected list → channel of individual matrix files
        KREVIEW_SELECT_SINGLE(KREVIEW_EXTRACT.out.matrices.flatten())

        // Step 4a: Per-evaluator CPU evaluation (×N, parallel)
        KREVIEW_EVAL_CPU_SINGLE(KREVIEW_SELECT_SINGLE.out.matrix)
        ch_json_stats = KREVIEW_EVAL_CPU_SINGLE.out.json_stats

        // Step 4b: Per-evaluator GPU evaluation (×N, parallel, gpushort) [optional]
        // Runs in parallel with CPU eval — they are independent.
        if (params.run_gpu_eval) {
            KREVIEW_EVAL_GPU_SINGLE(KREVIEW_SELECT_SINGLE.out.matrix)
        }

        // Step 4c: Fuse selected matrices → super-matrix (1 job, needs all)
        ch_all_selected = KREVIEW_SELECT_SINGLE.out.matrix.collect()
        KREVIEW_FUSE(ch_all_selected)

        // Step 5: Multimodal cross-evaluator evaluation (1 job) [optional]
        // Needs: OOF probs from CPU/GPU eval + super_matrix from FUSE
        if (params.run_multimodal_eval) {
            ch_cpu_jsons = KREVIEW_EVAL_CPU_SINGLE.out.json_stats.collect()
            ch_results = params.run_gpu_eval
                ? ch_cpu_jsons.mix(KREVIEW_EVAL_GPU_SINGLE.out.gpu_results.collect())
                : ch_cpu_jsons

            KREVIEW_EVAL_MULTIMODAL(
                KREVIEW_FUSE.out.super_matrix,
                ch_results
            )
        }

        // Step 6: Report generation [optional]
        if (!params.skip_report) {
            KREVIEW_REPORT(ch_all_selected)
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
