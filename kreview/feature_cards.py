# kreview/feature_cards.py — Auto-generated feature metadata cards.

from __future__ import annotations
import inspect
import structlog

log = structlog.get_logger()

__all__ = ["log", "TIER_LABELS", "build_feature_cards", "get_card_for_feature"]


TIER_LABELS = {
    1: "Core Fragmentation",
    2: "Epigenetics & Geometry",
    3: "Motif Sequence",
}

# Derived feature keywords detected via source introspection
_DERIVED_KEYWORDS = [
    "entropy",
    "bimodality",
    "spectral",
    "chrom_cv",
    "dnase1l3",
    "top10",
    "frac_diverged",
    "concentration",
    "peak_valley",
    "mad",
]


def build_feature_cards() -> dict[str, dict]:
    """Auto-generate feature metadata cards from the evaluator registry.

    Each card includes:
    - display_name: Human-readable evaluator name
    - source_file: Parquet file suffix (e.g. ``.FSR.ontarget.parquet``)
    - tier: Numeric tier (1–3)
    - tier_label: Human-readable tier label
    - category: Feature family (fragmentation, epigenetics_and_geometry, etc.)
    - has_derived: Whether the evaluator computes derived features
    - derived_types: List of derived feature types present

    Returns:
        Dictionary keyed by evaluator name.
    """
    from kreview.registry import get_all_evaluators

    cards = {}
    for e in get_all_evaluators():
        # Detect derived features via source code introspection
        try:
            src = inspect.getsource(type(e).extract)
        except (OSError, TypeError):
            src = ""

        derived_types = [kw for kw in _DERIVED_KEYWORDS if kw in src]

        cards[e.name] = {
            "display_name": e.name,
            "source_file": e.source_file,
            "tier": e.tier,
            "tier_label": TIER_LABELS.get(e.tier, f"Tier {e.tier}"),
            "category": e.category,
            "has_derived": len(derived_types) > 0,
            "derived_types": derived_types,
        }

    log.debug("feature_cards_built", n_cards=len(cards))
    return cards


def get_card_for_feature(feature_name: str, cards: dict) -> dict | None:
    """Look up the most likely card for a feature column name.

    Matches by checking if the feature name contains the evaluator's
    name (case-insensitive prefix matching).  Returns None if no match.
    """
    fn_lower = feature_name.lower()
    for name, card in cards.items():
        # Normalize evaluator name to match feature column prefixes
        # e.g. FSCOnTarget -> fscontarget, FsrGenomewide -> fsrgenomewide
        prefix = name.lower()
        if fn_lower.startswith(prefix) or prefix.replace("evaluator", "") in fn_lower:
            return card
    return None
