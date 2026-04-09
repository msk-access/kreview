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
