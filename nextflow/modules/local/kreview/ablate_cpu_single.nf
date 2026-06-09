// ---------------------------------------------------------
// KREVIEW_ABLATE_CPU_SINGLE — Per-evaluator CPU feature ablation
// ---------------------------------------------------------
// Runs nested CV feature group ablation using LR, RF, XGB
// for a SINGLE evaluator matrix.
//
// Finds the optimal feature group subset per model per fold.
// Output consumed by MERGE_ABLATION → EVAL_CPU_SINGLE.
//
// Data flow:
//   KREVIEW_SELECT_SINGLE.out.matrix (per-evaluator)
//     → KREVIEW_ABLATE_CPU_SINGLE ×N (parallel)
//     → collect → KREVIEW_MERGE_ABLATION (per-evaluator)
//     → KREVIEW_EVAL_CPU_SINGLE (with --best-subset)
// ---------------------------------------------------------

process KREVIEW_ABLATE_CPU_SINGLE {
    tag "ablate-cpu-${matrix.baseName.replace('_matrix', '')}"
    label 'process_medium'
    publishDir "${params.outdir}/ablation/cpu", mode: 'copy'

    input:
    path(matrix)  // Single selected *_matrix.parquet

    output:
    path "*_ablation_cpu.json", emit: ablation_json

    script:
    def evaluator    = matrix.baseName.replace('_matrix', '')
    def outer_folds  = params.cv_folds ?: 5
    def inner_folds  = params.ablation_inner_folds ?: 3
    def seed         = params.seed ?: 42
    """
    set -euo pipefail

    echo "=== KREVIEW_ABLATE_CPU_SINGLE: ${evaluator} ==="
    echo "Input: ${matrix}"
    echo "Outer folds: ${outer_folds}, Inner folds: ${inner_folds}"

    PYTHONUNBUFFERED=1 kreview eval ablate cpu \\
        --matrix ${matrix} \\
        --n-outer-folds ${outer_folds} \\
        --n-inner-folds ${inner_folds} \\
        --seed ${seed} \\
        --output .

    # Verify output
    if [ ! -f *_ablation_cpu.json ]; then
        echo "ERROR: No ablation results for ${evaluator}" >&2
        exit 1
    fi

    echo "Output: \$(ls *_ablation_cpu.json)"
    echo "=== KREVIEW_ABLATE_CPU_SINGLE: ${evaluator} DONE ==="
    """
}
