# Report Rendering API Reference

The `kreview.report` module is the CLI-facing entry point for rendering: it locates a
pipeline output directory, delegates to the data layer, and writes the page plus its
manifest. A partial report is always loud — evaluators that appear in the scoreboard but
lack model results are recorded in `missing_detail` rather than quietly omitted.

For conceptual explanations, see:

- [Report Data Layer](report-data.md)
- [Dashboard Guide](../machine-learning/dashboard-guide.md)

---

::: kreview.report
    options:
      show_root_heading: true
      show_source: false
      members_order: source
