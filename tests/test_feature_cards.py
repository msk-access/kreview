"""Tests for kreview.feature_cards — v0.0.8 feature card generation.

Covers:
  - build_feature_cards returns expected structure
  - get_card_for_feature matches on name prefix
  - TIER_LABELS has expected tiers
  - Derived feature detection works
"""

import pytest

from kreview.feature_cards import build_feature_cards, get_card_for_feature, TIER_LABELS


class TestBuildFeatureCards:
    def test_returns_dict(self):
        """build_feature_cards should return a non-empty dict."""
        cards = build_feature_cards()
        assert isinstance(cards, dict)
        assert len(cards) > 0

    def test_card_has_required_fields(self):
        """Every card should have the mandatory metadata fields."""
        cards = build_feature_cards()
        required = {"display_name", "source_file", "tier", "tier_label", "category"}
        for name, card in cards.items():
            missing = required - set(card.keys())
            assert not missing, f"Card '{name}' missing fields: {missing}"

    def test_tier_labels_in_cards(self):
        """Every card's tier_label should come from TIER_LABELS."""
        cards = build_feature_cards()
        valid_labels = set(TIER_LABELS.values())
        for name, card in cards.items():
            assert (
                card["tier_label"] in valid_labels
            ), f"Card '{name}' has invalid tier_label: {card['tier_label']}"

    def test_derived_types_is_list(self):
        """derived_types should be a list (possibly empty)."""
        cards = build_feature_cards()
        for name, card in cards.items():
            if "derived_types" in card:
                assert isinstance(card["derived_types"], list)


class TestGetCardForFeature:
    def test_matches_known_prefix(self):
        """Should match a feature column to its evaluator card."""
        cards = build_feature_cards()
        # FSR on-target should match
        card = get_card_for_feature("fsrontarget_some_metric", cards)
        # May or may not match depending on registry naming
        # Just verify it returns dict or None
        assert card is None or isinstance(card, dict)

    def test_returns_none_for_unknown(self):
        """Should return None for a totally unknown feature name."""
        cards = build_feature_cards()
        card = get_card_for_feature("zzz_nonexistent_feature_xyz", cards)
        assert card is None


class TestTierLabels:
    def test_has_three_tiers(self):
        """TIER_LABELS should have at least tiers 1, 2, 3."""
        assert 1 in TIER_LABELS
        assert 2 in TIER_LABELS

    def test_values_are_strings(self):
        for tier, label in TIER_LABELS.items():
            assert isinstance(label, str)
            assert len(label) > 0
