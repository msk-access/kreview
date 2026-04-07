---
name: cbioportal-parsing
description: How to parse cBioPortal MAF, SV, CNA, and clinical files for the labeling pipeline.
---

# cBioPortal File Parsing

## When to use this skill
- Loading data_mutations_extended.txt (MAF)
- Loading data_sv.txt (structural variants)
- Loading data_CNA.txt (copy number)
- Loading data_clinical_sample.txt or data_clinical_patient.txt

## File Formats

### MAF (data_mutations_extended.txt)
- Tab-separated, comment lines start with `#`
- Key columns: Tumor_Sample_Barcode, Mutation_Status, Chromosome,
  Start_Position, End_Position, Reference_Allele, Tumor_Seq_Allele2,
  t_ref_count, t_alt_count
- VAF = t_alt_count / (t_alt_count + t_ref_count)

### SV (data_sv.txt)
- Tab-separated
- Key columns: Sample_ID, SV_Status, Class
- Filter: SV_Status == 'SOMATIC'

### CNA (data_CNA.txt)
- Wide matrix: Hugo_Symbol × sample columns
- Values: -2 (homodel), -1.5 (deep loss), 0 (neutral), 2 (amp)
- Non-zero = CNA event present

### Clinical (data_clinical_sample.txt, data_clinical_patient.txt)
- Tab-separated with 4-line `#` header (skip with `comment='#'`)
- GENE_PANEL column identifies ACCESS vs IMPACT samples
- ACCESS panels: ACCESS129, ACCESS146
- IMPACT panels: IMPACT341, IMPACT410, IMPACT468, IMPACT505
