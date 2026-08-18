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
//     +---+---+---+---+
//     |       |   |   |
//  [ABLATE]  FUSE |   |        (optional: params.run_ablation)
//     |       |   |   |
//   MERGE_ABL |   |   |        (→ best_subset.json per evaluator)
//     |       |   |   |
//  EVAL_CPU  FUSE EVAL_GPU     (CPU ×N parallel, GPU ×N on gpushort)
//  (×N)      (1)  (×N)
//     |       |   |
//     +---+---+---+---+
//     |       |       |
//  SCOREBOARD |  MULTIMODAL_PREP (1)    → build stacking matrix
//     |       |       |
//     |       |  MULTIMODAL_SINGLE ×N   → scatter per model (CPU/GPU)
//     |       |       |
//     |       |  MULTIMODAL_ABLATION    → LOO (best model, CPU)
//     |       |       |
//     |       |  MULTIMODAL_MERGE       → unify JSON
//     |       |       |
//     +---+---+  (multimodal results feed the single REPORT, #79)
//         |
//       REPORT                 (needs matrices + JSONs + scoreboard + joblib)
//

// ── Module imports ──
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

// Multistage — feature ablation (optional, params.run_ablation)
include { KREVIEW_ABLATE_CPU_SINGLE } from '../modules/local/kreview/ablate_cpu_single'
include { KREVIEW_ABLATE_GPU_SINGLE } from '../modules/local/kreview/ablate_gpu_single'
include { KREVIEW_MERGE_ABLATION     } from '../modules/local/kreview/merge_ablation'

// Multistage — collect-only modules (need all evaluator results)
include { KREVIEW_SCOREBOARD        } from '../modules/local/kreview/scoreboard'

