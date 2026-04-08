# Evaluator Feature Registry

This documentation is directly synthesized from the `nbs/features/*.ipynb` Jupyter notebooks. These notebooks act as the active execution environment for each specific biological feature. During the CI compilation step, they are automatically transcoded into the python classes below.

The `registry.py` module loops through all of these exported classes and automatically registers them into the `kreview` execution engine!

---

## 📏 Fragment Size Coverage & Distributions
These features measure length distortions in circulating blood DNA caused by necrotic tumor shedding biases.

::: kreview.features.fsc_gene
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.fsc_binlevel
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.fsc_regions
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.fsd
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.fsr
    options:
      show_root_heading: true
      show_source: false

---

## ✂️ Nucleosome Protection (WPS & TFBS)
Measures the physical blockade signatures left by transcription factors and wrapped DNA Histones before DNAse nuclease shedding.

::: kreview.features.wps_panel
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.wps_genomewide
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.wps_background
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.tfbs
    options:
      show_root_heading: true
      show_source: false

---

## 🛑 Cleavage Signatures (EndMotifs)
Models the specific micro-nuclease patterns (like DNASE1L3) structurally slicing accessible DNA at `CCCA` junctions.

::: kreview.features.endmotif
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.endmotif_1mer
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.breakpoint_motif
    options:
      show_root_heading: true
      show_source: false

---

## 🧬 Diagnostic Motifs
Evaluates macro-scale localized sequence aberrations.

::: kreview.features.mds
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.mds_gene
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.mds_exon
    options:
      show_root_heading: true
      show_source: false

---

## 🗺️ Accessibility & Orientation
::: kreview.features.atac
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.ocf_ontarget
    options:
      show_root_heading: true
      show_source: false
::: kreview.features.ocf_offtarget
    options:
      show_root_heading: true
      show_source: false
