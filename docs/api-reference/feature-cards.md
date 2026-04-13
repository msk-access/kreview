# Feature Cards API Reference

The `kreview.feature_cards` module auto-generates metadata cards for each evaluator registered in the kreview system. These cards provide structured clinical context that enriches the dashboard's Feature Explanation page.

For the dashboard rendering context, see [Dashboard Guide](../machine-learning/dashboard-guide.md#page-3-feature-explanation-shap).

---

## Functions

### `build_feature_cards()`

Auto-generates feature metadata from the evaluator registry.

**Returns:** `dict[str, dict]` — Dictionary keyed by evaluator name, with values containing:

| Field | Type | Description |
|-------|------|-------------|
| `display_name` | `str` | Human-readable evaluator name |
| `source_file` | `str` | Parquet file suffix (e.g. `.FSR.ontarget.parquet`) |
| `tier` | `int` | Feature tier (1=Core Fragmentation, 2=Epigenetics & Geometry, 3=Motif Sequence) |
| `tier_label` | `str` | Human-readable tier label |
| `category` | `str` | Feature family (fragmentation, epigenetics_and_geometry, motifs) |
| `has_derived` | `bool` | Whether the evaluator computes derived features |
| `derived_types` | `list[str]` | Detected derived feature types (entropy, spectral, bimodality, etc.) |

**Derived feature detection** uses source code introspection (`inspect.getsource()`) to search for keywords in the evaluator's `extract()` method.

---

### `get_card_for_feature(feature_name, cards)`

Looks up the most likely card for a feature column name.

**Parameters:**

- `feature_name` (`str`) — Column name from the feature matrix (e.g. `fsrontarget_chr1_fsr_median`)
- `cards` (`dict`) — Dictionary returned by `build_feature_cards()`

**Returns:** `dict | None` — The matching card, or `None` if no match found.

Matching uses case-insensitive prefix comparison between the feature column name and evaluator names.

---

## Example

```python
from kreview.feature_cards import build_feature_cards, get_card_for_feature

cards = build_feature_cards()  # 26 cards from registry

# Look up a specific feature column
card = get_card_for_feature("fsrontarget_chr1_fsr_median", cards)
print(card)
# {'display_name': 'FsrOnTarget', 'source_file': '.FSR.ontarget.parquet',
#  'tier': 1, 'tier_label': 'Core Fragmentation', 'category': 'fragmentation',
#  'has_derived': True, 'derived_types': ['bimodality', 'chrom_cv']}
```

---

## Constants

### `TIER_LABELS`

```python
TIER_LABELS = {
    1: "Core Fragmentation",
    2: "Epigenetics & Geometry",
    3: "Motif Sequence",
}
```
