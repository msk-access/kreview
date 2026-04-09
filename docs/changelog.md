# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Multi-model evaluation:** XGBoost alongside Random Forest and Logistic Regression
- **SHAP explainability:** Beeswarm, dependence, and waterfall plots for RF and XGB
- **Subgroup analysis:** Sensitivity metrics stratified by cancer type and assay version
- **Exponential backoff retry:** DuckDB file loading with automatic retry on transient I/O failures
- **8 genomewide evaluators:** ATAC, BreakPointMotif, EndMotif, FSC, FSD, FSR, MDS, TFBS
- **CI/CD:** PyPI publishing via OIDC, GHCR Docker image publishing, Docker build dry-run in tests
- **Documentation:** MkDocs Material site with 15+ pages, Mermaid diagrams, MathJax, auto-generated API reference
- **Docker support:** Multi-stage Dockerfile with Quarto for standalone report generation

### Changed
- Feature count expanded from 18 to 26 evaluators
- CLI `--features` now accepts comma-separated values
- `Paths.krewlyzer_dirs` accepts manifest `.txt` files
- Dashboard layout changed from dual-column to sequential full-width rows
- nbdev upgraded from 2.x to 3.0.12 (hyphenated CLI commands)

### Fixed
- `PermissionError` during large-cohort loading via chunked I/O + retry
- Silent failures in subgroup analysis now logged explicitly
- `FSCBinEvaluator` test typo in notebook unit tests

## [0.0.1] - 2026-04-06

### Added
- Initial project scaffold using nbdev
- 5-tier ctDNA labeling engine (including Insufficient Data) (`CtDNALabeler`)
- DuckDB-backed parquet loading with chunked I/O
- 18 feature evaluators (Tier 1: FSC, FSD; Tier 2: WPS, EndMotif, OCF, etc.)
- Random Forest and Logistic Regression evaluation with Stratified K-Fold CV
- Quarto HTML dashboard generation
- CLI via Typer (`kreview run`, `kreview label`)
- pytest test suite with coverage reporting
