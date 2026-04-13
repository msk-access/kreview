# Decision Curve Analysis (DCA)

Decision Curve Analysis evaluates the **net clinical benefit** of using a predictive model at different probability thresholds, compared to default strategies of treating all patients or treating none.

---

## Why DCA?

AUC tells you *how well* a model discriminates, but not *whether using it improves clinical decisions*. DCA bridges this gap by asking:

> At a given risk threshold, does using this model result in more correctly identified positives without generating too many false-positive interventions?

This is critical in oncology screening contexts where:

- **Treating all** (e.g. recommending invasive biopsy for every patient) has a concrete harm cost
- **Treating none** misses treatable cancers
- A model should provide net benefit *between* these extremes

---

## How it works

For each threshold $t$ in $[0.01, 0.99]$:

$$
\text{Net Benefit}(t) = \frac{TP}{N} - \frac{FP}{N} \times \frac{t}{1 - t}
$$

Where:

- $TP/N$ = fraction of true positives correctly identified
- $FP/N$ = fraction of false positives incorrectly treated
- $t / (1-t)$ = the **harm-to-benefit ratio** at threshold $t$

### Reference strategies

| Strategy | Net Benefit |
|----------|-------------|
| **Treat All** | $\text{prevalence} - (1 - \text{prevalence}) \times \frac{t}{1-t}$ |
| **Treat None** | $0$ (always) |

### Interpretation

A model is clinically useful at any threshold where its net benefit curve **exceeds both reference lines**:

- Above "Treat All" → the model avoids unnecessary interventions
- Above "Treat None" → the model identifies patients who benefit from treatment
- Below both → using the model is worse than a simple default strategy

---

## In kreview

DCA is computed for RF and XGBoost models inside `single_feature_model()` using `decision_curve_analysis()`:

```python
from kreview.eval_engine import decision_curve_analysis

dca = decision_curve_analysis(y_true, y_prob, thresholds=np.linspace(0.01, 0.99, 99))
# Returns: {"thresholds", "net_benefit_model", "net_benefit_treat_all"}
```

The dashboard renders DCA on the **Model Validation → Decision Curve Analysis** tab with:

- Model curves (RF, XGBoost) as solid lines
- "Treat All" as a dashed gray line
- "Treat None" as a dotted gray line at y=0

---

## Clinical context

DCA is most informative when:

- The **positive class prevalence** is low (kreview's typical healthy-normal-enriched cohorts)
- The **cost of false positives** is non-trivial (e.g. invasive tissue biopsy, unnecessary treatment)
- You need to choose a **specific operating threshold** rather than relying on a single summary metric

!!! note "Limitation"
    DCA assumes a specific decision context (treat vs. don't treat). In fragmentomics research, the "treatment" is typically further diagnostic workup rather than direct therapy. Interpret net benefit accordingly.

---

## References

- Vickers AJ, Elkin EB. Decision curve analysis: a novel method for evaluating prediction models. *Medical Decision Making*. 2006;26(6):565-574.
- Vickers AJ, et al. A simple, step-by-step guide to interpreting decision curve analysis. *Diagnostic and Prognostic Research*. 2019;3:18.
