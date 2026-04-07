# cfDNA Fragmentomics Domain Knowledge

## Fragment-Only Approach
This framework evaluates fragmentomics features exclusively. Mutations are used
ONLY for labeling (ground truth), NOT for feature computation.

## Key Features and Biological Significance

### Tier 1 (Fragmentation)
- **FSC**: Fragment Size Coverage — GC-corrected fragment counts in 6 size bins per 100kb
- **FSD**: Fragment Size Distribution — size histogram per chromosome arm (mono/di-nucleosomal peaks)
- **FSR**: Fragment Short/Long Ratio — ratio of short (<150bp) to long (>250bp) fragments

### Tier 2 (Epigenetics + Nucleosome)
- **MDS**: Methylation Deconvolution Score — CpG methylation status from fragment ends
- **OCF**: Orientation-aware Cell-free Fragment — tissue-of-origin deconvolution (7 tissues)
- **ATAC/TFBS**: Chromatin accessibility at functional sites
- **WPS**: Windowed Protection Score — nucleosome positioning signal

### Tier 3 (End Motifs)
- **EndMotif**: 4-mer DNA end motif frequencies (256 motifs)
- **BreakPointMotif**: Breakpoint-adjacent motifs
- **EndMotif1mer**: Single-base end composition (A/C/G/T fractions)

## Healthy Controls
- 47 XS1 donors + 21 XS2 donors = 68 healthy normals
- These are non-cancer plasma donors — they define the "normal" distribution
