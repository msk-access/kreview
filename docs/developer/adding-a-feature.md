# Adding a Feature

Extending the pipeline is incredibly easy! Thanks to our dynamic class registry (`registry.get_all_evaluators`), any feature you construct will be automatically mapped, tested, and reported upon by `kreview run` globally.

---

## 1. Create the Notebook

Create a new file in the `nbs/` directory. By convention, label it with the module increment. Let's build a dummy "GC Content Feature".

```bash
touch nbs/15_gc_content.ipynb
```

In the first cell, map the export location:
```python
#| default_exp features.gc_evaluator
```

## 2. Inherit from `FeatureEvaluator`

```python
#| export
from kreview.eval_engine import FeatureEvaluator
import pandas as pd
import numpy as np

class GCEvaluator(FeatureEvaluator):
    """Calculates GC% metrics from sequencing data."""
    
    # 1. Define Standard Metadata
    name: str = "GC_Coverage" 
    source_file: str = ".gc.parquet" # The suffix from MSK Krewlyzer parquet drops
    tier: int = 2
    category: str = "coverage"
    
    # 2. Implement the mandatory extraction contract!
    def extract(self, df: pd.DataFrame) -> dict[str, float]:
        """Convert standard DuckDB parquet loads into scalar ML features."""
        
        # If your DuckDB query failed and pushed an empty DF, escape safely
        if df.empty:
            return {}
            
        metrics = {}
        
        # Pull your metrics
        metrics["median_gc"] = df["gc_ratio"].median()
        metrics["max_gc_shift"] = df["gc_ratio"].max()
        
        return metrics
```

## 3. That's It!

Run `nbdev_export`. Your class will be scraped and published into `kreview/features/gc_evaluator.py`.

Because `GCEvaluator` subclasses our root `FeatureEvaluator`, `registry.py` will actively discover it the next time you call `kreview run`, bind it to the CLI tree, build the biological ctDNA cohorts, inject it into the DuckDB data lake aggregator, run Sklearn metrics across it, and publish an HTML dashboard for it!
