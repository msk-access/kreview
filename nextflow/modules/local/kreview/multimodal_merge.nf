// ---------------------------------------------------------
// KREVIEW_MULTIMODAL_MERGE — Combine partial results
// ---------------------------------------------------------
// Stage 4 of decomposed multimodal pipeline.
// Merges prep metadata, per-model stacking results, and
// ablation results into a unified multimodal_results.json
// matching the monolithic schema.
//
// Runs on CPU.  Very lightweight (JSON merge only).
// ---------------------------------------------------------

process KREVIEW_MULTIMODAL_MERGE {
    tag "multimodal-merge"
    label 'process_low'
    publishDir "${params.outdir}/models/multimodal", mode: 'copy'

    input:
    path(stacking_results)   // Collected stacking_*_results.json from single
    path(prep_metadata)      // prep_metadata.json from prep
    path(ablation_results)   // ablation_results.json or NO_ABLATION sentinel

    output:
    path "merge_out/multimodal_results.json", emit: multimodal_json

    script:
    def ablation_flag = ablation_results.name != 'NO_ABLATION' ? "--ablation-results ${ablation_results}" : ""
    """
    set -euo pipefail
    mkdir -p merge_out stacking_results_dir

    # Stage stacking result JSONs into a directory
    for f in ${stacking_results}; do
        cp "\$f" stacking_results_dir/ 2>/dev/null || true
    done

    PYTHONUNBUFFERED=1 kreview eval multimodal merge \\
        --stacking-results-dir stacking_results_dir \\
        --prep-metadata ${prep_metadata} \\
        ${ablation_flag} \\
        --output merge_out
    """
}
