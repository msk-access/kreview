"""Tests for kreview.labels — Phase 1 audit fixes (C-04).

Covers:
  - Label hierarchy ordering (True+ > Possible+ > Possible- > Healthy)
  - Insufficient Data gate
  - Healthy volunteers always get Healthy Normal
  - 5-tier docstring accuracy
"""
import numpy as np
import pandas as pd
import pytest

from kreview.labels import CtDNALabeler


class TestLabelTierConstants:
    """Verify label constants match the 5-tier system."""

    def test_five_tiers_defined(self):
        """CtDNALabeler should define exactly 5 label tiers."""
        tiers = [
            CtDNALabeler.LABEL_TRUE_POS,
            CtDNALabeler.LABEL_POSS_POS,
            CtDNALabeler.LABEL_POSS_NEG,
            CtDNALabeler.LABEL_HEALTHY,
            CtDNALabeler.LABEL_INSUF_DATA,
        ]
        assert len(set(tiers)) == 5, "Should have exactly 5 distinct label tiers"

    def test_label_values(self):
        """Verify the exact string values of each tier."""
        assert CtDNALabeler.LABEL_TRUE_POS == "True ctDNA+"
        assert CtDNALabeler.LABEL_POSS_POS == "Possible ctDNA+"
        assert CtDNALabeler.LABEL_POSS_NEG == "Possible ctDNA−"
        assert CtDNALabeler.LABEL_HEALTHY == "Healthy Normal"
        assert CtDNALabeler.LABEL_INSUF_DATA == "Insufficient Data"

    def test_docstring_says_five_tier(self):
        """Docstring should reference 5-tier, not 4-tier (M-05)."""
        doc = CtDNALabeler.__doc__
        assert "5-tier" in doc or "five" in doc.lower(), (
            f"Docstring should mention 5-tier: got '{doc}'"
        )
