"""Tests for kreview.labels — Phase 1 audit fixes (C-04).

Covers:
  - Label hierarchy ordering (True+ > Possible+ > Possible- > Healthy)
  - Insufficient Data gate
  - Healthy volunteers always get Healthy Normal
  - 5-tier docstring accuracy
"""

import pandas as pd
import pytest

from kreview.labels import CtDNALabeler


class TestLabelTierConstants:
    """Verify label constants match the 5-tier + Undetermined system."""

    def test_five_core_tiers_defined(self):
        """CtDNALabeler should define exactly 5 core label tiers."""
        tiers = [
            CtDNALabeler.LABEL_TRUE_POS,
            CtDNALabeler.LABEL_POSS_POS,
            CtDNALabeler.LABEL_POSS_NEG,
            CtDNALabeler.LABEL_HEALTHY,
            CtDNALabeler.LABEL_INSUF_DATA,
        ]
        assert len(set(tiers)) == 5, "Should have exactly 5 distinct core label tiers"

    def test_undetermined_tier_defined(self):
        """LABEL_UNDETERMINED should be defined as a 6th tier (v0.0.16+)."""
        assert hasattr(
            CtDNALabeler, "LABEL_UNDETERMINED"
        ), "CtDNALabeler missing LABEL_UNDETERMINED constant"
        # Must be distinct from all 5 core tiers
        core = {
            CtDNALabeler.LABEL_TRUE_POS,
            CtDNALabeler.LABEL_POSS_POS,
            CtDNALabeler.LABEL_POSS_NEG,
            CtDNALabeler.LABEL_HEALTHY,
            CtDNALabeler.LABEL_INSUF_DATA,
        }
        assert (
            CtDNALabeler.LABEL_UNDETERMINED not in core
        ), "LABEL_UNDETERMINED must not collide with core tiers"

    def test_label_values(self):
        """Verify the exact string values of each tier."""
        assert CtDNALabeler.LABEL_TRUE_POS == "True ctDNA+"
        assert CtDNALabeler.LABEL_POSS_POS == "Possible ctDNA+"
        assert CtDNALabeler.LABEL_POSS_NEG == "Possible ctDNA−"
        assert CtDNALabeler.LABEL_HEALTHY == "Healthy Normal"
        assert CtDNALabeler.LABEL_INSUF_DATA == "Insufficient Data"
        assert CtDNALabeler.LABEL_UNDETERMINED == "Undetermined"

    def test_docstring_says_six_tier(self):
        """Docstring should reference 6-tier (5 core + Undetermined, v0.0.16+)."""
        doc = CtDNALabeler.__doc__
        assert (
            "6-tier" in doc or "six" in doc.lower()
        ), f"Docstring should mention 6-tier: got '{doc}'"


