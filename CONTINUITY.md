# CONTINUITY — kreview

**Phase.** Engineering is in maintenance and has been since 17 Sep. The work is evaluation
science, defending it, and now a **single re-baseline** that every other number waits behind.
Four adversarial-review rounds are closed on measurement rather than argument. The binding
constraints are cluster access and one upstream release, not developer time.

**Headline as last shipped (v0.0.33, and not re-derivable locally — see §2).** AUC **0.845**
against verified within-patient negatives, sensitivity **48.3% [0.424, 0.519]** at 98%
specificity, LOD50 **3.54% max VAF ≈ 7.1% tumor fraction**, scoped to aggregated-feature panel
fragmentomics rather than to cfDNA physics.

> ⚠️ **Everything above is about to be superseded.** The patient-grouped CV fix and the
> krewlyzer fragment-model release both change the numbers, and they are batched into one
> production run (§3, Track R). Quote v0.0.33 figures only with the tag attached.

---

## 1. Where we are (verified 19 Nov 2026)

**Code is exactly where it was on 17 Sep.** `develop` at `cb69bdb`, zero commits since, last
tag `v0.0.33`, no open PRs. Open issues: #121 (research roadmap), #144 and #145 (CI scoping).
The last comment on #121 is the round-4 audit from 9 Sep.

**Nothing ran on the cluster.** D2 was never submitted; there is no re-label output anywhere.
The September recommendation to submit it first is **superseded** — see Track R.

