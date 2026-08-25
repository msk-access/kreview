# 6-Tier ctDNA Labeling Hierarchy

## Label Definitions (strict priority order)
1. **True ctDNA+**: Any ACCESS somatic variant matched by exact coordinates to paired IMPACT tissue sample (any VAF)
2. **Possible ctDNA+**: ≥min_variants somatic SNVs with VAF ≥ min_vaf, OR ≥1 somatic SV, OR ≥1 non-neutral CNA
3. **Possible ctDNA−**: Cancer patient with no qualifying alterations
4. **Healthy Normal**: Non-cancer plasma donor (from healthy samplesheet)
5. **Insufficient Data**: Cancer patient with no SNV/SV/CNA signal AND total_fragments_pf < min_fragments (separates low-depth from true signal-negative). NB `total_fragments_pf` is NaN-safe by treating missing depth as infinite, so this tier does not fire at all when depth metadata is absent (#122)
6. **Undetermined**: Possible ctDNA+ whose only evidence is clonal hematopoiesis — **excluded from binary classification**, not moved into the negative class

Optional CH-hotspot demotion (`--ch-hotspot-maf`): a Possible ctDNA+ whose only evidence is
CH variants (n_non_ch_variants == 0, no SV/CNA/IMPACT) is demoted to **Undetermined**
(`kreview/labels.py`, `LABEL_UNDETERMINED`) and therefore leaves the modelled set entirely.
It is NOT demoted to Possible ctDNA−, which would silently put CH-only samples in the
negative class.
See the `ctdna-labeling` skill for the full CH logic and continuous-VAF stats.

## Critical Rules
- IMPACT rescue is threshold-independent (any VAF counts if tissue-confirmed)
- Only SOMATIC events are used. GERMLINE and UNKNOWN are excluded.
- SV and CNA are binary (presence/absence). No tissue cross-reference for SV/CNA.
- Labels are mutually exclusive — a sample belongs to exactly one group.
- `relabel()` only re-applies SNV thresholds. IMPACT match, SV, and CNA are precomputed.

## Defaults
- `min_vaf = 0.01` (1%)
- `min_variants = 1`