class TestVAFRegressionStats:
    """Tests for continuous VAF regression targets (mean_vaf, std_vaf).

    These columns are required for the Stage 2 Quantifier (regression
    head predicting continuous tumor burden).
    """

    @pytest.fixture()
    def maf_multi_variant(self):
        """MAF with 3 variants for one sample, 2 passing min_vaf threshold."""
        return pd.DataFrame(
            {
                "Tumor_Sample_Barcode": ["S1", "S1", "S1"],
                "Mutation_Status": ["SOMATIC", "SOMATIC", "SOMATIC"],
                "t_ref_count": [90, 80, 99],
                "t_alt_count": [10, 20, 1],  # VAF: 0.10, 0.20, 0.01
            }
        )

    @pytest.fixture()
    def maf_single_variant(self):
        """MAF with exactly 1 passing variant — std_vaf should be 0."""
        return pd.DataFrame(
            {
                "Tumor_Sample_Barcode": ["S2"],
                "Mutation_Status": ["SOMATIC"],
                "t_ref_count": [85],
                "t_alt_count": [15],  # VAF: 0.15
            }
        )

    def test_mean_std_vaf_computed(self, maf_multi_variant):
        """mean_vaf and std_vaf should reflect only VAF-passing variants."""
        from kreview.labels import compute_snv_summary

        result = compute_snv_summary({"S1"}, maf_multi_variant, min_vaf=0.05)
        row = result.set_index("SAMPLE_ID").loc["S1"]

        assert "mean_vaf" in result.columns, "mean_vaf column must exist"
        assert "std_vaf" in result.columns, "std_vaf column must exist"

        # Only 2 passing variants: VAF 0.10 and 0.20
        assert (
            abs(row["mean_vaf"] - 0.15) < 0.01
        ), f"Expected ~0.15, got {row['mean_vaf']}"
        assert row["std_vaf"] > 0, "std_vaf should be > 0 with 2 passing variants"

    def test_single_variant_std_is_zero(self, maf_single_variant):
        """std_vaf should be 0.0 when only one variant passes the filter."""
        from kreview.labels import compute_snv_summary

        result = compute_snv_summary({"S2"}, maf_single_variant, min_vaf=0.05)
        row = result.set_index("SAMPLE_ID").loc["S2"]

        assert (
            row["std_vaf"] == 0.0
        ), f"Expected std_vaf=0 for single variant, got {row['std_vaf']}"
        assert abs(row["mean_vaf"] - 0.15) < 0.01

    def test_no_passing_variants_fallback(self, maf_multi_variant):
        """mean_vaf and std_vaf should be 0.0 when no variants pass min_vaf."""
        from kreview.labels import compute_snv_summary

        # Set min_vaf so high that nothing passes
        result = compute_snv_summary({"S1"}, maf_multi_variant, min_vaf=0.99)
        row = result.set_index("SAMPLE_ID").loc["S1"]

        assert row["mean_vaf"] == 0.0
        assert row["std_vaf"] == 0.0
        assert not row["has_snv"]

    def test_no_somatic_variants_fallback(self):
        """mean_vaf and std_vaf should be 0.0 when MAF has no somatic variants."""
        from kreview.labels import compute_snv_summary

        empty_maf = pd.DataFrame(
            {
                "Tumor_Sample_Barcode": ["S3"],
                "Mutation_Status": ["GERMLINE"],
                "t_ref_count": [90],
                "t_alt_count": [10],
            }
        )
        result = compute_snv_summary({"S3"}, empty_maf, min_vaf=0.01)
        row = result.set_index("SAMPLE_ID").loc["S3"]

        assert row["mean_vaf"] == 0.0
        assert row["std_vaf"] == 0.0

    def test_missing_sample_gets_zero_vaf(self, maf_multi_variant):
        """Samples not in MAF should get 0.0 for all VAF columns."""
        from kreview.labels import compute_snv_summary

        result = compute_snv_summary(
            {"S1", "S_MISSING"}, maf_multi_variant, min_vaf=0.05
        )
        missing_row = result.set_index("SAMPLE_ID").loc["S_MISSING"]

        assert missing_row["mean_vaf"] == 0.0
        assert missing_row["std_vaf"] == 0.0
        assert missing_row["max_vaf"] == 0.0


