# Evaluation CLI API Reference

The `kreview.cli_eval` module implements the `kreview eval` command family — the CPU and
GPU model stages, the nested-CV ablation stages, and the multimodal stacking stages that the
Nextflow DAG scatters over. Each subcommand is a pipeline stage boundary, not a convenience
wrapper: there is one implementation per behaviour and the DAG calls it.

For conceptual explanations, see:

- [Cli](cli.md)
- [Pipeline Architecture](../developer/pipeline-architecture.md)

---

::: kreview.cli_eval
    options:
      show_root_heading: true
      show_source: false
      members_order: source
