# Fragmentomics Feature Glossary

Our pipeline currently supports the high-throughput evaluation of 22 unique `FeatureEvaluator` modules (and growing!). These are designed to capture systemic genome-wide signatures of non-random DNA shedding from tumor cellular death.

Here is the classification structure of the features.

---

## 📏 Fragment Size Metrics
Tumor cfDNA is physically shorter than normal cfDNA because tumor cell-death occurs rapidly (necrosis) dodging the clean apoptotic laddering that fragments healthy cells safely on circulating histone boundaries.

- **FSD (Fragment Size Distribution):** Calculates the raw density profile of all fragment lengths across the sample.
- **FSC (Fragment Size Coverage):** Measures the specific ratio of short fragments (< 150bp) vs long fragments (150-220bp) at targeted loci across the exome. A high `short_to_long_ratio` powerfully correlates with ctDNA+.

## ✂️ Nucleosome & Cleavage Mapping
These features attempt to trace the physical proteins that were bound to the cfDNA right before apoptosis occurred.

- **WPS (Window Protection Score):** Evaluates depth profiles across narrow windows to identify where nucleosomes perfectly protected the DNA helix from circulating nucleases, or where Transcription Factor Binding Sites (TFBS) sat.
- **EndMotif / BreakPointMotif:** Analyzes the first 4-nucleotide sequence of every read. Some nucleases specifically slice at `CCCA` motifs. Shifts in specific tetramers serve as powerful cancer markers because tumor tissues up/downregulate specific nucleases (e.g. `DNASE1L3`, `DFFB`).

## 🔍 Structural Integrity
- **OCF (Orientation-aware cfDNA Fragmentation):** Looks at the specific strand orientation at DNA break thresholds to detect asymmetrical tissue shedding biases.

---

!!! tip "Adding a new biological feature?"
    If you've written a new metric in Rust inside the `Krewlyzer` core, and you need to register it into our Sklearn pipeline to find its statistical viability, please follow the [Adding a Feature](../developer/adding-a-feature.md) Python protocol!
