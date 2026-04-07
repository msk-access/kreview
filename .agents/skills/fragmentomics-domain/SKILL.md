---
name: fragmentomics-domain
description: cfDNA fragmentomics biology — what each feature measures and how to interpret it for ctDNA detection.
---

# cfDNA Fragmentomics Domain Knowledge

## When to use this skill
- Implementing a new feature evaluator
- Interpreting evaluation results
- Writing documentation or exploration cells

## Biology Background
Cell-free DNA (cfDNA) in plasma is released during cell death. Cancer cells
contribute "circulating tumor DNA" (ctDNA) with distinct fragmentation patterns:

1. **Shorter fragments** — ctDNA tends to be shorter than normal cfDNA
2. **Altered nucleosome positioning** — different WPS patterns at regulatory regions
3. **Epigenetic signatures** — methylation and chromatin states from tissue of origin
4. **End motif preferences** — DNA cleavage enzymes leave characteristic motifs

## Feature Interpretation

| Feature | What it measures | Direction in ctDNA+ |
|---|---|---|
| FSC core_short_ratio | Fraction of 120-150bp fragments | ↑ increased |
| FSR short_long_ratio | Short / Long fragment ratio | ↑ increased |
| MDS score | Global methylation from fragment ends | Variable |
| OCF z-score | Tissue-of-origin signal strength | ↑ if tissue contributing |
| ATAC z-score | Chromatin accessibility deviation from normal | ↑ or ↓ depending on mark |
| WPS periodicity_score | Regularity of nucleosome spacing | ↓ disrupted |
| EndMotif entropy | Diversity of end motifs | Changed |

## Confounders
- **Sequencing depth** (total_fragments) — many features are depth-dependent
- **GC bias** — addressed by GC correction in FSC.ontarget vs FSC (uncorrected)
- **Panel design** — XS1 vs XS2 have different target regions and probe designs
