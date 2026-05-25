// ---------------------------------------------------------
// KREVIEW_EVAL_GPU — Per-evaluator GPU evaluation
// ---------------------------------------------------------
// Runs `kreview eval gpu` on per-evaluator feature matrices
// using TabPFN and/or TabICL foundation models.
// Fine-tuning is ON by default. Use gpu_no_finetune to disable.
//
// This process is configured with GPU resource labels so SLURM
// schedules it on GPU-capable nodes.
//
// Inputs:  matrices_dir (directory of *_matrix.parquet files)
// Outputs: gpu_output/*_model_results.json
// ---------------------------------------------------------

process KREVIEW_EVAL_GPU {
    tag "kreview-eval-gpu"
    label 'process_gpu'

    input:
    path(matrices_dir)

    output:
    path "gpu_output/*_model_results.json", emit: gpu_results

    script:
    def models_arg = params.gpu_models ?: 'tabpfn,tabicl'
    def device_arg = params.gpu_device ?: 'cuda'
    def finetune_flag = params.gpu_no_finetune ? '--no-finetune' : ''
    def epochs_arg = params.gpu_finetune_epochs ?: 30
    def resume_flag = params.resume_eval ? '--resume' : ''
    """
    set -euo pipefail

    mkdir -p gpu_output

    PYTHONUNBUFFERED=1 kreview eval gpu \\
        --matrices-dir ${matrices_dir} \\
        --models ${models_arg} \\
        --device ${device_arg} \\
        ${finetune_flag} \\
        --finetune-epochs ${epochs_arg} \\
        --cv-folds ${params.cv_folds ?: 5} \\
        ${resume_flag} \\
        --seed ${params.seed ?: 42} \\
        ${params.deterministic ? '--deterministic' : '--no-deterministic'} \\
        --output gpu_output
    """
}
