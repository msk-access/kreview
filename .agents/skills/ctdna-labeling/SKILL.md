---
name: ctdna-labeling
description: 4-tier ctDNA labeling hierarchy with IMPACT tissue rescue, configurable VAF/variant thresholds.
---

# ctDNA Labeling Logic

## When to use this skill
- Implementing or modifying the CtDNALabeler class
- Understanding label assignment logic
- Debugging label discrepancies

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

### 3. Possible ctDNA− (no signal)
- **Criterion**: Cancer patient, NOT True ctDNA+ or Possible ctDNA+
- These are actively assessed cancer samples with no qualifying alterations

### 4. Healthy Normal
- **Criterion**: From healthy samplesheet (47 XS1 + 21 XS2 = 68 donors)
- NOT cancer patients

## Filtering Rules
- Only `Mutation_Status == 'SOMATIC'` variants are used
- GERMLINE and UNKNOWN are excluded
- Only ACCESS samples (GENE_PANEL in {ACCESS129, ACCESS146}) are eligible
- VAF = t_alt_count / (t_alt_count + t_ref_count)
