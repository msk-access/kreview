# ctDNA Labeling Engine

`kreview` evaluates computational fragmentomic features by measuring how accurately they distinguish tumor-derived circulating tumor DNA (ctDNA) from normal apoptotic background DNA.

To do this, it first establishes a rigid "Ground Truth" label matrix utilizing the `CtDNALabeler` engine (`kreview.labels.py`), relying strictly on MSK-IMPACT orthogonal tissue assays.

---

## 🔬 The Biological Assumption

Unlike standard genomics which calls somatic variants directly from the blood, **Fragmentomics** relies on subtle physical signatures—like fragment sizes, nucleosome imprints, and cleavage end-motifs—measured broadly across the entire epigenome.

Because we are evaluating *new* experimental fragmentomic models, we need incontrovertible proof that the patient sample actually *has* ctDNA present. For this, we look at **Variant Allele Frequency (VAF)**.

$$
VAF = \frac{\text{Alternate Allele Depth (t\_alt\_count)}}{\text{Total Depth (t\_ref\_count + t\_alt\_count)}}
$$

If a sample contains somatic Single Nucleotide Variants (SNVs) with a high detectable VAF, or massive Copy Number Alterations (CNAs)/Structural Variants (SVs), then the physical tumor footprint in the blood is high.

---

## 🏷️ The 4-Tier Labeling Hierarchy

`kreview` evaluates samples strictly by the following labels:

### 1. True ctDNA+
The gold standard. This label is granted **only** if one of three conditions is met:
- An SNV mutation detected in the blood cfDNA perfectly matches a somatic mutation detected in the patient's matched solid-tissue MSK-IMPACT biopsy.
- A macroscopic structural variant (SV) is positively called.
- Wide-scale somatic Copy Number Alterations (CNAs) are detected.

### 2. Possible ctDNA+
The silver standard. The sample lacks a matched MSK-IMPACT tissue biopsy (or the biopsy was negative), but the global MSK-ACCESS assay still detected generic somatic SNVs passing the configured stringency threshold:

$$
VAF \ge 0.01 \quad \text{and} \quad n_{variants} \ge 1
$$
*(Configurable via the `--chunk-size` or Python configs)*.

### 3. Possible ctDNA−
Symptomatic cancer patients whose blood cfDNA draws generated completely zeroes across the board: **No SNVs, No SVs, No CNAs**. While they have cancer, their systemic shedding rate is too low for traditional orthogonal validation. 

### 4. Healthy Normal
True negative controls. Drawn entirely from the MSK `XS1` and `XS2` healthy volunteer sequencing runs. Their data establishes the baseline apoptotic fragmentation profile.

---

!!! warning "QC Gate: Insufficient Data"
    If a `Possible ctDNA−` sample shows absolutely no cancer signal, AND their sequencing coverage yielded `< 2000` total fragments, the pipeline scrubs them into an **Insufficient Data** bucket. They will be entirely excluded from the Machine Learning algorithms so drop-out noise doesn't corrupt the models!
