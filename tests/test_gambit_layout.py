"""
Test suite for draw_tree.gambit_layout module.

Tests for determine_node_level() and gambit_layout_to_ef() covering:
- Node level calculation with default and custom multipliers
- Simple 2-player games
- Chance nodes with fractional and whole-number probabilities
- Information sets (imperfect information)
- Player name space replacement
- Action label hiding
- Shared terminal depth
- Custom multiplier parameters
- File saving behaviour (with/without .ef extension, default naming)
- Terminal nodes without outcomes
"""

import os
import tempfile

import pygambit
import pytest

from draw_tree.gambit_layout import determine_node_level, gambit_layout_to_ef


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_game(title="test_game"):
    """Create a minimal 2-player game: Alice chooses Left/Right, terminal payoffs."""
    g = pygambit.Game.new_tree(players=["Alice", "Bob"], title=title)
    g.append_move(g.root, g.players[0], ["Left", "Right"])
    g.set_outcome(g.root.children[0], g.add_outcome([1, 0]))
    g.set_outcome(g.root.children[1], g.add_outcome([0, 1]))
    return g


def _asymmetric_game(title="asym_game"):
    """Alice chooses Left/Right; after Left Bob chooses Up/Down. Right is terminal."""
    g = pygambit.Game.new_tree(players=["Alice", "Bob"], title=title)
    g.append_move(g.root, g.players[0], ["Left", "Right"])
    g.append_move(g.root.children[0], g.players[1], ["Up", "Down"])
    g.set_outcome(g.root.children[0].children[0], g.add_outcome([1, 0]))
    g.set_outcome(g.root.children[0].children[1], g.add_outcome([0, 1]))
    g.set_outcome(g.root.children[1], g.add_outcome([2, 2]))
    return g


def _read_ef(path):
    with open(path) as f:
        return f.read()


# ---------------------------------------------------------------------------
# determine_node_level
# ---------------------------------------------------------------------------


class TestDetermineNodeLevel:
    """Unit tests for the determine_node_level helper."""

    def test_default_multipliers_level_zero_sublevel_one(self):
        # level=0, sublevel=1 → 0*4 - 2 + 0 = -2
        assert determine_node_level(0, 1) == -2.0

    def test_default_multipliers_level_one_sublevel_one(self):
        # level=1, sublevel=1 → 1*4 - 2 + 0 = 2
        assert determine_node_level(1, 1) == 2.0

    def test_default_multipliers_level_two(self):
        assert determine_node_level(2, 1) == 6.0

    def test_sublevel_zero_gives_no_extra_depth(self):
        # sublevel=0 means extra_depth=0
        assert determine_node_level(1, 0) == 2.0

    def test_sublevel_greater_than_one_adds_extra(self):
        # sublevel=2 → extra = (2-1)*2 = 2, total = 2+2 = 4
        assert determine_node_level(1, 2) == 4.0
        # sublevel=3 → extra = (3-1)*2 = 4, total = 2+4 = 6
        assert determine_node_level(1, 3) == 6.0

    def test_custom_multipliers(self):
        # level=2, sublevel=2, lm=6, sm=3
        # depth = 2*6 - 3 = 9, extra = (2-1)*3 = 3 → 12
        assert (
            determine_node_level(2, 2, level_multiplier=6, sublevel_multiplier=3)
            == 12.0
        )

    def test_large_level(self):
        assert determine_node_level(10, 1) == 10 * 4 - 2

    def test_negative_level_multiplier_raises(self):
        with pytest.raises(
            ValueError, match="level_multiplier must be non-negative"
        ):
            determine_node_level(1, 1, level_multiplier=-2)

    def test_negative_sublevel_multiplier_raises(self):
        with pytest.raises(
            ValueError, match="sublevel_multiplier must be non-negative"
        ):
            determine_node_level(1, 1, sublevel_multiplier=-1)

    def test_zero_multipliers_accepted(self):
        assert determine_node_level(1, 1, level_multiplier=0, sublevel_multiplier=0) == 0.0


