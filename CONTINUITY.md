# CONTINUITY — kreview

**Phase.** Engineering is in maintenance; the work is **evaluation science and defending it**.
Three adversarial-review rounds are closed on measurement rather than argument, and the open
items are now mostly *experiments*, not code. The binding constraint is GPU/cluster access, not
developer time.

**Headline we would defend today:** AUC **0.845** against verified within-patient negatives
(0.856 pooled, 0.976 against donors only — anchor choice moves it 13.1 points, more than any
modeling decision), sensitivity **48.3% at 98% specificity**, LOD50 ≈ **8–10% tumor fraction**,
scoped to aggregated-feature panel fragmentomics rather than to cfDNA physics.

---

## 1. Where we are

**Code — v0.0.33 shipped 25 Aug** (PyPI, GHCR `v0.0.33`/`v0.0.33-gpu`/`latest`, versioned
docs; back-merged to develop). ⚠️ **Scoreboard intervals in v0.0.33 are not comparable to
v0.0.32's** — they resample patients rather than rows, so they are ~10% wider with no model
change behind them.

**What shipped.** Dual-anchor operating points and per-sample depth
columns (#122/#123, merged in #125); the report's visual rebuild — hero zone, burden-response
curve, glossary info icons, axis-title and tick fixes (#126); the Nextflow DAG drawn into
Methods and Run diagnostics with a workflow-drift guard (#127); three review-driven analysis
scripts. Eight CI checks green on each. **Nothing since v0.0.32 is tagged**, so every number
being quoted comes from an unreleased build.

**Science.** Modeling is saturated within aggregated-feature representations (every knob ≤0.01
AUC). The tumor-informed TN anchor replaced the 68-donor anchor and is what makes the operating
point defensible — and, incidentally, what makes the contamination bound computable. Detection
is a clean sigmoid in tumor burden. Labels are not the ceiling. Fragmentomics tracks current
shedding and does not anticipate genotype conversion.

**Review.** Two of our claims withdrawn (the OR-panel union figure; the label-noise mechanism),
one partly upheld against us (coverage *evenness* runs with the reviewer's noise mechanism), four
of their objections refuted with data, three of their own objections withdrawn by them, and one
leakage pathway we disclosed before they found it. Their qTN contamination bound (≤4.1%,
conservative in direction) is sound and worth keeping.

**Local compute has a ceiling.** TabICL will not run the leakage comparison on the M2 Pro.
MPS works and beats CPU, but `n_estimators=8` against quadratic context cost puts a single
1,900-row fit past ten minutes, and the arm needs twenty of them. It belongs on the cluster.
Related: **all installs go in isolated environments** — a base-env install pulled `setuptools`
past 81 and removed `pkg_resources`, the exact breakage the `setuptools<81` pin exists to
prevent (`.agents/memory/feedback-isolated-envs-only.md`).

## 1a. What the local batch established (24 Aug)

Three results changed what we can claim, and all three came from running our own numbers
rather than from the reviewer.

**Uncertainty on the headline is about the threshold, not about clustering.** The primary
endpoint had shipped as a bare point estimate. Under a patient-clustered bootstrap with the
threshold re-estimated per resample it is **0.483 [0.424, 0.519]**, and decomposing that width
gives a clustering design effect of **1.26** against a threshold-estimation inflation of
**11.3×**. Three review rounds argued about the smaller term by an order of magnitude. The
same clustering effect, measured independently on the stacking AUC through the eval engine,
is **1.21** — inside the reviewer's predicted 1.14–1.23 both times.

**Every interval in the scoreboard was too narrow.** `_bootstrap_auc` resampled rows, so
evaluator and holdout CIs treated a patient's repeated timepoints as independent. Fixed; CIs
widen ~10% on the next run and are not comparable across that boundary.

**The histology gap rests on one stratum.** Matched on confirmed-variant count within True+
only, NSCLC vs bladder at 4+ variants holds (41.2% vs 20.3%, OR 2.75, p=0.004, non-overlapping
intervals); NSCLC vs pancreatic at 2–3 is marginal (p=0.049, overlapping) and would not survive
a correction across the three contrasts. The pooled figure sent to the reviewer overstates it.
Composition is a real confound but a **band-specific** one: pancreatic is 47.5% True+ inside
the 1–5% VAF band and 75.1% cohort-wide.

---

## 2. The register

Effort: **S** ≤ half a day · **M** 1–3 days · **L** ≥ a week. "Gate" = what must land first.
**Done** rows stay listed with their PR, because what was tried and what it cost is the part
that gets lost. 22 items remain, 9 of them on the cluster.

### Track A — Ship what is already built (code, local)

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| A1 | ~~Close #122 and #123~~ **done** | Both shipped in #125 | — | S |
| A2 | ~~Cut v0.0.33~~ **done, #139** | Tagged on main via `release/v0.0.33` — git-flow, matching history rather than the old guide text, which #138 corrected | A1 | S |
| A3 | **Regenerate the v0.0.32 report from the tagged build** | The HTML we have been reading is a local render; the artifact of record should come from a tag | A2 | S |

### Track B — Make the report say what the review forced us to admit (code, local)

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| B1 | ~~Verification-bias ladder as a panel~~ **done, #136** | Four rungs with patient-clustered intervals spanning 13.1 AUC points. Sized M on the assumption it needed new data; the numbers already shipped as a caption clause, so it was a prominence task | — | S |
| B2 | ~~Effective n on the TN anchor~~ **done, #132** | Grew past its estimate: the primary endpoint had no interval at all, and neither did the scoreboard's. Both are patient-clustered now, and the decomposition (§1a) is the finding | — | M |
| B3 | ~~Resolution-floor phrasing~~ **no-op** | The "at most" phrasing existed only in the reviewer draft, never in the findings engine. Draft corrected | — | — |
| B6 | ~~Subgroup floor, interval, tier composition~~ **#134** | Not in the original plan; fell out of C2. The panel printed retinoblastoma's AUC on 72 positives at the same weight as NSCLC's on 2,254 — the denominator error we withdrew an odds ratio for, still live in the report | — | M |
| B4 | **Per-assay threshold calibration at the decision layer** | A 98% global threshold realizes 98.2% / 97.5% per assay version; fixable at the threshold, not the features | — | M |
| B5 | **Per-variant penumbra annotation as a detection-power prior** | Highest-value item from the three-way paper read: turns a population phenomenon into a per-call confidence modifier. Needs no new data once the BED exists | D7 | M |

### Track C — Research answerable here, on CPU (research, local)

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| C1 | **Nuisance battery** — predict depth, input mass, age, site *from* the features; partial them out | The reviewer's own words: the single experiment that would most change the reading of F3 and F8. Evaluation-only, so the metadata firewall permits it | — | M |
| C2 | ~~Histology gap per variant-count stratum~~ **done, #133** | Did not close the objection — narrowed our claim to the 4+ stratum (§1a). Everything it needed was already local | — | S |
| C3 | **Penumbra feature-ablation** — mask the shared 1.4%, re-fit | If 0.856 survives, the signal is not penumbra-driven and we can say so with a citation. If it drops, our discrimination lives in the least transportable regions | D7 | M |
| C4 | **Within-Cristiano benchmark, Jiang as external validation** | The obvious public-data benchmark is confounded — cancer is Cristiano, healthy is Jiang, so "cancer vs healthy" is "study A vs study B". Cristiano's own 245 healthy controls make it internally valid | — | M |

### Track D — Needs the cluster (research, HPC)

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| D1 | **tabicl_ft grouped-vs-ungrouped** | The last hole in the leakage argument: CPU arms move ≤0.005 AUC, but the headline arm is GPU-only and untested. Both we and the reviewer have flagged it | SLURM wrapper (F1) | M |
| D2 | **True unique-depth re-label** (`kreview label --krewlyzer-dir`) | F7's formal gate. The v0.0.32 outputs predate #122, so `total_fragments_pf` does not exist in them; the depth question cannot be settled from what we have | — | S–M |
| D3 | **CH subtraction using matched buffy coats** | The surviving alternative explanation for the variant-silent flags, and the companion paper independently urges the caution | D2 | M |
| D4 | **Blinded chart review** (72 flagged + 72 matched controls) | The clinical validation of the variant-silent value case | D2, D3 | L |
| D5 | **E2 in-silico dilution** — tumor-high libraries into unmatched qTN backgrounds, 286 converters as the matched subset | Makes the LOD claim definitive in tumor-fraction units instead of inferred via TF ≈ 2×VAF | — | L |
| D6 | **Buffy fingerprint-collapse pilot** (~50 paired buffy BAMs) | Features predict assay version at AUC 1.000. If buffy-anchored normalization collapses that, cross-assay calibration is solved at the feature level | — | M |
| D7 | **Penumbra mask re-derived locally** — per-target unique molecule yield across the normal pool, GC- and probe-corrected | Their coordinates are not portable to a deep panel (their thresholds are calibrated to 0.1–1× WGS). A null result is equally publishable | — | M |
| D8 | **Off-target coverage feasibility → CNVkit/ichorCNA hybrid TF** | Gates a real tumor-fraction estimate, which is what the LOD claim should be stated in | — | L |
| D9 | **E3 read-level representation (go/no-go)** | The only escape from the C2 saturation ceiling — GEMINI's 0.64→0.91 shows the field escaped it exactly this way | — | L |

### Track E — Writing and decisions (planning)

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| E1 | **Send the reviewer response** | Draft is complete through their round-3 record, including the correction that their open item 2 still cites our withdrawn F7 result | decision | S |
| E2 | **Verify the field-norm claims before quoting** (17% patient-grouped / 1.4% TF-stratified / 0.5% imperfect-reference, over 213 papers) | Their numbers, not ours. Quotable and embarrassing if wrong | — | M |
| E3 | **Fix C1/C2 final wording** | C1 in TF units, scoped to aggregated features; C2 as "saturated *within aggregated representations*" | — | S |
| E4 | **Non-comparability statement vs DELFI/GEMINI** | 48.3% at 98% spec is ctDNA+ vs ctDNA− *within cancer patients*; a referee will otherwise read a 40-point deficit against screening cohorts | — | S |
| E5 | **Chart-review protocol** — single pre-specified composite endpoint, matching on depth/age/histology/assay version | Adopted from the review; must be written before D4 runs, not after | D2 | M |

### Track F — Infrastructure and hygiene (code, mixed)

| # | Item | Why | Gate | Effort |
|---|---|---|---|---|
| F1 | ~~SLURM wrapper for GPU research jobs~~ **done, #130** | Ready for D1; mirrors `process_gpu` and fails loudly with no GPU. Not submitted — that spends the allocation | — | S |
| F2 | ~~Isolated-env recipe~~ **done, #130** | Refuses to install unless `pyvenv.cfg` exists and `sys.prefix != base_prefix` — the check that was missing | — | S |
| F3 | ~~nbformat 4.5 guard~~ **done, #130** | 118 checks across every notebook | — | S |
| F4 | ~~Two latent mypy errors~~ **done, #130** | Neither was type noise: the cli one hid a real unpack-the-characters-of-a-column-name bug | — | S |
| F6 | ~~API reference and release guide~~ **done, #138** | The reference covered 5 of 13 modules — `report_data` and `selection` undocumented while the scoreboard displaying their output had a page. The release guide also described a flow no release has used | — | M |
| F7 | ~~Taxonomy and report-guide corrections~~ **done, #137** | Eleven files said 5-tier; the rules file and labeling skill said CH-only samples are demoted to `Possible ctDNA−` when the code excludes them as `Undetermined`. `mkdocs build --strict` had been failing before this release and the last | — | M |
| F5 | **Local env carries arfs 2.4 against LightGBM 4.7** | Two GrootCV tests fail on any clean checkout here; the `arfs>=3.0.0` pin exists to prevent exactly this (ERR-20260824-001). CI is unaffected, so it costs developer time rather than correctness | — | S |

---

## 3. Critical path

Four chains, mostly independent:

1. **Defensibility of the headline** → D1 (tabicl_ft arm) + B1/B2. Until D1 lands, the leakage
   answer covers rf and xgb but not the model the headline uses.
2. **F7 / variant-silent value case** → D2 → D3 → (E5) → D4. Everything here is gated on one
   cheap re-label; that makes D2 the highest-leverage cluster job.
3. **LOD in real tumor-fraction units** → D5, with D8 as the more ambitious version.
4. **Escaping saturation** → D9 alone. Large, and the only item that could move the headline
   rather than qualify it.

**The free local tail is spent.** A1, B2, B3, C2 and F1–F4 are done; B6 was added and shipped
on the way. What remains in Tracks B, C and E is real work, and everything in D needs the
cluster. The only item still costing under a day is A2/A3, and that waits on a decision rather
than on effort.

---

## 4. Decisions needed

1. ~~Ship v0.0.33 now, or after B1?~~ **Resolved** — B1 landed first, and v0.0.33 shipped with
   it on 25 Aug: 60 commits carrying every interval change and the honest anchor panel.
2. **Cluster ordering.** My recommendation: D2 first (cheap, unblocks two chains), then D1 (the
   review gap), then D6. Submitting any of these spends the group allocation, so each needs your
   explicit go.
3. **Send the reviewer response now, or hold for D1?** Moved: the draft has gained the
   measured design effects (1.26 and 1.21 against their predicted 1.14–1.23), the
   threshold-vs-clustering decomposition they do not have, and a correction narrowing our own
   histology claim to the 4+ stratum. Holding still buys the headline arm; sending now
   corrects their record before they build further on our withdrawn F7 result.
4. **Is D9 (read-level) in scope at all this cycle?** It is the only path past saturation and it
   is a rewrite of the representation layer, not an experiment.

---

## 5. Standing constraints

- **Isolated environments only** — never install into a base interpreter; verify `sys.prefix`
  before installing (`.agents/memory/feedback-isolated-envs-only.md`).
- **No PHI in the repo.** `.agents/memory/` and `.agents/learnings/` are committed and public;
  clinical workbooks with identifiers stay on the maintainer's machine.
- **Outward actions ask first** — shared-branch pushes, releases, image publishes, and any SLURM
  submission that spends the allocation.
- Pre-#101 holdout numbers are not comparable to grouped-split runs, and **CIs from before
  #132 are not comparable either** — they were sample-level and are ~10% too narrow.
- **CI does not run on stacked PRs** (the workflow triggers only on PRs into develop), and
  merging a base branch with `--delete-branch` auto-closes anything targeting it. Retarget
  dependents first.
- CI-only lint failures reproduce in `python:3.12-slim` amd64 installed exactly as CI
  (`.agents/memory/reference-ci-env-repro.md`).
