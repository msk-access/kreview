// ---------------------------------------------------------
// KREVIEW_EVAL_GPU_SINGLE — Per-evaluator GPU evaluation
// ---------------------------------------------------------
// Runs `kreview eval gpu` on a SINGLE evaluator matrix using
// TabPFN and/or TabICL foundation models.
//
// Used in multistage mode to scatter GPU evaluation across
// evaluators in parallel (×N jobs on gpushort partition).
//
// Container: Uses the GPU container (kreview:vX.Y.Z-gpu)
//            via the 'process_gpu' label in nextflow.config.
// SLURM:     Routed to gpushort partition with --gres=gpu:1.
//            Singularity --nv flag exposes host NVIDIA drivers.
//
// Data flow (multistage):
//   KREVIEW_SELECT_SINGLE.out.matrix (per-evaluator)
//     → KREVIEW_EVAL_GPU_SINGLE ×N (parallel, gpushort)
//     → collect → KREVIEW_EVAL_MULTIMODAL
// ---------------------------------------------------------

process KREVIEW_EVAL_GPU_SINGLE {
    tag "eval-gpu-${matrix.baseName.replace('_matrix', '')}"
    label 'process_gpu'
    publishDir "${params.outdir}/models/gpu", mode: 'copy'

    input:
    path(matrix)  // Single selected *_matrix.parquet

    output:
    path "*_model_results.json", emit: gpu_results

    script:
    def evaluator     = matrix.baseName.replace('_matrix', '')
    def models_arg    = params.gpu_models          ?: 'tabpfn,tabicl'
    def device_arg    = params.gpu_device          ?: 'cuda'
    def finetune_flag = params.gpu_no_finetune     ? '--no-finetune' : ''
    def epochs_arg    = params.gpu_finetune_epochs ?: 30
    def cv_folds      = params.cv_folds            ?: 5
    """
    set -euo pipefail

    # Stage single matrix into directory (kreview eval gpu expects --matrices-dir)
    mkdir -p matrices
    cp ${matrix} matrices/

    echo "=== KREVIEW_EVAL_GPU_SINGLE: ${evaluator} ==="
    echo "Input:  ${matrix}"
    echo "Device: ${device_arg}"
    echo "Models: ${models_arg}"

    PYTHONUNBUFFERED=1 kreview eval gpu \\
        --matrices-dir matrices \\
        --models ${models_arg} \\
        --device ${device_arg} \\
        ${finetune_flag} \\
        --finetune-epochs ${epochs_arg} \\
        --cv-folds ${cv_folds} \\
        --output .

    # Verify output exists (fail loudly, not silently)
    if [ ! -f *_model_results.json ]; then
        echo "ERROR: No GPU model results produced for ${evaluator}" >&2
        exit 1
    fi

    echo "Output: \$(ls *_model_results.json)"
    echo "=== KREVIEW_EVAL_GPU_SINGLE: ${evaluator} DONE ==="
    """
}
