"""Tests for kreview.core — Phase 1 audit fixes (C-04).

Covers:
  - Package import and version
  - Paths dataclass construction
  - LabelConfig defaults
  - Manifest file expansion
  - IMPACT_PANELS and ACCESS_PANELS constants
"""

import kreview
import pytest

from kreview.core import Paths, LabelConfig, IMPACT_PANELS, ACCESS_PANELS


def test_import():
    """Verify the package can be successfully imported."""
    assert kreview.__version__ is not None


class TestPaths:
    def test_construction(self, tmp_path):
        """Paths should accept all required fields."""
        p = Paths(
            cancer_samplesheet=tmp_path / "cancer.csv",
            healthy_xs1_samplesheet=tmp_path / "xs1.csv",
            healthy_xs2_samplesheet=tmp_path / "xs2.csv",
            cbioportal_dir=tmp_path / "cbio",
            krewlyzer_dirs=[tmp_path / "krew"],
        )
        assert str(p.cancer_samplesheet).endswith("cancer.csv")

    def test_manifest_expansion(self, tmp_path):
        """A .txt manifest file should be expanded to a list of directories."""
        manifest = tmp_path / "manifest.txt"
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        manifest.write_text(f"{dir1}\n{dir2}\n")

        p = Paths(
            cancer_samplesheet=tmp_path / "cancer.csv",
            healthy_xs1_samplesheet=tmp_path / "xs1.csv",
            healthy_xs2_samplesheet=tmp_path / "xs2.csv",
            cbioportal_dir=tmp_path / "cbio",
            krewlyzer_dirs=[str(manifest)],
        )
        # After post_init expansion, should have 2 dirs
        assert len(p.krewlyzer_dirs) == 2


class TestLabelConfig:
    def test_defaults(self):
        """LabelConfig should have sensible defaults."""
        c = LabelConfig()
        assert c.min_vaf == 0.01
        assert c.min_variants == 1
        assert c.min_fragments == 2000
        assert len(c.access_panels) > 0
        assert len(c.impact_panels) > 0

    def test_custom_values(self):
        """LabelConfig should accept custom thresholds."""
        c = LabelConfig(min_vaf=0.05, min_variants=3)
        assert c.min_vaf == 0.05
        assert c.min_variants == 3


class TestConstants:
    def test_impact_panels_not_empty(self):
        assert len(IMPACT_PANELS) >= 3

    def test_access_panels_not_empty(self):
        assert len(ACCESS_PANELS) >= 1


# ── make_variant_key tests ───────────────────────────────────────────────────

import numpy as np
import pandas as pd

from kreview.core import make_variant_key, VARIANT_KEY_COLS, LABEL_META_COLS


class TestMakeVariantKey:
    """Tests for make_variant_key() — genomic coordinate hashing."""

    def test_produces_tuple_key(self):
        """Each row should produce a (chrom, start, end, ref, alt) tuple."""
        df = pd.DataFrame(
            {
                "Chromosome": ["7"],
                "Start_Position": [55249071],
                "End_Position": [55249071],
                "Reference_Allele": ["C"],
                "Tumor_Seq_Allele2": ["T"],
            }
        )
        keys = make_variant_key(df)
        assert len(keys) == 1
        assert keys.iloc[0] == ("7", 55249071, 55249071, "C", "T")

    def test_multiple_rows(self):
        """Should produce one key per row."""
        df = pd.DataFrame(
            {
                "Chromosome": ["7", "12"],
                "Start_Position": [100, 200],
                "End_Position": [100, 200],
                "Reference_Allele": ["C", "G"],
                "Tumor_Seq_Allele2": ["T", "A"],
            }
        )
        keys = make_variant_key(df)
        assert len(keys) == 2
        assert keys.iloc[0] != keys.iloc[1]

    def test_missing_column_raises(self):
        """Missing required column should raise KeyError."""
        df = pd.DataFrame(
            {
                "Chromosome": ["7"],
                "Start_Position": [100],
                # Missing End_Position, Reference_Allele, Tumor_Seq_Allele2
            }
        )
        with pytest.raises(KeyError, match="Missing required col"):
            make_variant_key(df)

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty Series without error."""
        df = pd.DataFrame(columns=VARIANT_KEY_COLS)
        keys = make_variant_key(df)
        assert len(keys) == 0

    def test_position_cast_to_int(self):
        """Start_Position and End_Position should be cast to int in key."""
        df = pd.DataFrame(
            {
                "Chromosome": ["7"],
                "Start_Position": [100.0],  # float input
                "End_Position": [100.0],
                "Reference_Allele": ["C"],
                "Tumor_Seq_Allele2": ["T"],
            }
        )
        keys = make_variant_key(df)
        chrom, start, end, ref, alt = keys.iloc[0]
        assert isinstance(start, int)
        assert isinstance(end, int)


# ── LABEL_META_COLS tests ────────────────────────────────────────────────────


class TestLabelMetaCols:
    """Tests for LABEL_META_COLS — canonical exclusion set for features."""

    def test_contains_essential_columns(self):
        """LABEL_META_COLS should contain key label and metadata columns."""
        essential = {
            "label",
            "SAMPLE_ID",
            "PATIENT_ID",
            "CANCER_TYPE",
            "max_vaf",
            "has_snv",
            "has_sv",
            "has_cna",
        }
        missing = essential - LABEL_META_COLS
        assert not missing, f"LABEL_META_COLS missing essential columns: {missing}"

    def test_no_feature_column_names(self):
        """LABEL_META_COLS should NOT contain feature-like column names."""
        # Feature columns follow patterns like *_median, *_score, etc.
        for col in LABEL_META_COLS:
            assert not col.endswith(
                "_score"
            ), f"Feature-like column in LABEL_META_COLS: {col}"


# ── Data loader error handling tests ─────────────────────────────────────────


class TestDataLoaders:
    """Tests for data loading functions — error handling paths."""

    def test_load_maf_missing_file_raises(self):
        """load_maf should raise on nonexistent file."""
        from kreview.core import load_maf

        with pytest.raises((FileNotFoundError, Exception)):
            load_maf("/nonexistent/path/maf.txt")

    def test_load_sv_missing_file_raises(self):
        """load_sv should raise on nonexistent file."""
        from kreview.core import load_sv

        with pytest.raises((FileNotFoundError, Exception)):
            load_sv("/nonexistent/path/sv.txt")

    def test_load_cna_missing_file_raises(self):
        """load_cna should raise on nonexistent file."""
        from kreview.core import load_cna

        with pytest.raises((FileNotFoundError, Exception)):
            load_cna("/nonexistent/path/cna.txt")

    def test_load_clinical_sample_missing_file_raises(self):
        """load_clinical_sample should raise on nonexistent file."""
        from kreview.core import load_clinical_sample

        with pytest.raises((FileNotFoundError, Exception)):
            load_clinical_sample("/nonexistent/path/clinical.txt")
