from pathlib import Path

import pytest

import gtdraw.core as core
from gtdraw.converter import ef_to_efg
from gtdraw.layout_editor import (
    apply_layout_positions,
    normalise_layout_ef,
    parse_ef_layout,
    positions_changed,
)


EF1 = """\
player 1 name Alice
player 2 name Bob
level 0 node root player 1
level 2 node left xshift -1 from root move L
level 2 node right xshift 1 from root move R payoffs 1 0
iset left right player 2
"""


def test_parse_ef1_layout_and_iset_assignment():
    layout = parse_ef_layout(EF1)
    nodes = layout.node_map

    assert nodes["root"].x == 0
    assert nodes["root"].y == 0
    assert nodes["left"].x == -1
    assert nodes["left"].y == -2
    assert nodes["right"].x == 1
    assert nodes["right"].terminal is True
    assert nodes["right"].payoffs == ["1", "0"]
    assert layout.isets[0].node_ids == ["left", "right"]
    assert nodes["left"].player == 2


def test_component_payload_uses_player_colors_edge_labels_and_payoffs():
    layout = parse_ef_layout(EF1)
    payload = layout.to_component_payload({1: "#111111", 2: "#222222"})

    nodes = {node["id"]: node for node in payload["nodes"]}
    edge = next(edge for edge in payload["edges"] if edge["child"] == "left")

    assert nodes["root"]["color"] == "#111111"
    assert nodes["left"]["color"] == "#222222"
    assert edge["color"] == "#111111"
    assert edge["label"] == "L"
    assert nodes["right"]["payoffs"] == [
        {"text": "1", "color": "#111111"},
        {"text": "0", "color": "#222222"},
    ]
    assert payload["legend"] == [
        {"player": 1, "label": "Alice", "color": "#111111", "shape": "circle"},
        {"player": 2, "label": "Bob", "color": "#222222", "shape": "circle"},
    ]


def test_example_ef_editor_nodes_match_displayed_player_colors():
    ef_text = Path("games/example.ef").read_text(encoding="utf-8")
    layout = parse_ef_layout(normalise_layout_ef(ef_text))
    payload = layout.to_component_payload(
        {
            0: "#759138",  # chance green
            1: "#0000FF",  # player 1 blue
            2: "#FF00FF",  # player 2 pink
        }
    )
    nodes = {node["id"]: node for node in payload["nodes"]}

    assert nodes["n1"]["color"] == "#0000FF"
    assert nodes["n2"]["color"] == "#759138"
    assert nodes["n3"]["color"] == "#FF00FF"
    assert nodes["n5"]["color"] == "#FF00FF"


def test_example_ef_editor_edges_and_isets_match_displayed_player_colors():
    ef_text = Path("games/example.ef").read_text(encoding="utf-8")
    layout = parse_ef_layout(normalise_layout_ef(ef_text))
    payload = layout.to_component_payload(
        {
            0: "#759138",  # chance green
            1: "#0000FF",  # player 1 blue
            2: "#FF00FF",  # player 2 pink
        }
    )
    edges = {
        (edge["parent"], edge["child"]): edge["color"]
        for edge in payload["edges"]
    }
    isets = payload["isets"]

    assert edges[("n1", "n3")] == "#0000FF"
    assert edges[("n2", "n5")] == "#759138"
    assert edges[("n3", "n7")] == "#FF00FF"
    assert isets[0]["node_ids"] == ["n3", "n5"]
    assert isets[0]["color"] == "#FF00FF"


def test_parse_xshift_variables():
    ef = """\
player 1 name Alice
level 0 node root player 1
level 2 node a xshift -d=1.5 from root move A
level 2 node b xshift d from root move B
"""
    layout = parse_ef_layout(ef)

    assert layout.node_map["a"].x == -1.5
    assert layout.node_map["b"].x == 1.5


def test_apply_positions_updates_only_layout_fields():
    updated = apply_layout_positions(
        EF1,
        {
            "left": {"x": -2.25, "y": -3.5},
            "right": {"x": 1.25, "y": -2.75},
        },
    )

    assert "player 1 name Alice" in updated
    assert "level 3.5 node left xshift -2.25 from root move L" in updated
    assert "level 2.75 node right xshift 1.25 from root move R payoffs 1 0" in updated
    assert "iset left right player 2" in updated

    layout = parse_ef_layout(updated)
    assert layout.node_map["left"].player == 2
    assert layout.node_map["right"].player == 2


