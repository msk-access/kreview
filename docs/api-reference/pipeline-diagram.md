# Pipeline Diagram API Reference

The `kreview.pipeline_diagram` module declares the Nextflow DAG once — nodes, the processes
each stands for, and the routing between them — and emits it as static SVG at build time.
Layouts are computed here rather than in the browser, so the geometry that ships is the
geometry that was verified, and the same declaration produces both the report's embedded
diagrams and the standalone pages in `docs/diagrams/`.

`tests/test_pipeline_diagram.py` asserts the declaration against the workflow in both
directions, so a stage added to the DAG cannot leave the diagram describing an older
topology.

For conceptual explanations, see:

- [Nextflow](../operations/nextflow.md)
- [Dashboard Guide](../machine-learning/dashboard-guide.md)

---

::: kreview.pipeline_diagram
    options:
      show_root_heading: true
      show_source: false
      members_order: source
