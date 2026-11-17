"""Tests for the command line: a drawing's style block applies, and a flag overrides it."""

import sys

import pytest

import gtdraw
from gtdraw.cli import main

BODY = (
    "level 0 node 1 player 1\n"
    "level 1 node 1 xshift -1 from 1,1 move a payoffs 1 0\n"
    "level 1 node 2 xshift 1 from 1,1 move b payoffs 0 1\n"
    "level 2 node 1 xshift -1 from 1,1 move c\n"
    "level 2 node 2 xshift 1 from 1,2 move d\n"
    "iset 2,1 2,2 player 2\n"
)

BLOCK = (
    "% gtdraw: edge_thickness 1.6\n"
    "% gtdraw: color_scheme custom\n"
    "% gtdraw: scale_factor 0.5\n"
    "% gtdraw: node_size 2.5\n"
    "% gtdraw: iset_boundary solid\n"
    '% gtdraw: custom_colors {"1": "#123456"}\n'
)


@pytest.fixture
def drawing(tmp_path):
    path = tmp_path / "game.ef"
    path.write_text(BLOCK + BODY)
    return str(path)


def cli(capsys, monkeypatch, *args):
    """Run the command line; return (stdout, stderr, exit code or None)."""
    monkeypatch.setattr(sys, "argv", ["gtdraw", *args])
    code = None
    try:
        main()
    except SystemExit as e:
        code = e.code
    out, err = capsys.readouterr()
    return out, err, code


def api(path, **options):
    return gtdraw.tikz(path) if not options else gtdraw.tikz(path, **options)


def test_block_applies_without_a_flag(capsys, monkeypatch, drawing):
    out, err, code = cli(capsys, monkeypatch, drawing)
    assert code is None
    assert out == api(drawing) + "\n"
    assert "\\treethickn1.6pt" in out
    assert out != api(drawing, edge_thickness=1.0) + "\n"


@pytest.mark.parametrize(
    "flag, options",
    [
        ("--edge-thickness=2.0", {"edge_thickness": 2.0}),
        ("--edge-thickness=1.0", {"edge_thickness": 1.0}),  # equal to the default
        ("--color-scheme=default", {"color_scheme": "default"}),  # equal to the default
        ("scale=1.0", {"scale_factor": 1.0}),  # equal to the default
        ("grid", {"show_grid": True}),
        ("--iset-dotted", {"iset_boundary": "dotted"}),
        ("--custom-colors=1:#abcdef", {"custom_colors": {1: "#abcdef"}}),
        ("--node-size=1.5", {"node_size": 1.5}),  # equal to the default
    ],
)
def test_flag_beats_the_block(capsys, monkeypatch, drawing, flag, options):
    out, err, code = cli(capsys, monkeypatch, drawing, flag)
    assert code is None
    assert out == api(drawing, **options) + "\n"
    assert out != api(drawing) + "\n"


def test_rejected_value_leaves_the_block(capsys, monkeypatch, drawing):
    out, err, code = cli(capsys, monkeypatch, drawing, "--node-size=big")
    assert code is None
    assert "Invalid node-size" in err
    assert out == api(drawing) + "\n"


@pytest.mark.parametrize("flag", ["--font=bogus", "scale=0", "--edge-thickness=big"])
def test_other_rejected_values_leave_the_block(capsys, monkeypatch, drawing, flag):
    out, err, code = cli(capsys, monkeypatch, drawing, flag)
    assert out == api(drawing) + "\n"


def test_malformed_block_exits_with_its_line(capsys, monkeypatch, tmp_path):
    path = tmp_path / "bad.ef"
    path.write_text("% gtdraw: node_size 2\n% gtdraw: edge_thickness fat\n" + BODY)
    out, err, code = cli(capsys, monkeypatch, str(path))
    assert code == 1
    assert out == ""
    assert "line 2" in err


def test_no_block_matches_the_api(capsys, monkeypatch, tmp_path):
    path = tmp_path / "plain.ef"
    path.write_text(BODY)
    out, err, code = cli(capsys, monkeypatch, str(path))
    assert out == api(str(path)) + "\n"
