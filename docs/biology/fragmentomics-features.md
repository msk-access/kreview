# Fragmentomics Feature Glossary

Our pipeline currently supports the high-throughput evaluation of **26 unique `FeatureEvaluator` modules** (and growing!). These are designed to capture systemic genome-wide signatures of non-random DNA shedding from tumor cellular death.

!!! info "On-Target vs Genomewide"
    Many features have two variants: **OnTarget** (restricted to panel-capture regions, suffix `.ontarget.parquet`) and **Genomewide** (whole-genome coverage, suffix `.parquet`). On-target features are higher depth but narrower scope; genomewide features capture broader biological signals at lower depth.

---

## Complete Evaluator Registry

| Evaluator | Parquet Suffix | Tier | Category |
|-----------|---------------|------|----------|
| `FSC_gene` | `.FSC.gene.parquet` | 1 | Fragment Size |
| `FSCOnTarget` | `.FSC.ontarget.parquet` | 1 | Fragment Size |
| `FSCGenomewide` | `.FSC.parquet` | 1 | Fragment Size |
| `FSC_regions` | `.FSC.regions.parquet` | 1 | Fragment Size |
| `FsdOnTarget` | `.FSD.ontarget.parquet` | 1 | Fragment Size |
| `FsdGenomewide` | `.FSD.parquet` | 1 | Fragment Size |
| `FsrOnTarget` | `.FSR.ontarget.parquet` | 1 | Fragment Size |
| `FsrGenomewide` | `.FSR.parquet` | 1 | Fragment Size |
| `WPSPanel` | `.WPS.panel.parquet` | 2 | Nucleosome |
| `WPSGenome` | `.WPS.parquet` | 2 | Nucleosome |
| `WPSBackground` | `.WPS_background.parquet` | 2 | Nucleosome |
| `TfbsOnTarget` | `.TFBS.ontarget.parquet` | 2 | Nucleosome |
| `TfbsGenomewide` | `.TFBS.parquet` | 2 | Nucleosome |
| `EndMotifOnTarget` | `.EndMotif.ontarget.parquet` | 2 | Cleavage |
| `EndMotifGenomewide` | `.EndMotif.parquet` | 2 | Cleavage |
| `EndMotif1mer` | `.EndMotif1mer.parquet` | 2 | Cleavage |
| `BreakPointMotifOnTarget` | `.BreakPointMotif.ontarget.parquet` | 2 | Cleavage |
| `BreakPointMotifGenomewide` | `.BreakPointMotif.parquet` | 2 | Cleavage |
| `MdsOnTarget` | `.MDS.ontarget.parquet` | 2 | Motif Divergence |
| `MdsGenomewide` | `.MDS.parquet` | 2 | Motif Divergence |
| `MDSGene` | `.MDS.gene.parquet` | 2 | Motif Divergence |
| `MDSExon` | `.MDS.exon.parquet` | 2 | Motif Divergence |
| `AtacOnTarget` | `.ATAC.ontarget.parquet` | 2 | Accessibility |
| `AtacGenomewide` | `.ATAC.parquet` | 2 | Accessibility |
| `OCFOntarget` | `.OCF.ontarget.parquet` | 2 | Orientation |
| `OCFOfftarget` | `.OCF.offtarget.parquet` | 2 | Orientation |

---

## 📏 Fragment Size Metrics (Tier 1)

Tumor cfDNA tends to be shorter than normal cfDNA because rapid cell death (necrosis) disrupts the clean apoptotic nucleosome-wrapping that generates uniform ~167bp fragments from healthy cells.

- **FSD (Fragment Size Distribution):** Calculates the raw density profile of all fragment lengths across the sample.
- **FSC (Fragment Size Coverage):** Measures the specific ratio of short fragments (< 150bp) vs long fragments (150-220bp) at targeted loci across the exome. A high `short_to_long_ratio` is associated with ctDNA+ status.
- **FSR (Fragment Size Ratio):** Computes a single scalar short-to-long ratio as a global summary metric, both at panel-capture regions and genome-wide.

## ✂️ Nucleosome & Cleavage Mapping (Tier 2)

These features trace nucleosome positioning and nuclease cleavage patterns present in the cfDNA at the time of cell death.

- **WPS (Window Protection Score):** Evaluates depth profiles across narrow windows to identify where nucleosomes perfectly protected the DNA helix from circulating nucleases, or where TFBS sat.
- **TFBS (Transcription Factor Binding Sites):** Specifically measures the nucleosome-depleted regions at known transcription factor binding locations.
- **EndMotif / BreakPointMotif:** Analyzes the first 4-nucleotide sequence of every read. Specific nucleases cleave at preferred recognition sites (e.g. `CCCA`). Shifts in tetramer frequencies can serve as cancer markers because tumor tissues up-regulate or down-regulate specific nucleases (e.g. `DNASE1L3`, `DFFB`).
- **EndMotif1mer:** Single-base resolution motif analysis for maximum granularity.

## 🔍 Structural Integrity & Accessibility (Tier 2)

- **OCF (Orientation-aware cfDNA Fragmentation):** Looks at the specific strand orientation at DNA break thresholds to detect asymmetrical tissue shedding biases.
- **ATAC (Chromatin Accessibility):** Evaluates fragment coverage at ATAC-seq peak regions. Open chromatin regions in tumor tissue produce distinctive fragmentation patterns.
- **MDS (Motif Divergence Score):** Measures the statistical divergence of a sample's end-motif distribution from healthy baselines, available at gene-level, exon-level, and genome-wide resolution.

---

!!! tip "Adding a new biological feature?"
    If you've written a new metric in Rust inside the `Krewlyzer` core, and you need to register it into our Sklearn pipeline, follow the [Adding a Feature](../developer/adding-a-feature.md) guide!
