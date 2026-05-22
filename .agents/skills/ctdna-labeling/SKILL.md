---
name: ctdna-labeling
description: 5-tier ctDNA labeling hierarchy with IMPACT tissue rescue, CH hotspot filtering, configurable VAF/variant thresholds, and continuous VAF regression stats.
---

# ctDNA Labeling Logic

## When to use this skill
- Implementing or modifying the CtDNALabeler class
- Understanding label assignment logic
- Debugging label discrepancies
- Configuring CH hotspot filtering

## Priority Hierarchy (strict order)

### 1. True ctDNA+ (tissue-confirmed)
- **Criterion**: Any ACCESS somatic variant with EXACT coordinate match in paired IMPACT tissue
- **Match key**: (Chromosome, Start_Position, End_Position, Reference_Allele, Tumor_Seq_Allele2)
- **VAF**: Any (threshold-independent)
- **Requires**: Paired IMPACT sample (63.8% of patients)

### 2. Possible ctDNA+ (signal detected)
- **Criterion**: NOT True ctDNA+ AND any of:
  - ≥ `min_variants` somatic SNVs with VAF ≥ `min_vaf`
  - ≥ 1 somatic SV (binary)
  - ≥ 1 non-neutral CNA (value ≠ 0)
- **CH demotion**: If CH hotspot filtering is enabled, samples with ONLY CH variants
  (n_non_ch_variants == 0) and no SV/CNA/IMPACT evidence are demoted to Possible ctDNA−

### 3. Possible ctDNA− (no signal)
- **Criterion**: Cancer patient, NOT True ctDNA+ or Possible ctDNA+
- These are actively assessed cancer samples with no qualifying alterations

### 4. Healthy Normal
- **Criterion**: From healthy samplesheet (47 XS1 + 21 XS2 = 68 donors)
- NOT cancer patients

### 5. Insufficient Data
- **Criterion**: Cancer patient with no SNV/SV/CNA signal AND total_fragments_pf < `min_fragments`
- Separates low-sequencing-depth samples from true signal-negative samples

## Filtering Rules
- Only `Mutation_Status == 'SOMATIC'` variants are used
- GERMLINE and UNKNOWN are excluded
- Only ACCESS samples (GENE_PANEL in {ACCESS129, ACCESS146}) are eligible
- VAF = t_alt_count / (t_alt_count + t_ref_count)

## CH Hotspot Filtering (optional)
- Activated via `--ch-hotspot-maf` CLI flag or `LabelConfig(ch_hotspot_maf=Path(...))`
- A curated MAF file of known CH variants (DNMT3A, TET2, ASXL1, JAK2, etc.)
- Loaded by `load_ch_hotspots()` → `set[tuple]` of (chrom, pos, ref, alt) keys
- Each somatic variant is tagged `is_ch` based on coordinate match
- Output columns: `n_ch_variants`, `n_non_ch_variants`
- **Demotion rule**: Possible ctDNA+ with n_non_ch_variants == 0 AND no SV/CNA/IMPACT → Possible ctDNA−
- Demotion only fires when CH is the **sole evidence**

## Continuous VAF Statistics
- `mean_vaf`: Mean VAF of VAF-passing variants (for Stage 2 Quantifier regression targets)
- `std_vaf`: Std deviation of VAF-passing variants (0.0 if ≤1 variant)
- Computed only from passing variants (VAF ≥ `min_vaf`), not from all somatic variants
- Zero-filled for samples with no passing variants and for healthy volunteers
