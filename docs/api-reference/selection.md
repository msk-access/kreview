# Feature Selection API Reference

The `kreview.selection` module scores features and applies the selection strategies —
mRMR, hybrid union, and the GrootCV/Leshy family from `arfs` that became the multimodal
default in #96. It also owns `build_binary_target`, the single definition of which label
tiers form the positive and negative classes.

For conceptual explanations, see:

- [Models And Metrics](../machine-learning/models-and-metrics.md)
- [Statistical Tests](../machine-learning/statistical-tests.md)

---

::: kreview.selection
    options:
      show_root_heading: true
      show_source: false
      members_order: source