# ---------------------------------------------------------------------------
# gambit_layout_to_ef – output content
# ---------------------------------------------------------------------------


class TestGambitLayoutToEfContent:
    """Tests that verify the textual content of the generated .ef string."""

    def test_player_lines(self):
        g = _simple_game()
        ef = gambit_layout_to_ef(g, save_to=os.path.join(tempfile.gettempdir(), "t.ef"))
        content = _read_ef(ef)
        os.unlink(ef)
        assert "player 1 name Alice" in content
        assert "player 2 name Bob" in content

    def test_player_names_spaces_replaced(self):
        g = pygambit.Game.new_tree(players=["Player One", "Player Two"], title="sp")
        g.append_move(g.root, g.players[0], ["A", "B"])
        g.set_outcome(g.root.children[0], g.add_outcome([1, 0]))
        g.set_outcome(g.root.children[1], g.add_outcome([0, 1]))
        ef = gambit_layout_to_ef(
            g, save_to=os.path.join(tempfile.gettempdir(), "sp.ef")
        )
        content = _read_ef(ef)
        os.unlink(ef)
        assert "Player~One" in content
        assert "Player~Two" in content

    def test_action_labels_present_by_default(self):
        g = _simple_game()
        ef = gambit_layout_to_ef(
            g, save_to=os.path.join(tempfile.gettempdir(), "al.ef")
        )
        content = _read_ef(ef)
        os.unlink(ef)
        assert "move Left" in content
        assert "move Right" in content

    def test_hide_action_labels(self):
        g = _simple_game()
        ef = gambit_layout_to_ef(
            g,
            save_to=os.path.join(tempfile.gettempdir(), "hid.ef"),
            hide_action_labels=True,
        )
        content = _read_ef(ef)
        os.unlink(ef)
        assert "move" not in content

    def test_payoffs_present(self):
        g = _simple_game()
        ef = gambit_layout_to_ef(
            g, save_to=os.path.join(tempfile.gettempdir(), "pay.ef")
        )
        content = _read_ef(ef)
        os.unlink(ef)
        assert "payoffs 1 0" in content
        assert "payoffs 0 1" in content

    def test_terminal_without_outcome(self):
        g = pygambit.Game.new_tree(players=["Alice", "Bob"], title="noout")
        g.append_move(g.root, g.players[0], ["L", "R"])
        ef = gambit_layout_to_ef(
            g, save_to=os.path.join(tempfile.gettempdir(), "no.ef")
        )
        content = _read_ef(ef)
        os.unlink(ef)
        # payoffs keyword still emitted but with no values
        lines = [l for l in content.splitlines() if "payoffs" in l]
        assert len(lines) == 2
        for line in lines:
            assert line.rstrip().endswith("payoffs")

    def test_root_has_no_xshift(self):
        g = _simple_game()
        ef = gambit_layout_to_ef(
            g, save_to=os.path.join(tempfile.gettempdir(), "rx.ef")
        )
        content = _read_ef(ef)
        os.unlink(ef)
        root_line = [
            l for l in content.splitlines() if "node 1" in l and "from" not in l
        ][0]
        assert "xshift" not in root_line

    def test_non_root_has_xshift(self):
        g = _simple_game()
        ef = gambit_layout_to_ef(
            g, save_to=os.path.join(tempfile.gettempdir(), "nx.ef")
        )
        content = _read_ef(ef)
        os.unlink(ef)
        child_lines = [l for l in content.splitlines() if "from" in l]
        for line in child_lines:
            assert "xshift" in line


# ---------------------------------------------------------------------------
# Chance nodes
# ---------------------------------------------------------------------------