def test_root_drag_rewrites_child_relative_xshifts():
    updated = apply_layout_positions(EF1, {"root": {"x": 0.5, "y": -0.25}})

    assert "level 0.25 node root player 1 xshift 0.5" in updated
    assert "level 2 node left xshift -1.5 from root move L" in updated
    assert "level 2 node right xshift 0.5 from root move R payoffs 1 0" in updated


def test_legacy_ef0_is_normalised_before_dragging():
    ef0 = """\
player 1 name Alice
player 2 name Bob
level 0 node 1 player 1
level 2 node 1 xshift -1 from 0,1 move L
level 2 node 2 xshift 1 from 0,1 move R payoffs 1 0
iset 2,1 2,2 player 2
"""
    normalised = normalise_layout_ef(ef0)

    assert "level 0 node n1 player 1" in normalised
    assert "from n1 move L" in normalised
    assert "iset n2 n3 player 2" in normalised
    assert "," not in normalised.split("from", 1)[1].split(" ", 1)[0]


def test_positions_changed_detects_real_drag_only():
    layout = parse_ef_layout(EF1)

    assert positions_changed(layout, {"left": {"x": -1, "y": -2}}) is False
    assert positions_changed(layout, {"left": {"x": -1.5, "y": -2}}) is True


def test_fractional_level_renders_and_curved_iset_follows_drag(tmp_path):
    updated = apply_layout_positions(
        EF1,
        {
            "left": {"x": -2.25, "y": -3.5},
            "right": {"x": 1.25, "y": -2.75},
        },
    )
    ef_path = tmp_path / "dragged.ef"
    ef_path.write_text(updated, encoding="utf-8")

    tikz = core.tikz(str(ef_path), iset_curved=True)
    iset_lines = [line for line in tikz.splitlines() if ".. controls" in line]

    assert "(-2.25,-3.5)" in tikz
    assert any("-2.25,-3.5" in line for line in iset_lines)


def test_adjusted_ef_can_convert_to_loadable_efg(tmp_path):
    pygambit = pytest.importorskip("pygambit")
    updated = apply_layout_positions(EF1, {"left": {"x": -2, "y": -3}})
    ef_path = tmp_path / "dragged.ef"
    ef_path.write_text(updated, encoding="utf-8")

    efg_path = ef_to_efg(str(ef_path), save_to=str(tmp_path / "dragged.efg"))
    game = pygambit.read_efg(efg_path)

    assert len(game.players) == 2


def test_static_component_asset_contains_streamlit_bridge():
    asset = Path("src/gtdraw/components/layout_editor/index.html")
    html = asset.read_text(encoding="utf-8")

    assert "streamlit:setComponentValue" in html
    assert 'id="legend"' in html
    assert "function renderLegend()" in html
    assert "layout.legend" in html
    assert "legend-swatch" in html
    assert 'id="zoomSlider"' in html
    assert 'value="1.35"' in html
    assert "let zoom = Number(zoomSlider.value)" in html
    assert "zoomedWidth = width / zoom" in html
    assert 'zoomSlider.addEventListener("input"' in html
    assert "pointerdown" in html
    assert "isetPointerDown" in html
    assert "Dragging information set" in html
    assert 'kind: "iset"' in html
    assert "node.y -= displayDy" in html
    assert "iset-handle" in html
    assert "function isetHandlePoint(nodes)" in html
    assert "handle.addEventListener(\"pointerdown\", isetPointerDown)" in html
    assert "polyline" in html
    assert "node.label || node.id" not in html
    assert "edge-label" in html
    assert "payoff-label" in html
    assert "font-size: 0.34px" in html
    assert "font-size: 0.3px" in html
    assert "displayY(node) + 0.52" in html
    assert "dy: idx === 0 ? 0 : 0.34" in html
    assert "formatLabel(edge.label)" in html
    assert "node.payoffs.forEach" in html
    assert "function displayY(node)" in html
    assert "node.y = -(point.y + active.offsetY)" in html
    assert 'stroke: edge.color || "#243b53"' in html
    assert 'stroke: iset.color || "#8b5d33"' in html
    assert "stroke-width: 2.2px" in html
    assert "stroke-dasharray: 1px 7px" in html
    assert "stroke-width: 2.4px" in html
    assert "if (node.player >= 0 && node.color) return node.color" in html
    assert 'node.terminal ? "#fbbf24"' in html
