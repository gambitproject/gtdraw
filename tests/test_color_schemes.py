"""Tests for the color logic in draw_tree.

Covers:
  - get_player_color() dispatch for every scheme
  - color_definitions() LaTeX output for every scheme
  - generate_legend() TikZ output
  - Integration with generate_tikz / generate_tex via color_scheme parameter
"""

import pytest

import draw_tree.core as core
from draw_tree import generate_tikz


# ── get_player_color ──────────────────────────────────────────────────

class TestGetPlayerColorDefault:
    """Default scheme always returns 'black'."""

    def test_chance_player(self):
        assert core.get_player_color(0, "default") == "black"

    def test_regular_player(self):
        assert core.get_player_color(1, "default") == "black"

    def test_high_player_number(self):
        assert core.get_player_color(99, "default") == "black"

    def test_negative_player(self):
        assert core.get_player_color(-1, "default") == "black"


class TestGetPlayerColorGambit:
    """Gambit scheme has a fixed 7-entry palette (0=chance, 1-6=players)."""

    def test_chance_node(self):
        assert core.get_player_color(0, "gambit") == "chancecolor"

    def test_player_one(self):
        assert core.get_player_color(1, "gambit") == "playeronecolor"

    def test_player_two(self):
        assert core.get_player_color(2, "gambit") == "playertwocolor"

    def test_all_six_players(self):
        expected = [
            "playeronecolor", "playertwocolor", "playerthreecolor",
            "playerfourcolor", "playerfivecolor", "playersixcolor",
        ]
        for i, name in enumerate(expected, start=1):
            assert core.get_player_color(i, "gambit") == name

    def test_player_seven_raises(self):
        with pytest.raises(ValueError, match="only supports up to 6 players"):
            core.get_player_color(7, "gambit")

    def test_player_100_raises(self):
        with pytest.raises(ValueError, match="only supports up to 6 players"):
            core.get_player_color(100, "gambit")

    def test_negative_player_returns_black(self):
        assert core.get_player_color(-1, "gambit") == "black"


class TestGetPlayerColorDistinctipy:
    """distinctipy scheme: chance -> chancecolor, players -> p{N}rgb."""

    def test_chance_node(self):
        assert core.get_player_color(0, "distinctipy") == "chancecolor"

    def test_player_one(self):
        assert core.get_player_color(1, "distinctipy") == "p1rgb"

    def test_player_twelve(self):
        assert core.get_player_color(12, "distinctipy") == "p12rgb"

    def test_many_players_no_error(self):
        for i in range(1, 50):
            result = core.get_player_color(i, "distinctipy")
            assert result == f"p{i}rgb"


class TestGetPlayerColorColorblind:
    """colorblind scheme: same naming as distinctipy."""

    def test_chance_node(self):
        assert core.get_player_color(0, "colorblind") == "chancecolor"

    def test_player_one(self):
        assert core.get_player_color(1, "colorblind") == "p1rgb"

    def test_high_player(self):
        assert core.get_player_color(20, "colorblind") == "p20rgb"


# ── color_definitions ─────────────────────────────────────────────────

class TestColorDefinitionsDefault:
    """Default scheme should only define chancecolor."""

    def test_contains_chancecolor(self):
        defs = core.color_definitions("default")
        assert any("chancecolor" in d for d in defs)

    def test_no_player_colors(self):
        defs = core.color_definitions("default")
        assert not any("playeronecolor" in d for d in defs)
        assert not any("p1rgb" in d for d in defs)

    def test_single_definition(self):
        defs = core.color_definitions("default")
        assert len(defs) == 1


class TestColorDefinitionsGambit:
    """Gambit scheme defines chance + 6 named player colors."""

    def test_defines_seven_colors(self):
        defs = core.color_definitions("gambit")
        assert len(defs) == 7

    def test_chancecolor_present(self):
        defs = core.color_definitions("gambit")
        assert any("chancecolor" in d for d in defs)

    def test_playeronecolor_rgb(self):
        defs = core.color_definitions("gambit")
        assert any("playeronecolor" in d and "234,51,35" in d for d in defs)

    def test_playertwocolor_is_blue(self):
        defs = core.color_definitions("gambit")
        assert any("playertwocolor" in d and "blue" in d for d in defs)

    def test_all_six_player_colors_present(self):
        defs = core.color_definitions("gambit")
        combined = "\n".join(defs)
        for name in ["playeronecolor", "playertwocolor", "playerthreecolor",
                      "playerfourcolor", "playerfivecolor", "playersixcolor"]:
            assert name in combined