class TestChanceNodes:
    def test_fractional_probability(self):
        g = pygambit.Game.new_tree(players=["Alice", "Bob"], title="frac")
        g.append_move(g.root, g.players.chance, ["H", "T"])
        g.set_chance_probs(g.root.infoset, ["1/2", "1/2"])
        g.append_move(g.root.children[0], g.players[0], ["A", "B"])
        g.set_outcome(g.root.children[0].children[0], g.add_outcome([1, 0]))
        g.set_outcome(g.root.children[0].children[1], g.add_outcome([0, 1]))
        g.set_outcome(g.root.children[1], g.add_outcome([2, 2]))

        ef = gambit_layout_to_ef(
            g, save_to=os.path.join(tempfile.gettempdir(), "fc.ef")
        )
        content = _read_ef(ef)
        os.unlink(ef)
        assert "player 0" in content
        assert "\\frac{1}{2}" in content

    def test_whole_number_probability(self):
        g = pygambit.Game.new_tree(players=["Alice"], title="whole")
        g.append_move(g.root, g.players.chance, ["X", "Y"])
        g.set_chance_probs(g.root.infoset, ["1", "0"])
        g.set_outcome(g.root.children[0], g.add_outcome([5]))
        g.set_outcome(g.root.children[1], g.add_outcome([0]))

        ef = gambit_layout_to_ef(
            g, save_to=os.path.join(tempfile.gettempdir(), "wh.ef")
        )
        content = _read_ef(ef)
        os.unlink(ef)
        assert "~1 " in content
        assert "~0 " in content


# ---------------------------------------------------------------------------
# Information sets
# ---------------------------------------------------------------------------


class TestInformationSets:
    def test_iset_line_generated(self):
        g = pygambit.Game.new_tree(players=["Alice", "Bob"], title="iset")
        g.append_move(g.root, g.players[0], ["Left", "Right"])
        g.append_move(g.root.children[0], g.players[1], ["Up", "Down"])
        g.append_infoset(g.root.children[1], g.root.children[0].infoset)
        for c in g.root.children:
            g.set_outcome(c.children[0], g.add_outcome([1, 0]))
            g.set_outcome(c.children[1], g.add_outcome([0, 1]))

        ef = gambit_layout_to_ef(
            g, save_to=os.path.join(tempfile.gettempdir(), "is.ef")
        )
        content = _read_ef(ef)
        os.unlink(ef)
        iset_lines = [l for l in content.splitlines() if l.startswith("iset")]
        assert len(iset_lines) == 1
        assert "player 2" in iset_lines[0]

    def test_iset_nodes_have_no_inline_player(self):
        """Nodes in a multi-node infoset should NOT have 'player' on their own line."""
        g = pygambit.Game.new_tree(players=["Alice", "Bob"], title="isnp")
        g.append_move(g.root, g.players[0], ["L", "R"])
        g.append_move(g.root.children[0], g.players[1], ["U", "D"])
        g.append_infoset(g.root.children[1], g.root.children[0].infoset)
        for c in g.root.children:
            g.set_outcome(c.children[0], g.add_outcome([1, 0]))
            g.set_outcome(c.children[1], g.add_outcome([0, 1]))

        ef = gambit_layout_to_ef(
            g, save_to=os.path.join(tempfile.gettempdir(), "inp.ef")
        )
        content = _read_ef(ef)
        os.unlink(ef)
        # The Bob decision node lines should not contain "player 2" inline
        bob_node_lines = [
            l
            for l in content.splitlines()
            if l.startswith("level") and "from" in l and "payoffs" not in l
        ]
        for line in bob_node_lines:
            assert "player" not in line


# ---------------------------------------------------------------------------
# shared_terminal_depth
# ---------------------------------------------------------------------------


