"""Guards on the notebooks themselves, so the export stays reproducible.

nbdev derives each generated cell's hash from the notebook cell. A notebook written
without cell ids (nbformat 4.4) makes that hash unstable, so `nbdev-export` emits a
different module on every run and never reaches a fixed point — and the export-sync
gate then fails on whichever unrelated PR happens to touch a notebook next. This
caught exactly that on the pipeline-diagram module (#127).
"""

import json
import re
from pathlib import Path

import pytest

NBS = sorted((Path(__file__).resolve().parents[1] / "nbs").rglob("*.ipynb"))
NB_IDS = [str(p.relative_to(p.parents[1])) for p in NBS]


def test_notebooks_exist():
    assert NBS, "no notebooks found — nbs/ is the source of truth for kreview/*.py"


@pytest.mark.parametrize("nb_path", NBS, ids=NB_IDS)
def test_notebook_declares_cell_ids(nb_path: Path):
    """nbformat >= 4.5, so every cell carries a stable id."""
    nb = json.loads(nb_path.read_text())
    minor = nb.get("nbformat_minor", 0)
    assert nb.get("nbformat") == 4 and minor >= 5, (
        f"{nb_path.name} is nbformat 4.{minor}; cell ids arrive at 4.5 and without them "
        "nbdev's export hash moves on every run"
    )


@pytest.mark.parametrize("nb_path", NBS, ids=NB_IDS)
def test_every_cell_has_a_unique_id(nb_path: Path):
    nb = json.loads(nb_path.read_text())
    ids = [c.get("id") for c in nb["cells"]]
    missing = [i for i, v in enumerate(ids) if not v]
    assert not missing, f"{nb_path.name}: cells {missing} have no id"
    assert len(set(ids)) == len(ids), f"{nb_path.name}: duplicate cell ids"


@pytest.mark.parametrize("nb_path", NBS, ids=NB_IDS)
def test_exported_notebooks_name_their_module(nb_path: Path):
    """A notebook that exports code must declare where it exports to."""
    nb = json.loads(nb_path.read_text())
    sources = ["".join(c["source"]) for c in nb["cells"]]
    # nbdev accepts both `#| export` and `# | export`; this repo uses both spellings
    exports = re.compile(r"#\s*\|\s*export")
    default_exp = re.compile(r"#\s*\|\s*default_exp\s+\S")
    if not any(exports.search(s) for s in sources):
        pytest.skip("notebook exports nothing")
    assert any(default_exp.search(s) for s in sources), (
        f"{nb_path.name} has #| export cells but no #| default_exp — "
        "nbdev cannot tell which module to write"
    )