class TestColorDefinitionsDistinctipy:
    """distinctipy scheme generates N player colors via the distinctipy library."""

    def test_two_players(self):
        defs = core.color_definitions("distinctipy", num_players=2)
        assert any("chancecolor" in d for d in defs)
        assert any("p1rgb" in d for d in defs)
        assert any("p2rgb" in d for d in defs)

    def test_ten_players(self):
        defs = core.color_definitions("distinctipy", num_players=10)
        for i in range(1, 11):
            assert any(f"p{i}rgb" in d for d in defs)

    def test_rgb_format(self):
        defs = core.color_definitions("distinctipy", num_players=2)
        player_defs = [d for d in defs if "p1rgb" in d]
        assert len(player_defs) == 1
        assert "definecolor" in player_defs[0]
        assert "RGB" in player_defs[0]

    def test_deterministic_with_seed(self):
        """Same num_players should produce identical colors (rng=42)."""
        defs1 = core.color_definitions("distinctipy", num_players=4)
        defs2 = core.color_definitions("distinctipy", num_players=4)
        assert defs1 == defs2


class TestColorDefinitionsColorblind:
    """colorblind scheme also uses distinctipy but with Deuteranomaly filter."""

    def test_two_players(self):
        defs = core.color_definitions("colorblind", num_players=2)
        assert any("p1rgb" in d for d in defs)
        assert any("p2rgb" in d for d in defs)

    def test_differs_from_distinctipy(self):
        """colorblind and distinctipy should produce different palettes."""
        defs_d = core.color_definitions("distinctipy", num_players=4)
        defs_c = core.color_definitions("colorblind", num_players=4)
        player_d = [d for d in defs_d if "p1rgb" in d]
        player_c = [d for d in defs_c if "p1rgb" in d]
        assert player_d != player_c


# ── generate_legend ───────────────────────────────────────────────────

class TestGenerateLegend:
    """generate_legend produces TikZ code for a player color legend."""

    def test_empty_player_list(self):
        result = core.generate_legend([], "gambit")
        assert result == ""

    def test_default_scheme_returns_empty(self):
        result = core.generate_legend([1, 2], "default")
        assert result == ""

    def test_gambit_contains_player_colors(self):
        result = core.generate_legend([0, 1, 2], "gambit")
        assert "playeronecolor" in result
        assert "playertwocolor" in result
        assert "chancecolor" in result

    def test_contains_tikz_scope(self):
        result = core.generate_legend([1], "gambit")
        assert "\\begin{scope}" in result
        assert "\\end{scope}" in result

    def test_chance_node_is_rectangle(self):
        result = core.generate_legend([0], "gambit")
        assert "rectangle" in result

    def test_player_node_is_circle(self):
        result = core.generate_legend([1], "gambit")
        assert "circle" in result

    def test_skips_negative_players(self):
        result = core.generate_legend([-1, 1], "gambit")
        assert "playeronecolor" in result
        assert result.count("\\node[inner sep") == 1


# ── Integration with generate_tikz ───────────────────────────────────

class TestColorSchemeIntegration:
    """Verify color_scheme parameter flows through generate_tikz end-to-end."""

    @pytest.fixture
    def ef_file(self):
        return "games/example.ef"

    def test_default_scheme_no_player_color_defs(self, ef_file):
        tikz = generate_tikz(ef_file, color_scheme="default")
        assert "playeronecolor" not in tikz
        assert "p1rgb" not in tikz

    def test_gambit_scheme_defines_player_colors(self, ef_file):
        tikz = generate_tikz(ef_file, color_scheme="gambit")
        assert "playeronecolor" in tikz

    def test_distinctipy_scheme_defines_prgb_colors(self, ef_file):
        tikz = generate_tikz(ef_file, color_scheme="distinctipy")
        assert "p1rgb" in tikz

    def test_colorblind_scheme_defines_prgb_colors(self, ef_file):
        tikz = generate_tikz(ef_file, color_scheme="colorblind")
        assert "p1rgb" in tikz

    def test_all_schemes_produce_valid_tikzpicture(self, ef_file):
        for scheme in ("default", "gambit", "distinctipy", "colorblind"):
            tikz = generate_tikz(ef_file, color_scheme=scheme)
            assert "\\begin{tikzpicture}" in tikz
            assert "\\end{tikzpicture}" in tikz

    def test_chancecolor_present_in_non_default_schemes(self, ef_file):
        for scheme in ("gambit", "distinctipy", "colorblind"):
            tikz = generate_tikz(ef_file, color_scheme=scheme)
            assert "chancecolor" in tikz

    def test_efg_file_with_color_scheme(self):
        tikz = generate_tikz(
            "games/efg/one_card_poker.efg", color_scheme="gambit"
        )
        assert "playeronecolor" in tikz
        assert "tikzpicture" in tikz