class TestSharedTerminalDepth:
    def test_terminals_at_same_level_when_enabled(self):
        g = _asymmetric_game()
        ef = gambit_layout_to_ef(
            g,
            save_to=os.path.join(tempfile.gettempdir(), "std.ef"),
            shared_terminal_depth=True,
        )
        content = _read_ef(ef)
        os.unlink(ef)
        terminal_lines = [l for l in content.splitlines() if "payoffs" in l]
        levels = []
        for line in terminal_lines:
            parts = line.split()
            levels.append(float(parts[1]))  # "level <val> ..."
        assert len(set(levels)) == 1, f"Expected all same level, got {levels}"

    def test_terminals_at_different_levels_when_disabled(self):
        g = _asymmetric_game()
        ef = gambit_layout_to_ef(
            g,
            save_to=os.path.join(tempfile.gettempdir(), "nstd.ef"),
            shared_terminal_depth=False,
        )
        content = _read_ef(ef)
        os.unlink(ef)
        terminal_lines = [l for l in content.splitlines() if "payoffs" in l]
        levels = []
        for line in terminal_lines:
            parts = line.split()
            levels.append(float(parts[1]))
        assert len(set(levels)) > 1, f"Expected different levels, got {levels}"


# ---------------------------------------------------------------------------
# Custom multipliers
# ---------------------------------------------------------------------------


class TestCustomMultipliers:
    def test_level_multiplier_changes_levels(self):
        g = _simple_game()
        ef_default = gambit_layout_to_ef(
            g,
            save_to=os.path.join(tempfile.gettempdir(), "lmd.ef"),
        )
        ef_custom = gambit_layout_to_ef(
            g,
            save_to=os.path.join(tempfile.gettempdir(), "lmc.ef"),
            level_multiplier=6,
        )
        content_d = _read_ef(ef_default)
        content_c = _read_ef(ef_custom)
        os.unlink(ef_default)
        os.unlink(ef_custom)
        # With a larger multiplier, the level values should differ
        assert content_d != content_c

    def test_xshift_multiplier_changes_offsets(self):
        g = _simple_game()
        ef1 = gambit_layout_to_ef(
            g,
            save_to=os.path.join(tempfile.gettempdir(), "xs1.ef"),
            xshift_multiplier=2,
        )
        ef2 = gambit_layout_to_ef(
            g,
            save_to=os.path.join(tempfile.gettempdir(), "xs2.ef"),
            xshift_multiplier=4,
        )
        content1 = _read_ef(ef1)
        content2 = _read_ef(ef2)
        os.unlink(ef1)
        os.unlink(ef2)
        assert content1 != content2


# ---------------------------------------------------------------------------
# File saving behaviour
# ---------------------------------------------------------------------------