class TestCHHotspotFiltering:
    """Tests for CH hotspot variant filtering and demotion logic."""

    @pytest.fixture()
    def ch_hotspots(self):
        """A set of CH hotspot variant keys (chrom, pos, ref, alt)."""
        return {
            ("7", 148504724, "C", "T"),  # e.g. DNMT3A R882H analog
        }

    @pytest.fixture()
    def maf_ch_only(self):
        """MAF where the only variant matches a CH hotspot."""
        return pd.DataFrame(
            {
                "Tumor_Sample_Barcode": ["S1"],
                "Mutation_Status": ["SOMATIC"],
                "t_ref_count": [90],
                "t_alt_count": [10],
                "Chromosome": ["7"],
                "Start_Position": [148504724],
                "Reference_Allele": ["C"],
                "Tumor_Seq_Allele2": ["T"],
            }
        )

    @pytest.fixture()
    def maf_mixed(self):
        """MAF with one CH variant and one non-CH variant."""
        return pd.DataFrame(
            {
                "Tumor_Sample_Barcode": ["S1", "S1"],
                "Mutation_Status": ["SOMATIC", "SOMATIC"],
                "t_ref_count": [90, 85],
                "t_alt_count": [10, 15],
                "Chromosome": ["7", "12"],
                "Start_Position": [148504724, 25398284],
                "Reference_Allele": ["C", "G"],
                "Tumor_Seq_Allele2": ["T", "A"],
            }
        )

    def test_ch_only_variant_tagged(self, ch_hotspots, maf_ch_only):
        """CH-only sample should have n_non_ch_variants=0."""
        from kreview.labels import compute_snv_summary

        result = compute_snv_summary(
            {"S1"}, maf_ch_only, min_vaf=0.05, ch_variants=ch_hotspots
        )
        row = result.set_index("SAMPLE_ID").loc["S1"]

        assert (
            row["n_ch_variants"] == 1
        ), f"Expected 1 CH variant, got {row['n_ch_variants']}"
        assert (
            row["n_non_ch_variants"] == 0
        ), f"Expected 0 non-CH, got {row['n_non_ch_variants']}"

    def test_mixed_variants_counted(self, ch_hotspots, maf_mixed):
        """Mixed CH+non-CH should count both correctly."""
        from kreview.labels import compute_snv_summary

        result = compute_snv_summary(
            {"S1"}, maf_mixed, min_vaf=0.05, ch_variants=ch_hotspots
        )
        row = result.set_index("SAMPLE_ID").loc["S1"]

        assert row["n_ch_variants"] == 1
        assert row["n_non_ch_variants"] == 1
        assert row["has_snv"]  # Still has passing variants

    def test_no_ch_set_passthrough(self, maf_ch_only):
        """Without ch_variants, all variants are counted as non-CH (n_ch=0)."""
        from kreview.labels import compute_snv_summary

        result = compute_snv_summary(
            {"S1"}, maf_ch_only, min_vaf=0.05, ch_variants=None
        )
        row = result.set_index("SAMPLE_ID").loc["S1"]

        assert row["n_ch_variants"] == 0
        assert row["n_non_ch_variants"] == 1

    def test_load_ch_hotspots_validation(self, tmp_path):
        """load_ch_hotspots should raise ValueError for missing columns."""
        from kreview.labels import load_ch_hotspots

        bad_file = tmp_path / "bad_ch.tsv"
        bad_file.write_text("Hugo_Symbol\tChromosome\nDNMT3A\t7\n")

        with pytest.raises(ValueError, match="missing required columns"):
            load_ch_hotspots(bad_file)

    def test_load_ch_hotspots_valid(self, tmp_path):
        """load_ch_hotspots should return a set of variant tuples."""
        from kreview.labels import load_ch_hotspots

        good_file = tmp_path / "ch.tsv"
        good_file.write_text(
            "Chromosome\tStart_Position\tReference_Allele\tTumor_Seq_Allele2\n"
            "7\t148504724\tC\tT\n"
            "2\t25457242\tG\tA\n"
        )

        result = load_ch_hotspots(good_file)
        assert len(result) == 2
        assert ("7", 148504724, "C", "T") in result


# ── compute_impact_match tests ───────────────────────────────────────────────


