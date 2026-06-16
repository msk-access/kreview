// ---------------------------------------------------------
// KREVIEW_SCOREBOARD — Cross-evaluator scoreboard aggregation
// ---------------------------------------------------------
// Reads all *_model_results.json (CPU) and *_gpu_model_results.json
// (GPU) files, merges them per evaluator via Python helpers, and
// produces a unified scoreboard ranking table.
//
// Runs AFTER all CPU/GPU eval jobs complete (needs all JSONs).
// Produces scoreboard_combined__all.parquet consumed by REPORT.
// ---------------------------------------------------------

process KREVIEW_SCOREBOARD {
    tag "kreview-scoreboard"
    label 'process_medium'
    publishDir "${params.outdir}", mode: 'copy'

    input:
    path(model_results)  // Collected CPU + GPU JSONs

    output:
    path "scoreboard_combined__all.parquet", emit: scoreboard
    path "scoreboard_combined__all.csv",     emit: scoreboard_csv

    script:
    """
    set -euo pipefail

    # All JSONs are symlinked in the work directory by Nextflow — no staging needed.
    # Python load_all_model_results() natively discovers and merges CPU+GPU JSONs.
    python3 << 'EOF'
import traceback, sys
from kreview.scoreboard import build_scoreboard
from pathlib import Path

try:
    sb = build_scoreboard(Path('.'))
    sb.to_parquet('scoreboard_combined__all.parquet')
    sb.to_csv('scoreboard_combined__all.csv', index=False)
except Exception as e:
    print(f'SCOREBOARD ERROR: {e}', file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

print(f'Scoreboard: {len(sb)} evaluators', flush=True)
if len(sb) > 0:
    print(f"  Best: {sb.iloc[0]['evaluator']} (AUC={sb.iloc[0]['best_auc']:.3f})", flush=True)
EOF
    """
}
