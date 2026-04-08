# Statistical Evaluation

Before feeding extracted feature matrix numbers blindly into complex ensemble models, `kreview` utilizes native `scipy.stats` functionality dynamically executed in `eval_engine.evaluate_feature()`.

Our data almost never follows a clean parametric geometric distribution, so we strictly use non-parametric distribution tests.

---

## The 4-Way Omnibus Test (Kruskal-Wallis)

We group the sample's generated feature matrices by the 4 established `CtDNALabeler` labels.

Because we are checking more than two independent samples (the 4 groups) to determine if they originate from the same distribution, we employ the **Kruskal-Wallis H-test** (`stats.kruskal`).

If the omnibus $p$-value returns significant ($p < 0.05$), it proves that the feature is successfully stratifying *at least one* label. We then move to pairwise analysis to figure out which ones.

## Pairwise Separation (Mann-Whitney U)

To see specifically if the feature perfectly separates `True ctDNA+` from `Healthy Normal` cases, we execute independent 2-sample **Mann-Whitney U** rank-sum tests.

We additionally compute a Rank-Biserial correlation dynamically to understand the direction and magnitude of that separation.

## Effect Size (Cohen's d)

As an accompaniment to strict $p$-values (which easily become inflated by large sample cohorts), we aggressively compute **Cohen's d**. This represents the standardized difference between two means (usually True+ vs Healthy).

$$
d = \frac{M_{1} - M_{2}}{SD_{pooled}}
$$

If $d > 0.8$, the fragmentomic feature creates a Massive biological separation.

## Confounder Tracking (Spearman Rank)

Fragmentomics logic is notorious for being accidentally driven by sequencing depth (how deep were the target captures sequenced) rather than actual biological shedding signals.

To prevent this, `evaluate_feature` independently extracts a **Spearman Rank Correlation** mapping the generated feature against:
1. `max_vaf` (Is the feature actually scaling linearly with structural tumor burden?)
2. `total_fragments` (Is the feature artificially inflating simply because a sample was sequenced to 4,000x depth?)