// Multistage — decomposed multimodal pipeline (prep → single × N → ablation → merge)
include { KREVIEW_MULTIMODAL_PREP       } from '../modules/local/kreview/multimodal_prep'
include { KREVIEW_MULTIMODAL_SINGLE_CPU } from '../modules/local/kreview/multimodal_single'
include { KREVIEW_MULTIMODAL_SINGLE_GPU } from '../modules/local/kreview/multimodal_single'
include { KREVIEW_MULTIMODAL_ABLATION   } from '../modules/local/kreview/multimodal_ablation'
include { KREVIEW_MULTIMODAL_MERGE      } from '../modules/local/kreview/multimodal_merge'

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
    ch_json_stats   = Channel.empty()
    ch_duckdb_db    = Channel.empty()

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
    // .ifEmpty guard: if all extracts are ignored, flatten() produces empty
    // channel — ifEmpty prevents deadlock in downstream .combine()/.collect()
    KREVIEW_SELECT_SINGLE(KREVIEW_EXTRACT.out.matrices.flatten().ifEmpty(Channel.empty()))

    // Step 4a: Feature ablation [optional, params.run_ablation]
    // Runs BEFORE eval to determine optimal feature subsets per fold.
    ch_best_subset = Channel.empty()
    if (params.run_ablation) {
        // CPU ablation (parallel, one per evaluator)
        KREVIEW_ABLATE_CPU_SINGLE(KREVIEW_SELECT_SINGLE.out.matrix)

        // GPU ablation [optional, runs in parallel with CPU ablation]
        if (params.run_gpu_eval) {
            // Pair matrix + eval_stats by evaluator name
            ch_gpu_ablate_input = KREVIEW_SELECT_SINGLE.out.matrix
                .map { f -> [f.baseName.replace('_matrix', ''), f] }
                .combine(
                    KREVIEW_SELECT_SINGLE.out.eval_stats
                        .map { f -> [f.baseName.replace('_eval_stats', ''), f] },
                    by: 0
                )
                .map { key, matrix, stats -> [matrix, stats] }

            KREVIEW_ABLATE_GPU_SINGLE(
                ch_gpu_ablate_input.map { it[0] },
                ch_gpu_ablate_input.map { it[1] }
            )

            // Pair CPU + GPU ablation results by evaluator name
            // .ifEmpty guard: if GPU ablation is ignored for all evaluators,
            // combine() would deadlock waiting for items that never arrive.
            ch_ablation_pairs = KREVIEW_ABLATE_CPU_SINGLE.out.ablation_json
                .map { f -> [f.baseName.replace('_ablation_cpu', ''), f] }
                .combine(
                    KREVIEW_ABLATE_GPU_SINGLE.out.ablation_json
                        .map { f -> [f.baseName.replace('_ablation_gpu', ''), f] }
                        .ifEmpty(Channel.empty()),
                    by: 0
                )
                .map { key, cpu_json, gpu_json -> [cpu_json, gpu_json] }

            KREVIEW_MERGE_ABLATION(
                ch_ablation_pairs.map { it[0] },
                ch_ablation_pairs.map { it[1] }
            )
        } else {
            // CPU-only ablation — pass sentinel for GPU
            KREVIEW_MERGE_ABLATION(
                KREVIEW_ABLATE_CPU_SINGLE.out.ablation_json,
                Channel.value(file('NO_GPU_ABLATION'))
            )
        }

        ch_best_subset = KREVIEW_MERGE_ABLATION.out.best_subset
    }

    // Step 4b: Per-evaluator CPU evaluation (×N, parallel)
    // When ablation is enabled, pair matrix with best_subset by evaluator name
    if (params.run_ablation) {
        // #60: join(remainder:true), NOT combine(by:0). combine is an inner join, so an
        // evaluator whose best_subset was never produced (its ablation failed and was
        // ignored upstream) would be SILENTLY DROPPED from eval — scientific data loss with
        // no error. This join is the last line of defence before eval: remainder:true keeps
        // the unmatched matrix (best_subset padded to null); we fall back to the
        // NO_BEST_SUBSET sentinel — identical to the ablation-off path — and log LOUDLY, so
        // the evaluator is degraded-but-present, never dropped. (best_subset keys are always
        // a subset of matrix keys, so the only remainder rows are matrices without a subset;
        // the filter guards the theoretical inverse.)
        ch_cpu_eval_input = KREVIEW_SELECT_SINGLE.out.matrix
            .map { f -> [f.baseName.replace('_matrix', ''), f] }
            .join(
                ch_best_subset
                    .map { f -> [f.baseName.replace('_best_subset', ''), f] },
                by: 0, remainder: true
            )
            .filter { it[1] != null }
            .map { key, matrix, bs ->
                if (bs == null) {
                    log.warn "[#60] ablation best_subset MISSING for evaluator '${key}' (CPU eval) — " +
                             "ablation likely failed and was ignored upstream. Falling back to " +
                             "full-feature eval (NO_BEST_SUBSET); evaluator is NOT dropped."
                }
                [matrix, bs ?: file('NO_BEST_SUBSET')]
            }

        KREVIEW_EVAL_CPU_SINGLE(
            ch_cpu_eval_input.map { it[0] },
            ch_cpu_eval_input.map { it[1] }
        )
    } else {
        KREVIEW_EVAL_CPU_SINGLE(
            KREVIEW_SELECT_SINGLE.out.matrix,
            Channel.value(file('NO_BEST_SUBSET'))
        )
    }
    ch_json_stats = KREVIEW_EVAL_CPU_SINGLE.out.json_stats

    // Step 4c: Per-evaluator GPU evaluation (×N, parallel, gpushort) [optional]
    // Runs in parallel with CPU eval — they are independent.
    // Pairs each matrix with its eval_stats for intelligent feature capping.
    if (params.run_gpu_eval) {
        // Pair matrix + eval_stats + best_subset by evaluator name
        ch_gpu_base = KREVIEW_SELECT_SINGLE.out.matrix
            .map { f -> [f.baseName.replace('_matrix', ''), f] }
            .combine(
                KREVIEW_SELECT_SINGLE.out.eval_stats
                    .map { f -> [f.baseName.replace('_eval_stats', ''), f] },
                by: 0
            )

        if (params.run_ablation) {
            // #60: join(remainder:true) — see the CPU eval note above. Same fix so GPU eval
            // does not silently drop an evaluator whose best_subset is missing.
            ch_gpu_input = ch_gpu_base
                .join(
                    ch_best_subset
                        .map { f -> [f.baseName.replace('_best_subset', ''), f] },
                    by: 0, remainder: true
                )
                .filter { it[1] != null }
                .map { key, matrix, stats, bs ->
                    if (bs == null) {
                        log.warn "[#60] ablation best_subset MISSING for evaluator '${key}' (GPU eval) — " +
                                 "falling back to full-feature eval (NO_BEST_SUBSET); evaluator is NOT dropped."
                    }
                    [matrix, stats, bs ?: file('NO_BEST_SUBSET')]
                }
        } else {
            ch_gpu_input = ch_gpu_base
                .map { key, matrix, stats -> [matrix, stats, file('NO_BEST_SUBSET')] }
        }

        KREVIEW_EVAL_GPU_SINGLE(
            ch_gpu_input.map { it[0] },
            ch_gpu_input.map { it[1] },
            ch_gpu_input.map { it[2] }
        )
    }

    // Step 4d: Fuse selected matrices → super-matrix (1 job, needs all)
    ch_all_selected = KREVIEW_SELECT_SINGLE.out.matrix.collect()
    KREVIEW_FUSE(ch_all_selected)

    // Collect all model results (CPU + GPU).
    // ifEmpty([]) prevents channel deadlock if some evaluators fail
    // with errorStrategy='ignore' (failed tasks emit no outputs).
    ch_cpu_jsons = KREVIEW_EVAL_CPU_SINGLE.out.json_stats.collect().ifEmpty([])
    ch_all_jsons = params.run_gpu_eval
        ? ch_cpu_jsons
            .mix(KREVIEW_EVAL_GPU_SINGLE.out.gpu_results.collect().ifEmpty([]))
            .flatten()
            .collect()
        : ch_cpu_jsons

    // Step 4d: Build scoreboard (needs all JSONs + the selection-QC sidecars — #108:
    // selection columns are sourced from the sidecars or explicitly "unknown", never
    // the legacy default label)
    KREVIEW_SCOREBOARD(
        ch_all_jsons,
        KREVIEW_SELECT_SINGLE.out.selection_qc.collect().ifEmpty(file('NO_SELECTION_QC'))
    )

    // #79: report-facing channels default to sentinels; the optional stages below
    // reassign them when they actually run (NO_* pattern, #97).
    ch_mm_report_jsons = Channel.value(file('NO_MULTIMODAL'))
    ch_report_ablation = Channel.value(file('NO_MERGED_ABLATION'))
    if (params.run_ablation) {
        ch_report_ablation = ch_best_subset.collect().ifEmpty(file('NO_MERGED_ABLATION'))
    }

    // Step 5: Multimodal cross-evaluator evaluation [optional]
    // Uses decomposed pipeline: prep → single × N → ablation → merge
    if (params.run_multimodal_eval) {
        // 5a: Prep — build stacking + raw matrices (CPU)
        KREVIEW_MULTIMODAL_PREP(
            ch_all_jsons,
            KREVIEW_FUSE.out.super_matrix
        )

        // 5b: Single — scatter per model (CPU + GPU in parallel)
        def cpu_models = (params.multimodal_models ?: 'rf,xgb').split(',')
            .collect { it.trim() }
        ch_cpu_model_names = Channel.of(cpu_models).flatten()

        // Determine raw features path (may not exist)
        ch_raw_matrix = KREVIEW_MULTIMODAL_PREP.out.raw_features_matrix
            .ifEmpty(file('NO_RAW_FEATURES'))

        KREVIEW_MULTIMODAL_SINGLE_CPU(
            ch_cpu_model_names,
            KREVIEW_MULTIMODAL_PREP.out.stacking_matrix,
            ch_raw_matrix,
            KREVIEW_MULTIMODAL_PREP.out.prep_metadata
        )

        // GPU models — only if requested
        ch_gpu_single_results = Channel.empty()
        if (params.multimodal_gpu_models) {
            def gpu_models = params.multimodal_gpu_models.split(',')
                .collect { it.trim() }
            ch_gpu_model_names = Channel.of(gpu_models).flatten()

            KREVIEW_MULTIMODAL_SINGLE_GPU(
                ch_gpu_model_names,
                KREVIEW_MULTIMODAL_PREP.out.stacking_matrix,
                ch_raw_matrix,
                KREVIEW_MULTIMODAL_PREP.out.prep_metadata
            )
            ch_gpu_single_results = KREVIEW_MULTIMODAL_SINGLE_GPU.out.single_result
        }

        // Collect all single results (CPU + GPU)
        ch_all_single_results = KREVIEW_MULTIMODAL_SINGLE_CPU.out.single_result
            .mix(ch_gpu_single_results)
            .collect()

        // 5c: Ablation — LOO using best model (CPU)
        KREVIEW_MULTIMODAL_ABLATION(
            KREVIEW_MULTIMODAL_PREP.out.stacking_matrix,
            ch_all_single_results
        )

        // 5d: Merge — combine all partial JSONs
        // #97: ablation is OPTIONAL input to merge. If MULTIMODAL_ABLATION fails
        // terminally (errorStrategy 'ignore'), its output channel is empty — without the
        // ifEmpty sentinel that starved this process, so MERGE and REPORT_MULTIMODAL
        // never ran and the whole multimodal tail was silently lost (iris v0.0.29 run).
        // The module already handles the NO_ABLATION sentinel; the workflow just never
        // sent it. Same pattern as NO_SCOREBOARD below.
        KREVIEW_MULTIMODAL_MERGE(
            ch_all_single_results,
            KREVIEW_MULTIMODAL_PREP.out.prep_metadata,
            KREVIEW_MULTIMODAL_ABLATION.out.ablation_results.ifEmpty(file('NO_ABLATION'))
        )

        // #79: the multimodal tab of the single-page report consumes the raw partial
        // JSONs (prep metadata + per-model stacking + LOO ablation). Collected with
        // ifEmpty so a failed optional stage degrades the tab instead of starving
        // KREVIEW_REPORT (#97 pattern). The dedicated REPORT_MULTIMODAL process is gone —
        // one report, one implementation.
        ch_mm_report_jsons = KREVIEW_MULTIMODAL_PREP.out.prep_metadata
            .mix(
                KREVIEW_MULTIMODAL_SINGLE_CPU.out.single_result,
                ch_gpu_single_results,
                KREVIEW_MULTIMODAL_ABLATION.out.ablation_results,
            )
            .collect()
            .ifEmpty(file('NO_MULTIMODAL'))
    }

    // Step 6: Report generation [optional] — #79 single-page report.
    // Consumes aggregates only (labels, model JSONs, selection QC, scoreboard,
    // multimodal + ablation JSONs); matrices, eval_stats and joblib models are no
    // longer needed since SHAP left the render path.
    if (!params.skip_report) {
        ch_scoreboard = KREVIEW_SCOREBOARD.out.scoreboard.ifEmpty(file('NO_SCOREBOARD'))
        KREVIEW_REPORT(
            KREVIEW_LABEL.out.labels,
            ch_all_jsons,
            KREVIEW_SELECT_SINGLE.out.selection_qc.collect(),
            ch_scoreboard,
            ch_mm_report_jsons,
            ch_report_ablation,
        )
        ch_html_reports = KREVIEW_REPORT.out.html_report
    }


    emit:
    html_reports = ch_html_reports
    json_stats   = ch_json_stats
    duckdb_db    = ch_duckdb_db
}
