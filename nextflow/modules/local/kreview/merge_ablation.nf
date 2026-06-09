// ---------------------------------------------------------
// KREVIEW_MERGE_ABLATION — Per-evaluator ablation merge
// ---------------------------------------------------------
// Merges CPU + GPU ablation JSONs into a single best_subset.json
// that tells EVAL_CPU/EVAL_GPU which features to use per fold.
//
// Data flow:
//   ABLATE_CPU_SINGLE.out + ABLATE_GPU_SINGLE.out
//     → KREVIEW_MERGE_ABLATION ×N (per-evaluator)
//     → KREVIEW_EVAL_CPU_SINGLE (--best-subset)
//     → KREVIEW_EVAL_GPU_SINGLE (--best-subset)
// ---------------------------------------------------------

process KREVIEW_MERGE_ABLATION {
    tag "merge-ablation-${cpu_json.baseName.replace('_ablation_cpu', '')}"
    label 'process_low'
    publishDir "${params.outdir}/ablation/merged", mode: 'copy'

    input:
    path(cpu_json)   // *_ablation_cpu.json
    path(gpu_json)   // *_ablation_gpu.json (or NO_GPU_ABLATION sentinel)

    output:
    path "*_best_subset.json", emit: best_subset

    script:
    def evaluator = cpu_json.baseName.replace('_ablation_cpu', '')
    """
    set -euo pipefail

    echo "=== KREVIEW_MERGE_ABLATION: ${evaluator} ==="

    # Build GPU flag — skip if sentinel file
    GPU_FLAG=""
    if [ -f "${gpu_json}" ] && [ "${gpu_json}" != "NO_GPU_ABLATION" ]; then
        GPU_FLAG="--gpu-json ${gpu_json}"
    fi

    PYTHONUNBUFFERED=1 kreview eval ablate merge \\
        --cpu-json ${cpu_json} \\
        \$GPU_FLAG \\
        --output .

    if [ ! -f *_best_subset.json ]; then
        echo "ERROR: No merged results for ${evaluator}" >&2
        exit 1
    fi

    echo "Output: \$(ls *_best_subset.json)"
    echo "=== KREVIEW_MERGE_ABLATION: ${evaluator} DONE ==="
    """
}