class TestComputeImpactMatch:
    """Tests for compute_impact_match() — IMPACT tissue rescue logic.

    Validates:
      - Shared variant between ACCESS and IMPACT → has_impact_match=True
      - No shared variant → has_impact_match=False
      - Patient with IMPACT sample → has_paired_impact=True
      - Sample with no somatic variants → defaults applied
      - Empty MAF → returns correct structure
    """

    @pytest.fixture()
    def clinical(self):
        """Clinical sample table with 2 ACCESS + 1 IMPACT sample for same patient."""
        return pd.DataFrame(
            {
                "SAMPLE_ID": ["ACCESS_S1", "ACCESS_S2", "IMPACT_S1"],
                "PATIENT_ID": ["P1", "P2", "P1"],
                "GENE_PANEL": ["MSK-ACCESS-v1", "MSK-ACCESS-v1", "IMPACT468"],
            }
        )

    @pytest.fixture()
    def maf_with_match(self):
        """MAF where ACCESS_S1 and IMPACT_S1 share a somatic variant."""
        return pd.DataFrame(
            {
                "Tumor_Sample_Barcode": [
                    "ACCESS_S1",  # ACCESS sample: same variant as IMPACT
                    "IMPACT_S1",  # IMPACT sample: shared variant
                    "ACCESS_S2",  # ACCESS sample: different variant
                ],
                "Mutation_Status": ["SOMATIC", "SOMATIC", "SOMATIC"],
                "Chromosome": ["7", "7", "12"],
                "Start_Position": [55249071, 55249071, 25398284],
                "End_Position": [55249071, 55249071, 25398284],
                "Reference_Allele": ["C", "C", "G"],
                "Tumor_Seq_Allele2": ["T", "T", "A"],
                "t_ref_count": [90, 85, 80],
                "t_alt_count": [10, 15, 20],
            }
        )

    @pytest.fixture()
    def maf_no_match(self):
        """MAF where ACCESS and IMPACT have NO shared variants."""
        return pd.DataFrame(
            {
                "Tumor_Sample_Barcode": [
                    "ACCESS_S1",  # ACCESS variant
                    "IMPACT_S1",  # IMPACT variant (different position)
                ],
                "Mutation_Status": ["SOMATIC", "SOMATIC"],
                "Chromosome": ["7", "12"],
                "Start_Position": [55249071, 25398284],
                "End_Position": [55249071, 25398284],
                "Reference_Allele": ["C", "G"],
                "Tumor_Seq_Allele2": ["T", "A"],
                "t_ref_count": [90, 85],
                "t_alt_count": [10, 15],
            }
        )

    def test_shared_variant_gives_match(self, clinical, maf_with_match):
        """ACCESS sample sharing variant with IMPACT → has_impact_match=True."""
        from kreview.labels import compute_impact_match

        result = compute_impact_match(
            {"ACCESS_S1", "ACCESS_S2"}, maf_with_match, clinical
        )
        s1 = result.set_index("SAMPLE_ID").loc["ACCESS_S1"]

        assert s1["has_impact_match"]
        assert s1["n_impact_confirmed"] >= 1

    def test_no_shared_variant_no_match(self, clinical, maf_no_match):
        """ACCESS sample with NO shared variant → has_impact_match=False."""
        from kreview.labels import compute_impact_match

        result = compute_impact_match({"ACCESS_S1"}, maf_no_match, clinical)
        s1 = result.set_index("SAMPLE_ID").loc["ACCESS_S1"]

        assert not s1["has_impact_match"]
        assert s1["n_impact_confirmed"] == 0

    def test_has_paired_impact_flag(self, clinical, maf_with_match):
        """Patient P1 has IMPACT sample → ACCESS_S1 has_paired_impact=True.
        Patient P2 does NOT → ACCESS_S2 has_paired_impact=False.
        """
        from kreview.labels import compute_impact_match

        result = compute_impact_match(
            {"ACCESS_S1", "ACCESS_S2"}, maf_with_match, clinical
        )
        s1 = result.set_index("SAMPLE_ID").loc["ACCESS_S1"]
        s2 = result.set_index("SAMPLE_ID").loc["ACCESS_S2"]

        assert s1["has_paired_impact"]
        assert not s2["has_paired_impact"]

    def test_output_columns(self, clinical, maf_with_match):
        """Output DataFrame should have expected columns."""
        from kreview.labels import compute_impact_match

        result = compute_impact_match({"ACCESS_S1"}, maf_with_match, clinical)
        expected_cols = {
            "SAMPLE_ID",
            "has_impact_match",
            "n_impact_confirmed",
            "has_paired_impact",
        }

        assert expected_cols.issubset(set(result.columns))

    def test_empty_maf(self, clinical):
        """Empty MAF (no rows) → all samples get has_impact_match=False."""
        from kreview.labels import compute_impact_match

        empty_maf = pd.DataFrame(
            columns=[
                "Tumor_Sample_Barcode",
                "Mutation_Status",
                "Chromosome",
                "Start_Position",
                "End_Position",
                "Reference_Allele",
                "Tumor_Seq_Allele2",
                "t_ref_count",
                "t_alt_count",
            ]
        )
        result = compute_impact_match({"ACCESS_S1"}, empty_maf, clinical)

        assert len(result) == 1
        s1 = result.set_index("SAMPLE_ID").loc["ACCESS_S1"]
        assert not s1["has_impact_match"]
        assert s1["n_impact_confirmed"] == 0


# ── Train/Test Split tests (v0.0.16+) ────────────────────────────────────────


