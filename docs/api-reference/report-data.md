# Report Data Layer API Reference

The `kreview.report_data` module assembles the single-page report's data blob from a
pipeline output directory and renders the page. It is the only place that decides what a
number in the report means — the operating points, their patient-clustered intervals, the
verification-bias ladder, the subgroup breakdowns and the automatic findings all originate
here, so the template renders and never computes.

Two guarantees live in this module: the blob is **aggregates only** (a build-time PHI guard
refuses to write anything sample-id-shaped), and a value that could not be sourced is
reported as unknown rather than defaulted.

For conceptual explanations, see:

- [Dashboard Guide](../machine-learning/dashboard-guide.md)
- [Models And Metrics](../machine-learning/models-and-metrics.md)

---

::: kreview.report_data
    options:
      show_root_heading: true
      show_source: false
      members_order: source
