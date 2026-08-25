# Reproducibility API Reference

The `kreview.reproducibility` module records the provenance stamped into run artifacts —
versions, seeds and environment — so a result can be traced back to the code and settings
that produced it.

!!! note "The one hand-maintained module"
    Every other module in `kreview/` is generated from a notebook in `nbs/`. This one is
    edited directly; see the [nbdev workflow](../developer/nbdev-workflow.md).

For conceptual explanations, see:

- [Nbdev Workflow](../developer/nbdev-workflow.md)

---

::: kreview.reproducibility
    options:
      show_root_heading: true
      show_source: false
      members_order: source