**What shipped, historically.** v0.0.33 on 25 Aug (PyPI, GHCR, versioned docs). Dual-anchor
operating points and per-sample depth columns (#122/#123 via #125); the report's visual rebuild
(#126); the Nextflow DAG in Methods and Run diagnostics (#127); the verification-bias ladder
(#136); patient-clustered intervals and the threshold-vs-clustering decomposition (#132); the
subgroup floor and tier composition (#134); taxonomy and release-guide corrections (#137/#138);
CI path scoping (#142); job-wrapper provenance (#146); the Context7 standing rule (#147).

**Science, as it stands.** Modeling is saturated *within aggregated-feature representations*.
The tumor-informed TN anchor replaced the 68-donor anchor and is what makes the operating point
defensible, and incidentally what makes the ≤4.1% contamination bound computable. Detection is a
clean sigmoid in tumor burden. Labels are not the ceiling. Fragmentomics tracks current shedding
and does not anticipate genotype conversion.

**Review.** Four rounds closed. Two of our claims withdrawn, one partly upheld against us, four
of their objections refuted with data, three of their own withdrawn by them, one leakage pathway
disclosed before they found it, and one defect in every interval we had sent self-disclosed. Their
qTN contamination bound (≤4.1%, conservative in direction) is sound and worth keeping.

### 1a. Round-4 findings not yet acted on (9 Sep, measured, nothing shipped)

| finding | status |
|---|---|
| Their validation of the interval decomposition is an **algebraic identity**, so it confirms nothing | disclosed on #121, not yet in the response |
| The decomposition ratios are **Monte Carlo noise at `n_boot=400`**. Converged: deff 1.184 / 1.087, inflation 10.91 / 17.08. The sub-1 value they queried is noise, not a mechanism | needs a code fix, Track B |
| `pct_true_pos` does **not** predict subgroup AUC (rho +0.074, p=0.82 on the primary; median −0.126 across 26) | measured, refutes their item 10 |
| **Multi-sample subset holds the operating point**: 0.4695 [0.4304, 0.5147] vs 0.4834 pooled, and higher at 99% spec | answers their item 6, belongs in the report |
| A global threshold realizes **99.0% spec on multi-sample and 96.6% on single-draw** patients | new, generalizes B4 to a second axis |
| Retinoblastoma was **not** excluded by the subgroup gate, contrary to their §4 | correction owed |
| Our quoted LOD (4–5% VAF / 8–10% TF) disagrees with the shipped payload (3.54% / 7.08%) | self-penalizing, still an inconsistency |

### 1b. Decisions taken 18–19 Nov (maintainer)

| topic | decision |
|---|---|
| Methylation | Cohort has no methylation libraries. No feature, correction or benchmark work. |
| ACCESS-HEME / CAR-T | Out of scope. No task schema, survival evaluator or lymphoma cohort work. |
| Copy number | Stays out of the model. Comparator or conditioning variable in evaluation only. |
| Metadata firewall | Unchanged. Evaluation and calibration only, never a model feature. |
| Upstream | krewlyzer moves to one fragment model and a new release. **Feature values change.** |
| Re-baseline | Grouped CV and the krewlyzer release go in **one** production run, with a pre-registration note written before it. |

---

## 2. Blocking gaps (new, and both of them bite)

**The local evaluation data is gone.** `~/Downloads/v0.0.32_eval` no longer exists: OOF scores,
labels, matrices, and the shipped `kreview_report_v0.0.33_release.html` with it. Every script in
`scripts/research_analyses/` hard-codes that path, so **nothing in the local research track can
run today**, including the nuisance audit, the TF-conditioning test and every M1–M8 measurement
behind the downstream export. Restore it from the cluster, or those items move to HPC and stop
being "local, CPU, cheap".

**Two plan documents are referenced but absent.** The November brief defers to
`kreview_PU_label_plan.md` and `ctDNA label noise and quantification.md` for the D5 design,
"prerequisite fix 1", and "PU-plan check 0.3". Neither is in this repo or anywhere on the
maintainer's machine. Items below that depend on them are marked **[doc missing]** and are
transcribed from the brief's summary of them, not from the source.

---

## 3. The register

Effort: **S** ≤ half a day · **M** 1–3 days · **L** ≥ a week. "Gate" = what must land first.
Done rows stay listed with their PR, because what was tried and what it cost is the part that
gets lost.

### Track R — the re-baseline (the gate everything crosses)

One production run. Nothing downstream of it is interpretable until it lands, and nothing
upstream of it should be re-measured twice.

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| R1 | **Patient-grouped CV at every site** | Grouping exists in exactly one place today: the train/test split (`labels.py:798`, `StratifiedGroupKFold`). All **8** CV construction sites in `eval_engine.py` use plain `StratifiedKFold`. `groups` is already plumbed to every call site for the *bootstrap interval* (#132), so the splitter swap is bounded but is not one line. | — | M |
| R2 | **krewlyzer fragment-model release** | One definition of a fragment; `{sample}.fragments.parquet` as a declared output. Upstream repo, own acceptance rule. | — | L |
| R3 | **Pre-registration note in `ANALYSIS_PLAN.md`** | Written *before* the run: krewlyzer version, which value-changing policies were accepted, and the statement that earlier numbers are not comparable. Required by the file's own between-runs rule. | R1, R2 | S |
| R4 | **Declare the new outputs** | `fragments.parquet` declared as known and **not read** by the tabular loader; the by-class tables declared. A cohort mixing two krewlyzer fragment-model versions must **raise**, not load. | R2 | S |
| R5 | **The production run itself** | Both changes together so kreview reruns once. | R1–R4 | M |

**Extraction is never tuned on the endpoint.** kreview performance is not evidence for a
krewlyzer extraction policy. A kreview result suggesting an extraction problem is raised as a
krewlyzer issue and settled by krewlyzer's own acceptance rule.

### Track B — review obligations the report still owes

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| B4 | **Threshold calibration at the decision layer** | Was per-assay (98.2% XS1 / 97.5% XS2). Now known to generalize: multi-sample 99.0% vs single-draw 96.6%, costing 6.6 points of sensitivity in the monitored population. Calibrate within the population the threshold is applied to, not per-assay. | — | M |
| B7 | **Raise `n_boot` for the decomposition ratios** | Shipped 1.26 / 0.94 are noise draws at 400 resamples; converged values are 1.184 / 1.087. Interval endpoints are fine at 400; only the two ratios need more. Separate resample count for the decomposition pass. | — | S |
| B8 | **Ship the multi-sample-subset operating point** | Measured and favourable. Answers the reviewer's item 6, and carries the caveat that this subset is exactly the inner-CV-exposed population. | R5 for fresh numbers | S |
| B9 | **Subgroup caption and the `pct_true_pos` null** | Caption AUCs as non-comparable across confirmation rates; state that the correlation was tested and is absent. | — | S |
| B1,B2,B3,B6 | ~~ladder, effective n, resolution floor, subgroup floor~~ | **done** — #136, #132, no-op, #134 | — | — |
| ~~B5~~ | ~~Per-variant penumbra annotation~~ | **RETIRED 18 Nov.** Belongs with gbcms / MRD reporting, not kreview. | — | — |

### Track N — nuisance and tumor-fraction conditioning (new evaluators, evaluation-only)

Supersedes the old C1. Both are blocked today by §2.

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| N1 | **Nuisance audit** | Does any family track a technical or host variable instead of tumor signal? Four tests: nuisance-only model, score-on-nuisance within qTN, assay-held-out, stratified endpoint. Each patient-grouped and run **within one assay version** as well as pooled. Flag thresholds **pre-registered before the run**; flagged families are reported, never silently removed. | R5, §2 | M |
| N2 | **TF-conditioning test** | Does a family carry information beyond tumor fraction, or is it a second measurement of burden? Within-VAF-bin detection and AUC, plus partial Spearman conditioning on log TF proxy. | R5, §2 | M |
| N3 | **Admission rule for any new feature family** | Pre-registered, all conditions: moves sens@98spec-qTN in the 0.5–2% VAF bins beyond the CI half-width; within one assay version and on the assay-held-out split; after conditioning on TF and copy-number state; not flagged by N1; present in off-target fragments where applicable. A gain seen only on a mixed-assay random split is not evidence. Belongs in `ANALYSIS_PLAN.md`, not here. | — | S |

**Caveat carried from the brief.** The DNASE1L3-like nuclease proxy was trained on low-pass WGS
in a prenatal-screening population to detect a rare homozygous variant. On a capture panel in
cancer patients it is untested. Treat it as a continuous end-motif axis, check stability across
assay versions before using it as a stratifier, check the licence, and drop it if it does not
transfer. The audit does not depend on it.

### Track D — cluster

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| D2 | **True unique-depth re-label** | F7's formal gate. **Now contested:** R5 re-runs labeling anyway and fragment membership changes, so a standalone D2 produces depth values the re-baseline discards. Run it now only if the depth answer is needed before the krewlyzer release. See §5 decision 1. | — | S–M |
| D3 | **CH subtraction, matched buffy coats** | Surviving alternative for the variant-silent flags; the companion paper independently urges the caution. | D2 or R5 | M |
| D4 | **Blinded chart review** (72 flagged + 72 matched) | Clinical validation of the variant-silent value case. Flag set moves with the re-baseline. | D3, E5 | L |
| D5 | **In-silico dilution** | Keystone. **Design changed:** mix at *fragment* level from `fragments.parquet` so motif features are valid, not only coordinate ones; add a **placebo arm** (non-tumor library from a different batch, same grid) so a shift that scales with dilution can be attributed; mix **within one assay version** only. Research code, not part of the tabular loader. **[doc missing]** for the original design. | R2 | L |
| D6 | **Buffy fingerprint-collapse pilot** | Features predict assay version at AUC 1.000. If buffy-anchored normalization collapses that, cross-assay calibration is solved at the feature level. | — | M |
| D8 | **Off-target coverage → hybrid TF** | A measured tumor fraction instead of a converted one. Retires the 2×VAF conversion and its patient-specific error. | — | L |
| D10 | **Fixed-position-set recomputation** | The reviewer's top-priority item across three rounds, and still **not previously on this register**. `max_vaf` is a maximum over whatever positions were *called*; the fixed-position version needs the ACCESS MAF joined to each patient's IMPACT variant keys. Not local: those are inputs to `kreview label`, not persisted outputs. Separates the noise reading of the coverage-evenness finding from the two substantive ones. | cluster data | M |
| ~~D7~~ | ~~Penumbra mask re-derived locally~~ | **MOVED UPSTREAM.** Now krewlyzer §2g, region-class stratification and the penumbra map. Enters kreview as a region class, never as coordinates. | — | — |

### Track X — downstream export and frozen scorer (new, §10 of the brief)

A downstream genomic-plus-radiological fusion model wants a few fragmentomic values per sample.
Their BAMs have already been run through krewlyzer. **One implementation per behaviour:** PON
normalisation, selection and collapse happen once, in kreview; the consumer receives a table and
never re-derives features.

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| X0 | **Answer Q1–Q6 with the consumer** | Blocking, before any code. Assay and prep match; krewlyzer and PON versions; patient overlap with our cohort (a frozen score for a training patient is leakage); what their model predicts and on how many patients; provisional table now or wait; whether their fusion model is itself a tabular foundation model. | — | S |
| X1 | **Confirm whether a predict path exists** | The brief flags this as a guess, code not re-read. If one exists, extend it; do not add a second. | — | S |
| X2 | **M1–M8 measurements** | Per-family model-class cost under grouped CV; PC variance; nuisance correlations; VAF redundancy; FSC-only survival split; frozen-vs-OOF agreement; consumer batch shift; patient overlap count. Blocked by §2. | R5, §2 | M |
| X3 | **Export table and frozen scorer** | One row per sample: `{family}_score`, `_score_pct_qtn`, `_dev`, `_pc1..k`, `fsr_level`, `score_source`, provenance. FSC-only, no genomic columns, no identifiers. Final fit on the full cohort with CV-chosen hyperparameters, calibration fit on OOF, one scoring entry point sharing the training loader and PON-z path, fail loud on every version mismatch. | X0–X2 | M |
| X4 | **Provisional label-free table** | `fsr_level`, `dev`, PCs need only the PON and loadings, so they can ship before the re-baseline, marked provisional. Superseded **as a whole** later; columns from two krewlyzer versions are never mixed. | X0 | S |

**Why the multimodal foundation-model stack is not the frozen scorer.** It answers a different
question (one number across families, when the consumer asked for one per family); its artifact
would *be* the cohort, since these models predict in context, breaking the aggregates-only rule
and unable to leave HPC; it needs the whole chain and would receive final-fit base scores where
it was trained on out-of-fold ones; its primary arm is the one still untested under grouped CV;
and the gain is within noise. Allowed only as a clearly separate, explicitly non-portable column.

### Track S — fragment-encoder (supersedes the old D9)

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| S1 | **Fragment encoder, LEAF-style** | The only escape from the saturation ceiling. **No released weights found** as of 18 Nov: corpus is public, checkpoints and model code are not, so a frozen-probe baseline is unavailable and a first encoder trains from scratch or from a general DNA language model. Re-check before any experiment. Pretraining is label-free and may start once the export exists; the go/no-go is gated on R1 and D5 and uses N3 plus N1. A coordinate-free encoder cannot see per-locus molecule yield, so the penumbra map enters as a region class. | R2 | L |

### Track E — writing and decisions

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| E1 | **Send the reviewer response** | Draft complete through round 3. Round 4 added four corrections it does not yet carry (§1a). Sending before the re-baseline keeps it about the tagged artifact; after, it describes numbers that no longer exist. | decision | S |
| E2 | **Verify the field-norm claims** (17% / 1.4% / 0.5% over 213 papers) | Their numbers, not ours. Quotable and embarrassing if wrong. | — | M |
| E3 | **Fix C1/C2 final wording** | C1 in TF units, scoped to aggregated features, **and** scoped as an analytical detection limit rather than a disease-burden threshold: in plasma there are no tumor cells, so tumor fraction is a ratio of release rates whose denominator moves with infection, inflammation and treatment. C2 as saturated *within aggregated representations*. | — | S |
| E4 | **Non-comparability statement vs DELFI/GEMINI** | 48.3% at 98% spec is ctDNA+ vs ctDNA− *within cancer patients*; a referee will otherwise read a 40-point deficit. | — | S |
| E5 | **Chart-review protocol** | Single pre-specified composite endpoint, matched on depth, age, histology, assay version. Written before D4 runs. | D2 or R5 | M |

### Track F — infrastructure

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| F5 | **Local env carries arfs 2.4 against LightGBM 4.7** | Two GrootCV tests fail on any clean checkout here (ERR-20260824-001). CI unaffected, so it costs developer time rather than correctness. | — | S |
| F8 | **CI scoping** (#144, #145) | A Markdown change runs 2 checks; a two-line shell change ran all 8 for ~26 minutes. `scripts/` cannot enter the image. | — | S |
| F1–F4, F6, F7 | ~~SLURM wrapper, isolated-env recipe, nbformat guard, mypy, API reference, taxonomy~~ | **done** — #130, #137, #138 | — | — |

### Retired by the November decisions

Recorded because what was *rejected and why* is the part that gets re-proposed.

| item | reason |
|---|---|
| Methylation work of any kind | No methylation libraries in the cohort |
| CAR-T schema, landmark survival evaluator, inflammation feature block | ACCESS-HEME out of scope; inflammation as a *feature* breaches the firewall |
| Low-MAPQ fraction, mitochondrial fragmentomics | Tiny or confounded on a capture panel dominated by design and pre-analytics |
| Histone-mark protection maps (MAP-WPS) | Source preprint could not be retrieved; off-target depth on ACCESS unmeasured |
| Per-sample GC or penumbra score **as a model feature** | Batch and copy-number confounded. May be *tested* under N3; expected to fail |
| Inverse-variance down-weighting of low-yield sites | Arithmetic does not support it: with an unchanged per-molecule error rate, pooled counting is already optimal and missing molecules are not recoverable by weighting |
| Per-variant penumbra annotation (old B5) | Belongs with gbcms / MRD reporting |
| Cancer-vs-healthy benchmark on public WGS (old C4) | Separate study. If run, within one source cohort with another as external validation |

---

## 4. Critical path

Everything now routes through one gate.

1. **R1 → R3 → R5.** The re-baseline. R2 is upstream and on its own clock; R1 is ours and can
   start today. Every number in Tracks B, N and X is provisional until R5 lands.
2. **§2 → N1, N2, X2.** The local research track is blocked on restoring the evaluation outputs,
   not on effort. Fix that before planning around "local, CPU, cheap".
3. **F7 chain:** D2 or R5 → D3 → E5 → D4. The flag set moves with the re-baseline, so running
   the chain before R5 means running it twice.
4. **D10** is independent of all of the above, needs cluster data, and is the reviewer's
   highest-priority open item.
5. **R2 → D5 → S1.** Fragment-level work. The longest chain and the only one that could move the
   headline rather than qualify it.

---

## 5. Decisions needed

1. **Does D2 run now, or fold into R5?** Running now gives the depth answer months earlier and
   unblocks D3/D4; the values are then discarded at the re-baseline and the chain runs twice.
   Folding in is cheaper and slower. This reverses the September recommendation, which predated
   the krewlyzer release. Either way, submission spends the allocation and needs an explicit go.
2. **Restore `v0.0.32_eval`, or move the local track to HPC?** Until one of these happens,
   N1, N2 and X2 have no data and `scripts/research_analyses/` cannot run at all.
3. **Send the reviewer response now, or after R5?** Now keeps it about v0.0.33, which is tagged
   and which they have already audited, and corrects their record on four points. After means
   re-deriving the whole response against numbers that do not exist yet.
4. **Where do the two missing plan documents live?** D5's original design and "PU-plan check
   0.3" are transcribed second-hand until they surface.
5. **Does the provisional export table (X4) ship before the re-baseline?** Default in the brief
   is yes, marked provisional and superseded as a whole.

---

## 6. Standing constraints

- **Isolated environments only.** Never install into a base interpreter; verify `sys.prefix`
  first (`.agents/memory/feedback-isolated-envs-only.md`).
- **No PHI in the repo.** `.agents/memory/` and `.agents/learnings/` are committed and public;
  clinical workbooks with identifiers stay on the maintainer's machine.
- **Outward actions ask first** — shared-branch pushes, releases, image publishes, and any SLURM
  submission that spends the allocation.
- **Library docs come from Context7, not memory** (`.agents/rules/context7.md`).
- **Comparability boundaries.** Pre-#101 holdout numbers are not comparable to grouped-split
  runs. CIs from before #132 were sample-level and are ~10% too narrow. Everything before R5
  will be not-comparable again, for two independent reasons at once.
- **No container rebuild for `scripts/` changes.** The Dockerfile copies only `pyproject.toml`,
  `settings.ini`, `README.md`, `LICENSE` and `kreview/`. Job wrappers bind-mount the checkout and
  record its SHA (#146).
- CI does not run on stacked PRs, and merging a base branch with `--delete-branch` auto-closes
  anything targeting it. Retarget dependents first.
- CI-only lint failures reproduce in `python:3.12-slim` amd64 installed exactly as CI
  (`.agents/memory/reference-ci-env-repro.md`).