class TestAssignTrainTestSplit:
    """Tests for _assign_train_test_split() — stratified holdout assignment.

    Validates:
      - Modelable labels get 'train'/'test', non-modelable get 'exclude'
      - Proportions approximate 80/20
      - Deterministic with same random_state
      - Undetermined and Insufficient Data are excluded
      - Too-few-samples fallback assigns all to 'train'
    """

    @pytest.fixture()
    def labeler(self):
        """Bare CtDNALabeler instance for split testing (bypasses data loading)."""
        from kreview.core import LabelConfig

        # Use object.__new__ to avoid __init__ which requires Paths + loads data
        instance = object.__new__(CtDNALabeler)
        instance.config = LabelConfig()
        return instance

    @pytest.fixture()
    def label_df(self):
        """DataFrame with 100 modelable + 10 non-modelable samples."""
        labels = (
            ["True ctDNA+"] * 30
            + ["Possible ctDNA+"] * 25
            + ["Healthy Normal"] * 25
            + ["Possible ctDNA\u2212"] * 20
            + ["Undetermined"] * 5
            + ["Insufficient Data"] * 5
        )
        return pd.DataFrame(
            {
                "SAMPLE_ID": [f"S{i:03d}" for i in range(110)],
                "label": labels,
            }
        )

    def test_modelable_get_train_or_test(self, labeler, label_df):
        """Modelable samples should have split == 'train' or 'test'."""
        result = labeler._assign_train_test_split(label_df.copy())
        modelable = result[~result["label"].isin(["Undetermined", "Insufficient Data"])]
        assert set(modelable["split"].unique()) == {"train", "test"}

    def test_non_modelable_excluded(self, labeler, label_df):
        """Undetermined and Insufficient Data samples get split='exclude'."""
        result = labeler._assign_train_test_split(label_df.copy())
        excluded = result[result["label"].isin(["Undetermined", "Insufficient Data"])]
        assert (excluded["split"] == "exclude").all(), (
            f"Non-modelable samples should be 'exclude', got: "
            f"{excluded['split'].value_counts().to_dict()}"
        )

    def test_proportions_approximate_80_20(self, labeler, label_df):
        """Train/test split should be approximately 80/20."""
        result = labeler._assign_train_test_split(label_df.copy())
        n_train = (result["split"] == "train").sum()
        n_test = (result["split"] == "test").sum()
        test_fraction = n_test / (n_train + n_test)
        assert (
            0.15 <= test_fraction <= 0.25
        ), f"Expected test fraction ~0.20, got {test_fraction:.3f}"

    def test_deterministic_same_seed(self, labeler, label_df):
        """Same random_state should produce identical splits."""
        r1 = labeler._assign_train_test_split(label_df.copy(), random_state=42)
        r2 = labeler._assign_train_test_split(label_df.copy(), random_state=42)
        pd.testing.assert_series_equal(
            r1["split"].reset_index(drop=True),
            r2["split"].reset_index(drop=True),
        )

    def test_different_seed_different_split(self, labeler, label_df):
        """Different random_state should produce different splits."""
        r1 = labeler._assign_train_test_split(label_df.copy(), random_state=42)
        r2 = labeler._assign_train_test_split(label_df.copy(), random_state=99)
        # At least some samples should swap train/test
        diff = (r1["split"].values != r2["split"].values).sum()
        assert diff > 0, "Different seeds should produce different splits"

    def test_too_few_samples_fallback(self, labeler):
        """With < 20 modelable samples, all should get split='train'."""
        small = pd.DataFrame(
            {
                "SAMPLE_ID": [f"S{i}" for i in range(15)],
                "label": ["True ctDNA+"] * 8 + ["Healthy Normal"] * 7,
            }
        )
        result = labeler._assign_train_test_split(small)
        assert (
            result["split"] == "train"
        ).all(), "All samples should be 'train' when n_modelable < 20"

    def test_split_column_exists(self, labeler, label_df):
        """Output DataFrame must have a 'split' column."""
        result = labeler._assign_train_test_split(label_df.copy())
        assert "split" in result.columns
        # Only valid values
        assert set(result["split"].unique()).issubset({"train", "test", "exclude"})
