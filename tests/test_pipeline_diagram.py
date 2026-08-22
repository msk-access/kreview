"""The drawn DAG must stay the real DAG.

The diagram names Nextflow processes as strings, so nothing but a test stops the
pipeline gaining a stage while the picture keeps describing the old topology.
"""

import re
from pathlib import Path

import pytest

from kreview.pipeline_diagram import (
    CLUSTERS,
    LEVELS,
    NODE_H,
    NODE_W,
    PIPELINE_NODES,
    declared_processes,
    mini_store,
    mini_svg,
    node_names,
    node_process_map,
    pipeline_svg,
)

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / "nextflow" / "workflows"


def workflow_processes() -> set[str]:
    """Every kreview process the eval workflow includes."""
    found: set[str] = set()
    for nf in WORKFLOWS.glob("*.nf"):
        found |= set(
            re.findall(r"include\s*\{\s*(KREVIEW_[A-Z_0-9]+)\s*\}", nf.read_text())
        )
    return found


@pytest.mark.skipif(not WORKFLOWS.exists(), reason="nextflow sources not in this tree")
def test_every_workflow_process_is_drawn():
    missing = workflow_processes() - declared_processes()
    assert (
        not missing
    ), f"stages in the DAG but absent from the diagram: {sorted(missing)}"


@pytest.mark.skipif(not WORKFLOWS.exists(), reason="nextflow sources not in this tree")
def test_no_invented_processes():
    invented = declared_processes() - workflow_processes()
    assert (
        not invented
    ), f"diagram names processes the workflow does not include: {sorted(invented)}"


def test_clusters_reference_known_nodes_and_processes():
    assert set(CLUSTERS) <= set(PIPELINE_NODES)
    for node, stages in CLUSTERS.items():
        flat = [p for stage in stages for p in stage]
        assert set(flat) <= declared_processes()
        # a cluster panel that omitted one of its node's processes would under-report
        assert set(flat) <= set(PIPELINE_NODES[node]["procs"])


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_level_renders_accessibly_and_deterministically(level):
    svg = pipeline_svg(level)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert f'aria-labelledby="pd-{level}-t pd-{level}-d"' in svg
    assert f'<title id="pd-{level}-t">' in svg and f'<desc id="pd-{level}-d">' in svg
    assert svg == pipeline_svg(level), "SVG generation must be deterministic"


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_nodes_do_not_overlap(level):
    """Boxes are placed on a declared grid; two on the same cell is a layout bug."""
    boxes = [
        (int(x), int(y))
        for x, y in re.findall(
            rf'<rect x="(\d+)" y="(\d+)" width="{NODE_W}" height="{NODE_H}" rx="6" fill="#f7f8fa"',
            pipeline_svg(level),
        )
    ]
    assert boxes
    for i, (ax, ay) in enumerate(boxes):
        for bx, by in boxes[i + 1 :]:
            assert not (
                ax < bx + NODE_W
                and bx < ax + NODE_W
                and ay < by + NODE_H
                and by < ay + NODE_H
            ), f"nodes overlap at ({ax},{ay}) and ({bx},{by}) in level {level}"


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_coordinates_stay_on_the_four_pixel_grid(level):
    svg = pipeline_svg(level)
    coords = [int(v) for v in re.findall(r'<rect x="(\d+)" y="\d+" width="160"', svg)]
    coords += [int(v) for v in re.findall(r'<rect x="\d+" y="(\d+)" width="160"', svg)]
    assert coords and all(c % 4 == 0 for c in coords)


def test_chips_are_opt_out_for_the_methods_copy():
    assert "pd-chiptext" in pipeline_svg("standard")
    # an empty status slot in a tab with no run to report reads as missing data
    assert "pd-chiptext" not in pipeline_svg("standard", chips=False)


def test_mini_topologies_stay_inside_their_viewbox():
    for cluster in CLUSTERS:
        svg = mini_svg(cluster)
        width = int(re.search(r'viewBox="0 0 (\d+) (\d+)"', svg).group(1))
        xs = [
            int(x) for x in re.findall(r'<rect x="(-?\d+)" y="-?\d+" width="148"', svg)
        ]
        assert xs, cluster
        assert (
            min(xs) >= 0 and max(xs) + 148 <= width
        ), f"{cluster} sub-diagram is clipped"


def test_store_and_maps_cover_every_cluster():
    store = mini_store()
    for cluster in CLUSTERS:
        assert f'data-cluster="{cluster}"' in store
    assert set(node_process_map()) == set(PIPELINE_NODES) == set(node_names())


def test_unknown_level_raises():
    with pytest.raises(KeyError):
        pipeline_svg("faithful")


def test_docs_copies_are_regenerated():
    """The committed docs pages must match the module, or they are a second source."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_diagrams", REPO / "scripts" / "build_diagrams.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in mod.PAGES:
        committed = REPO / "docs" / "diagrams" / name
        assert committed.exists(), f"{name} missing — run scripts/build_diagrams.py"
        assert committed.read_text() == mod.render(
            name
        ), f"{name} is stale — run scripts/build_diagrams.py and commit the result"
