// ---------------------------------------------------------
// KREVIEW_EVAL — Multi-stage evaluation pipeline
// ---------------------------------------------------------
//
// DAG (multistage mode — per-evaluator parallel):
//
//   KREVIEW_LABEL (1 job)
//        |
//   KREVIEW_EXTRACT ×N          (scatter across evaluators)
//        |
//   KREVIEW_SELECT_SINGLE ×N   (per-evaluator feature selection)
//        |
//     +---+---+---+
//     |       |   |
//  EVAL_CPU  FUSE EVAL_GPU     (CPU ×N parallel, GPU ×N on gpushort)
//  (×N)      (1)  (×N)
//     |       |   |
//     +---+---+---+---+
//     |       |       |
//  SCOREBOARD |   EVAL_MULTIMODAL   (scoreboard + multimodal in parallel)
//     |       |       |
//     +---+---+    REPORT_MULTIMODAL
//         |
//       REPORT                 (needs matrices + JSONs + scoreboard + joblib)
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

// Multistage — labeling (run once, shared across all extractors)
include { KREVIEW_LABEL } from '../modules/local/kreview/label'

// Multistage — bulk modules (kept for backward compat, used by monolithic)
include { KREVIEW_EXTRACT } from '../modules/local/kreview/extract'
include { KREVIEW_FUSE    } from '../modules/local/kreview/fuse'
include { KREVIEW_REPORT  } from '../modules/local/kreview/report'

// Multistage — per-evaluator scatter modules
include { KREVIEW_SELECT_SINGLE   } from '../modules/local/kreview/select_single'
include { KREVIEW_EVAL_CPU_SINGLE } from '../modules/local/kreview/eval_cpu_single'
include { KREVIEW_EVAL_GPU_SINGLE } from '../modules/local/kreview/eval_gpu_single'

// Multistage — collect-only modules (need all evaluator results)
include { KREVIEW_EVAL_MULTIMODAL   } from '../modules/local/kreview/eval_multimodal'
include { KREVIEW_REPORT_MULTIMODAL } from '../modules/local/kreview/report_multimodal'
include { KREVIEW_SCOREBOARD        } from '../modules/local/kreview/scoreboard'

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

        // Step 0: Label — single job, produces labels.parquet once
        KREVIEW_LABEL(
            ch_cancer_samplesheet,
            ch_healthy_xs1_samplesheet,
            ch_healthy_xs2_samplesheet,
            val_cbioportal_dir,
        )
        ch_labels = KREVIEW_LABEL.out.labels

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
        //         Each receives pre-computed labels.parquet (no re-labeling)
        KREVIEW_EXTRACT(
            ch_cancer_samplesheet,
            ch_healthy_xs1_samplesheet,
            ch_healthy_xs2_samplesheet,
            val_cbioportal_dir,
            val_krewlyzer_results,
            ch_evaluators,
            ch_labels
        )

        // Step 3: Per-evaluator feature selection (×N, parallel)
        // .flatten() converts collected list → channel of individual matrix files
        KREVIEW_SELECT_SINGLE(KREVIEW_EXTRACT.out.matrices.flatten())

        // Step 4a: Per-evaluator CPU evaluation (×N, parallel)
        KREVIEW_EVAL_CPU_SINGLE(KREVIEW_SELECT_SINGLE.out.matrix)
        ch_json_stats = KREVIEW_EVAL_CPU_SINGLE.out.json_stats
        ch_cpu_joblib = KREVIEW_EVAL_CPU_SINGLE.out.joblib_models

        // Step 4b: Per-evaluator GPU evaluation (×N, parallel, gpushort) [optional]
        // Runs in parallel with CPU eval — they are independent.
        // Pairs each matrix with its eval_stats for intelligent feature capping.
        if (params.run_gpu_eval) {
            // Pair matrix + eval_stats by evaluator name (basename matching)
            ch_gpu_input = KREVIEW_SELECT_SINGLE.out.matrix
                .map { f -> [f.baseName.replace('_matrix', ''), f] }
                .combine(
                    KREVIEW_SELECT_SINGLE.out.eval_stats
                        .map { f -> [f.baseName.replace('_eval_stats', ''), f] },
                    by: 0
                )
                .map { key, matrix, stats -> [matrix, stats] }

            KREVIEW_EVAL_GPU_SINGLE(ch_gpu_input.map { it[0] }, ch_gpu_input.map { it[1] })
        }

        // Step 4c: Fuse selected matrices → super-matrix (1 job, needs all)
        ch_all_selected = KREVIEW_SELECT_SINGLE.out.matrix.collect()
        KREVIEW_FUSE(ch_all_selected)

        // ── Collect all model results (CPU + GPU) ──
        // GPU tasks always exit 0 and emit a JSON (with error info on failure).
        // This prevents collect() deadlock — Nextflow only forwards outputs
        // from exit-0 tasks, so we must never exit 1 from GPU processes.
        ch_cpu_jsons = KREVIEW_EVAL_CPU_SINGLE.out.json_stats.collect()
        ch_all_jsons = params.run_gpu_eval
            ? ch_cpu_jsons
                .mix(KREVIEW_EVAL_GPU_SINGLE.out.gpu_results.collect())
                .flatten()
                .collect()
            : ch_cpu_jsons

        ch_cpu_joblib_collected = ch_cpu_joblib.collect()
        ch_all_joblib = params.run_gpu_eval
            ? ch_cpu_joblib_collected
                .mix(KREVIEW_EVAL_GPU_SINGLE.out.joblib_models.collect().ifEmpty([]))
                .flatten()
                .collect()
            : ch_cpu_joblib_collected

        // Step 4d: Build scoreboard (needs all JSONs)
        KREVIEW_SCOREBOARD(ch_all_jsons)

        // Step 5: Multimodal cross-evaluator evaluation (1 job) [optional]
        // Needs: OOF probs from CPU/GPU eval + super_matrix from FUSE
        if (params.run_multimodal_eval) {
            KREVIEW_EVAL_MULTIMODAL(
                KREVIEW_FUSE.out.super_matrix,
                ch_all_jsons
            )

            // Step 5b: Multimodal report — renders stacking dashboard
            if (!params.skip_report) {
                KREVIEW_REPORT_MULTIMODAL(
                    KREVIEW_EVAL_MULTIMODAL.out.multimodal_json,
                    KREVIEW_FUSE.out.super_matrix,
                )
            }
        }

        // Step 6: Report generation [optional]
        // Depends on selected matrices, model results, eval_stats,
        // selection_qc, joblib, and scoreboard.
        if (!params.skip_report) {
            KREVIEW_REPORT(
                KREVIEW_SELECT_SINGLE.out.matrix.collect(),
                ch_all_jsons,
                KREVIEW_SELECT_SINGLE.out.eval_stats.collect(),
                KREVIEW_SELECT_SINGLE.out.selection_qc.collect(),
                ch_all_joblib,
                KREVIEW_SCOREBOARD.out.scoreboard,
            )
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