class TestFileSaving:
    def test_save_to_with_ef_extension(self):
        g = _simple_game()
        path = os.path.join(tempfile.gettempdir(), "with_ext.ef")
        result = gambit_layout_to_ef(g, save_to=path)
        assert result == path
        assert os.path.isfile(result)
        os.unlink(result)

    def test_save_to_without_ef_extension(self):
        g = _simple_game()
        path = os.path.join(tempfile.gettempdir(), "no_ext")
        result = gambit_layout_to_ef(g, save_to=path)
        assert result.endswith(".ef")
        assert os.path.isfile(result)
        os.unlink(result)

    def test_default_filename_uses_game_title(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        g = _simple_game(title="my_game")
        result = gambit_layout_to_ef(g)
        assert result == "my_game.ef"
        assert os.path.isfile(tmp_path / result)

    def test_file_content_is_utf8(self):
        g = _simple_game()
        path = os.path.join(tempfile.gettempdir(), "utf8.ef")
        gambit_layout_to_ef(g, save_to=path)
        with open(path, encoding="utf-8") as f:
            f.read()  # should not raise
        os.unlink(path)


# ---------------------------------------------------------------------------
# Child level > parent level invariant
# ---------------------------------------------------------------------------


class TestChildLevelInvariant:
    def test_child_levels_exceed_parent_levels(self):
        """Every non-root node must have a level strictly greater than its parent."""
        g = _asymmetric_game()
        ef = gambit_layout_to_ef(
            g,
            save_to=os.path.join(tempfile.gettempdir(), "inv.ef"),
        )
        content = _read_ef(ef)
        os.unlink(ef)
        # Build a map from node ID → level from all level lines (EF 3.0: bare node IDs)
        node_id_to_level = {}
        for line in content.splitlines():
            if not line.startswith("level"):
                continue
            parts = line.split()
            node_id_to_level[parts[3]] = float(parts[1])
        # Verify every child level exceeds its parent level
        for line in content.splitlines():
            if "from" not in line:
                continue
            parts = line.split()
            child_level = float(parts[1])
            from_idx = parts.index("from")
            parent_id = parts[from_idx + 1]
            parent_level = node_id_to_level[parent_id]
            assert child_level > parent_level, (
                f"Child level {child_level} <= parent level {parent_level}"
            )

    def test_generated_ef_is_detected_as_v3(self):
        """gambit_layout_to_ef generates EF 3.0 files (no duplicate node names)."""
        from draw_tree.core import _detect_ef_version
        g = _asymmetric_game()
        ef = gambit_layout_to_ef(
            g,
            save_to=os.path.join(tempfile.gettempdir(), "v3chk.ef"),
        )
        content = _read_ef(ef)
        os.unlink(ef)
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("%")]
        assert _detect_ef_version(lines) == 3

    def test_generated_ef_from_references_are_bare(self):
        """EF 3.0 output uses bare node IDs in 'from' references (no commas)."""
        g = _asymmetric_game()
        ef = gambit_layout_to_ef(
            g,
            save_to=os.path.join(tempfile.gettempdir(), "bare.ef"),
        )
        content = _read_ef(ef)
        os.unlink(ef)
        for line in content.splitlines():
            if "from" not in line:
                continue
            parts = line.split()
            from_idx = parts.index("from")
            parent_ref = parts[from_idx + 1]
            assert "," not in parent_ref, (
                f"Expected bare node ID in 'from' reference, got: {parent_ref}"
            )


# ---------------------------------------------------------------------------
# Invalid multiplier arguments
# ---------------------------------------------------------------------------


class TestInvalidMultiplierArgs:
    """Verify that non-positive multipliers are rejected early."""

    def test_negative_level_multiplier_raises(self):
        g = _simple_game()
        with pytest.raises(ValueError, match="level_multiplier must be non-negative"):
            gambit_layout_to_ef(
                g,
                save_to=os.path.join(tempfile.gettempdir(), "bad.ef"),
                level_multiplier=-3,
            )

    def test_negative_sublevel_multiplier_raises(self):
        g = _simple_game()
        with pytest.raises(
            ValueError, match="sublevel_multiplier must be non-negative"
        ):
            gambit_layout_to_ef(
                g,
                save_to=os.path.join(tempfile.gettempdir(), "bad.ef"),
                sublevel_multiplier=-1,
            )

    def test_negative_xshift_multiplier_raises(self):
        g = _simple_game()
        with pytest.raises(
            ValueError, match="xshift_multiplier must be non-negative"
        ):
            gambit_layout_to_ef(
                g,
                save_to=os.path.join(tempfile.gettempdir(), "bad.ef"),
                xshift_multiplier=-5,
            )

    def test_zero_multipliers_accepted(self):
        """Verify that zero multipliers are accepted and do not crash or loop."""
        g = _simple_game()
        path = os.path.join(tempfile.gettempdir(), "zero_mult.ef")
        result = gambit_layout_to_ef(
            g,
            save_to=path,
            level_multiplier=0,
            sublevel_multiplier=0,
            xshift_multiplier=0,
        )
        assert os.path.isfile(result)
        os.unlink(result)

    def test_no_file_created_on_validation_error(self):
        """Ensure no .ef file is written when validation fails."""
        g = _simple_game()
        path = os.path.join(tempfile.gettempdir(), "should_not_exist.ef")
        with pytest.raises(ValueError):
            gambit_layout_to_ef(g, save_to=path, level_multiplier=-1)
        assert not os.path.exists(path)
