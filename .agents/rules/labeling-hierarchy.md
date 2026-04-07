# 4-Tier ctDNA Labeling Hierarchy

## Label Definitions (strict priority order)
1. **True ctDNA+**: Any ACCESS somatic variant matched by exact coordinates to paired IMPACT tissue sample (any VAF)
2. **Possible ctDNA+**: ≥min_variants somatic SNVs with VAF ≥ min_vaf, OR ≥1 somatic SV, OR ≥1 non-neutral CNA
3. **Possible ctDNA−**: Cancer patient with no qualifying alterations
4. **Healthy Normal**: Non-cancer plasma donor (from healthy samplesheet)

## Critical Rules
- IMPACT rescue is threshold-independent (any VAF counts if tissue-confirmed)
- Only SOMATIC events are used. GERMLINE and UNKNOWN are excluded.
- SV and CNA are binary (presence/absence). No tissue cross-reference for SV/CNA.
- Labels are mutually exclusive — a sample belongs to exactly one group.
- `relabel()` only re-applies SNV thresholds. IMPACT match, SV, and CNA are precomputed.

## Defaults
- `min_vaf = 0.01` (1%)
- `min_variants = 1`
