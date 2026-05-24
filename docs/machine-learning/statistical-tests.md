# Statistical Evaluation

Before feeding extracted feature matrix numbers into ensemble models, `kreview` utilizes native `scipy.stats` functionality executed in `evaluate_feature()`.

Our data almost never follows a clean parametric distribution, so we strictly use non-parametric tests.

```mermaid
flowchart LR
    classDef step fill:#8b5cf6,stroke:#5b21b6,color:#fff;
    A["Feature Matrix"]:::step --> B["Kruskal-Wallis\n(4-group omnibus)"]:::step
    B --> C["Mann-Whitney U\n(pairwise)"]:::step
    C --> D["Cohen's d\n(effect size)"]:::step
    D --> E["Spearman Rank\n(confounders)"]:::step
    E --> F["Univariate AUC\n(per-feature LR)"]:::step
    F --> G["Mutual Information\n(non-linear)"]:::step
    G --> H["mRMR / Hybrid Union\n(Selection)"]:::step
    H --> I["Pass to ML\nModels"]:::step
```

---

## The 4-Way Omnibus Test (Kruskal-Wallis)

We group the sample's generated feature matrices by the 4 primary `CtDNALabeler` labels (`True ctDNA+`, `Possible ctDNA+`, `Possible ctDNA−`, `Healthy Normal`).

Because we are checking more than two independent samples to determine if they originate from the same distribution, we employ the **Kruskal-Wallis H-test** (`stats.kruskal`).

If the omnibus $p$-value is significant ($p < 0.05$), it suggests that the feature is stratifying *at least one* label group. Pairwise analysis then identifies which groups differ.

## Pairwise Separation (Mann-Whitney U)

We run five independent 2-sample **Mann-Whitney U** rank-sum tests:

| Pair | Clinical Question |
|------|-------------------|
| True ctDNA+ vs Healthy Normal | Can this feature distinguish confirmed cancer from healthy? |
| Possible ctDNA+ vs Healthy Normal | Does the signal extend to unconfirmed positives? |
| True ctDNA+ vs Possible ctDNA+ | Can it differentiate confirmed from uncertain? |
| Possible ctDNA− vs Healthy Normal | Is there any signal in likely-negative patients? |
| True ctDNA+ vs Possible ctDNA− | How strong is the full positive-negative gap? |

We additionally compute a **Rank-Biserial correlation** to understand the direction and magnitude of separation.

### Benjamini-Hochberg FDR Correction
Because `kreview` executes five independent pair-wise checks simultaneously, it introduces a significant multiple-testing problem. To prevent artificially inflated False Positive rates (p-hacking), the engine natively applies the **Benjamini-Hochberg Method** to wrap all 5 raw $p$-values. The generated `fdr_pvalue` arrays are what you should evaluate for true significance.

## Effect Size (Cohen's d)

As an accompaniment to strict \(p\)-values (which easily become inflated by large sample cohorts), we compute **Cohen's d**. This represents the standardized difference between two means (True+ vs Healthy):

```math
d = \frac{M_{1} - M_{2}}{SD_{pooled}}
```

| Cohen's d | Interpretation |
|-----------|---------------|
| \(d \ge 0.8\) | Large biological separation |
| \(0.5 \le d < 0.8\) | Medium separation |
| \(d < 0.5\) | Small or negligible |

## Confounder Tracking (Spearman Rank)

Fragmentomics logic is notorious for being accidentally driven by sequencing depth rather than actual biological shedding signals.

To prevent this, `evaluate_feature` independently extracts **Spearman Rank Correlations** mapping the generated feature against:

1. `max_vaf` — Is the feature actually scaling linearly with structural tumor burden?
2. `total_fragments` — Is the feature artificially inflating simply because a sample was sequenced to 4,000x depth?

!!! warning "High Spearman Depth Correlation"
    If `spearman_depth_r > 0.5`, the feature may be a sequencing artifact rather than a true biological signal. Interpret its AUC with caution.

## Per-Feature QC Metrics

In addition to statistical tests, `evaluate_feature()` computes three data quality fields for each feature:

| Metric | Field | Purpose |
|--------|-------|---------|
| Missing count | `n_missing` | Number of NaN values in the feature column |
| Missing percentage | `pct_missing` | Percentage of samples with NaN (0–100) |
| Zero variance | `is_zero_variance` | Whether `std == 0` after dropping NaN (constant feature) |

These metrics are saved to `*_eval_stats.parquet` and surfaced in the dashboard's [Cohort & QC page](../machine-learning/dashboard-guide.md#page-5-cohort--qc).

## Feature Selection Scoring (v0.0.9+)

After descriptive statistics are computed, kreview scores every feature using complementary methods to decide which features enter the downstream ML models. The default strategy is **mRMR**.

### Minimum Redundancy Maximum Relevance (mRMR) [Default]

The `strategy="mrmr"` method iteratively selects features that maximize correlation with the target label (relevance) while minimizing correlation with already selected features (redundancy). 

- Resolves multicollinearity efficiently, ensuring models are not fed redundant fragments.
- Automatically handles NaNs via median/mean/zero imputation.
- The `--top-percentile` argument controls the final number of features retained ($K$).

### Hybrid Union Selection [Legacy/Fallback]

The `strategy="hybrid_union"` method determines the feature set by:

$$\text{Selected} = \text{Top}_{X\%}(\text{AUC}) \cup \text{Top}_{X\%}(\text{MI})$$

where $X$ is controlled by `--top-percentile` (default: 10%). The **union** ensures that features strong in *either* metric are retained — a feature with high AUC but low MI (linear predictor) or high MI but low AUC (non-linear predictor) will both be included.

!!! tip "Selection QC"
    The `selection_qc` metadata block in `model_results.json` records:
    
    - `method`: `mrmr` or `hybrid_union`
    - `n_selected_union`: Total features selected
    - `n_overlap_both`: Features in top-X% of *both* metrics (if hybrid)
    - `n_auc_only` / `n_mi_only`: Features exclusive to one metric (if hybrid)

!!! warning "Deprecated: `--top-n`"
    The `--top-n` flag (fixed count, Cohen's D ranking) is deprecated since v0.0.9. Use `--top-percentile` instead.

## Multimodal Selection (v0.0.10+)

When aggregating multiple feature sets in `kreview eval multimodal`, the pipeline offers two higher-order selection strategies via `--multimodal-selection`:

1. **`mi` (Default)**: Rapidly selects the top $K$ features using Mutual Information ranking across all concatenated features in the super-matrix.
2. **`boruta_shap`**: Interaction-aware selection using the Boruta-SHAP algorithm wrapping an XGBoost classifier. This rigorous approach verifies whether a feature is genuinely more important than a random shadow variable, ensuring extremely robust multimodal stacking performance.
