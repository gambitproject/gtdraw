"""Tests for ``gtdraw.Style``: the single statement of the options, and the style block."""

import dataclasses
import inspect
import io
import re

import pytest

import gtdraw
from gtdraw import Style
from gtdraw.style import _read_block, _strip_block

# A style with every option set to a value other than its default.
EVERY_OPTION = Style(
    scale_factor=0.65,
    show_grid=True,
    color_scheme="custom",
    edge_thickness=1.6,
    action_label_position={0: 0.3, 2: 0.7},
    font_family="sffamily",
    font_bold=True,
    font_italic=True,
    font_size="Large",
    custom_colors={0: "#759138", 1: "#000000", 2: "#11a1fd"},
    horizontal=True,
    mirror=True,
    legend_position="bottom-right",
    action_label_dist=5.0,
    iset_fill=True,
    iset_fill_opacity=0.5,
    iset_boundary="dotted",
    iset_curved=True,
    iset_curved_bend={-3: 0.0, 21: -20.0},
    iset_curved_bend_by="level",
    node_size=3.1,
    label_bg={0: True, 1: True},
    label_bg_color="#FF8800",
    label_bg_opacity=0.95,
    label_bg_by="level",
    label_bg_style="white_bg",
    vary_action_label_positions=True,
    action_label_position_by="level",
    vary_action_label_positions_by="player",
    vary_action_label_positions_choices=(1, 2),
)

DRAWING = """\
player 1 name I
player 2 name II
level 0 node 1 player 1
level 2 node 1 xshift -1 from 0,1 move L payoffs 1 0
level 2 node 2 xshift 1 from 0,1 move R payoffs 0 1
"""


def treethickn(tikz_code):
    """The edge thickness a drawing was rendered with, from its TikZ text."""
    return re.search(r"\\treethickn([0-9.]+)pt", tikz_code).group(1)


class TestOptions:
    def test_thirty_options(self):
        assert len(dataclasses.fields(Style)) == 30

    def test_every_option_is_non_default_in_the_fixture(self):
        defaults = Style()
        for field in dataclasses.fields(Style):
            assert getattr(EVERY_OPTION, field.name) != getattr(defaults, field.name), (
                field.name
            )

    def test_defaults(self):
        s = Style()
        assert s.color_scheme == "default"
        assert s.scale_factor == 1.0
        assert s.node_size == 1.5
        assert s.iset_curved_bend == 10.0
        assert s.label_bg_opacity == 0.8
        assert s.vary_action_label_positions_choices is None

    def test_no_public_function_restates_an_option(self):
        names = set(f.name for f in dataclasses.fields(Style))
        for func in (
            gtdraw.draw,
            gtdraw.tikz,
            gtdraw.tex,
            gtdraw.pdf,
            gtdraw.png,
            gtdraw.svg,
        ):
            assert not names & set(inspect.signature(func).parameters), func.__name__
        assert sorted(inspect.signature(gtdraw.pdf).parameters) == [
            "format",
            "options",
            "save_to",
            "source",
            "style",
        ]

    def test_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            Style().node_size = 2.0

    def test_keyword_only(self):
        with pytest.raises(TypeError):
            Style(1.0)

    def test_replace(self):
        s = Style().replace(node_size=2.0, color_scheme="gambit")
        assert (s.node_size, s.color_scheme) == (2.0, "gambit")
        assert Style().node_size == 1.5

    def test_replace_unknown_option_lists_the_valid_names(self):
        with pytest.raises(TypeError) as e:
            Style().replace(colour_scheme="gambit")
        message = str(e.value)
        assert "'colour_scheme'" in message
        for field in dataclasses.fields(Style):
            assert field.name in message

    @pytest.mark.parametrize(
        "options, fragment",
        [
            ({"color_scheme": "rainbow"}, "color_scheme"),
            ({"scale_factor": "big"}, "scale_factor"),
            ({"scale_factor": True}, "scale_factor"),
            ({"show_grid": 1}, "show_grid"),
            ({"iset_boundary": "wavy"}, "iset_boundary"),
            ({"legend_position": "middle"}, "legend_position"),
            ({"font_family": "comic"}, "font_family"),
            ({"font_size": "enormous"}, "font_size"),
            ({"action_label_position": {"a": 0.5}}, "action_label_position"),
            ({"custom_colors": {0: 5}}, "custom_colors"),
            ({"label_bg": {0: "yes"}}, "label_bg"),
            ({"vary_action_label_positions_choices": ["a"]}, "vary_action"),
        ],
    )
    def test_a_bad_value_names_its_option(self, options, fragment):
        with pytest.raises(ValueError, match=fragment):
            Style(**options)

    def test_lists_become_tuples_and_dicts_are_copied(self):
        choices = [4, 5]
        bend = {1: 2.0}
        s = Style(vary_action_label_positions_choices=choices, iset_curved_bend=bend)
        assert s.vary_action_label_positions_choices == (4, 5)
        bend[1] = 9.0
        assert s.iset_curved_bend == {1: 2.0}


class TestBlock:
    def test_round_trip_with_every_option_non_default(self):
        block = EVERY_OPTION.to_block()
        assert block.count("% gtdraw:") == 30
        assert Style.from_block(block) == EVERY_OPTION

    def test_round_trip_of_the_defaults(self):
        assert Style().to_block() == ""
        assert Style.from_block("") == Style()

    def test_round_trip_from_lines(self):
        lines = EVERY_OPTION.to_block().splitlines()
        assert Style.from_block(lines) == EVERY_OPTION

    def test_values_are_json_or_bare_words(self):
        s = Style.from_block(
            "% gtdraw: edge_thickness 1.6\n"
            "% gtdraw: font_bold true\n"
            "% gtdraw: color_scheme colorblind\n"
            '% gtdraw: label_bg_color "#FF8800"\n'
            "% gtdraw: vary_action_label_positions_choices [4, 5]\n"
            '% gtdraw: custom_colors {"0": "#759138", "-1": "#000000"}\n'
        )
        assert s.edge_thickness == 1.6
        assert s.font_bold is True
        assert s.color_scheme == "colorblind"
        assert s.label_bg_color == "#FF8800"
        assert s.vary_action_label_positions_choices == (4, 5)
        assert s.custom_colors == {0: "#759138", -1: "#000000"}

    def test_a_bare_word_may_be_a_hex_colour(self):
        assert Style.from_block(
            "% gtdraw: label_bg_color #FF8800\n"
        ).label_bg_color == ("#FF8800")

    def test_a_string_that_reads_as_json_is_written_quoted(self):
        s = Style(label_bg_color="true")
        assert s.to_block() == '% gtdraw: label_bg_color "true"\n'
        assert Style.from_block(s.to_block()) == s

    def test_digit_keys_become_ints(self):
        s = Style.from_block('% gtdraw: iset_curved_bend {"3": 0.0, "-3": 1.5}\n')
        assert s.iset_curved_bend == {3: 0.0, -3: 1.5}

    def test_the_block_is_the_comment_lines_before_the_first_other_line(self):
        text = (
            "% a comment\n"
            "\n"
            "  % gtdraw: node_size 2\n"
            "%gtdraw:  font_bold   true\n"
            "player 1 name I\n"
            "% gtdraw: node_size 9\n"
        )
        s = Style.from_block(text)
        assert s.node_size == 2 and s.font_bold is True

    def test_to_block_writes_what_differs_from_a_base(self):
        base = Style(color_scheme="colorblind", node_size=2.0)
        style = base.replace(color_scheme="default", edge_thickness=3.0)
        block = style.to_block(base)
        assert block == "% gtdraw: color_scheme default\n% gtdraw: edge_thickness 3.0\n"
        assert base.replace(**_read_block(block)) == style

    def test_strip_block(self):
        text = "% keep\n% gtdraw: node_size 2\nplayer 1\n% gtdraw: node_size 3\n"
        assert _strip_block(text) == ["% keep", "player 1", "% gtdraw: node_size 3"]

    @pytest.mark.parametrize(
        "text, line, fragment",
        [
            ("% gtdraw: colour_scheme gambit\n", 1, "colour_scheme"),
            ("% a\n\n% gtdraw: node_size big\n", 3, "node_size"),
            ("% a\n% gtdraw: color_scheme rainbow\n", 2, "color_scheme"),
            ("% gtdraw: node_size\n", 1, "no value"),
            ("% gtdraw:\n", 1, "<option>"),
            ("% gtdraw: label_bg_color two words\n", 1, "cannot read"),
            ("% gtdraw: node_size 1\n% gtdraw: node_size 2\n", 2, "twice"),
            ("%\n%\n% gtdraw: font_bold maybe\n", 3, "font_bold"),
        ],
    )
    def test_errors_carry_the_line_number(self, text, line, fragment):
        with pytest.raises(ValueError) as e:
            Style.from_block(text)
        assert f"line {line}:" in str(e.value)
        assert fragment in str(e.value)

    def test_an_unknown_option_lists_the_valid_names(self):
        with pytest.raises(ValueError) as e:
            Style.from_block("% gtdraw: nope 1\n")
        assert "node_size" in str(e.value)


class TestPrecedence:
    """Lowest first: ``Style()`` < ``style`` < the drawing's block < keyword options."""

    def block(self, thickness):
        return f"% gtdraw: edge_thickness {thickness}\n" + DRAWING

    def test_defaults(self):
        assert treethickn(gtdraw.tikz(io.StringIO(DRAWING))) == "1.0"

    def test_style_beats_the_defaults(self):
        code = gtdraw.tikz(io.StringIO(DRAWING), style=Style(edge_thickness=2.0))
        assert treethickn(code) == "2.0"

    def test_block_beats_style(self):
        code = gtdraw.tikz(io.StringIO(self.block(3)), style=Style(edge_thickness=2.0))
        assert treethickn(code) == "3"

    def test_options_beat_the_block(self):
        code = gtdraw.tikz(
            io.StringIO(self.block(3)),
            style=Style(edge_thickness=2.0),
            edge_thickness=4.0,
        )
        assert treethickn(code) == "4.0"

    def test_options_beat_style(self):
        code = gtdraw.tikz(
            io.StringIO(DRAWING), style=Style(edge_thickness=2.0), edge_thickness=4.0
        )
        assert treethickn(code) == "4.0"

    def test_the_block_sets_only_what_it_names(self):
        code = gtdraw.tikz(io.StringIO(self.block(3)), style=Style(node_size=2.5))
        assert treethickn(code) == "3"
        assert "\\ndiam2.5mm" in code

    def test_the_block_is_not_echoed_into_the_tikz(self):
        code = gtdraw.tikz(io.StringIO(self.block(3)))
        assert "gtdraw:" not in code
        assert gtdraw.tikz(io.StringIO(DRAWING)).replace("1.0pt", "3pt") == code

    def test_a_block_in_a_file(self, tmp_path):
        path = tmp_path / "d.ef"
        path.write_text(self.block(3))
        assert treethickn(gtdraw.tikz(path)) == "3"

    def test_unknown_option_raises_type_error(self):
        with pytest.raises(TypeError, match="colour_scheme"):
            gtdraw.tikz(io.StringIO(DRAWING), colour_scheme="gambit")

    def test_bad_option_value_raises_value_error(self):
        with pytest.raises(ValueError, match="color_scheme"):
            gtdraw.tikz(io.StringIO(DRAWING), color_scheme="rainbow")

    def test_style_must_be_a_style(self):
        with pytest.raises(TypeError, match="Style"):
            gtdraw.tikz(io.StringIO(DRAWING), style={"edge_thickness": 2.0})

    def test_a_bad_block_raises_with_its_line_number(self):
        text = "% a comment\n% gtdraw: node_size big\n" + DRAWING
        with pytest.raises(ValueError, match="line 2:"):
            gtdraw.tikz(io.StringIO(text))

    def test_an_unknown_option_in_the_block_raises_with_its_line_number(self):
        text = "% gtdraw: bogus 1\n" + DRAWING
        with pytest.raises(ValueError, match="line 1:"):
            gtdraw.tikz(io.StringIO(text))


class TestOtherFunctions:
    def test_tex_takes_style_and_options(self, tmp_path):
        out = gtdraw.tex(
            io.StringIO(DRAWING),
            str(tmp_path / "a"),
            style=Style(edge_thickness=2.0),
            node_size=2.5,
        )
        text = open(out).read()
        assert treethickn(text) == "2.0"
        assert "\\ndiam2.5mm" in text

    def test_tex_reads_the_block(self, tmp_path):
        out = gtdraw.tex(
            io.StringIO("% gtdraw: edge_thickness 3\n" + DRAWING), str(tmp_path / "a")
        )
        assert treethickn(open(out).read()) == "3"

    def test_a_bad_style_is_not_hidden_by_the_image_functions(self, tmp_path):
        for func in (gtdraw.pdf, gtdraw.png, gtdraw.svg):
            with pytest.raises(TypeError, match="bogus"):
                func(io.StringIO(DRAWING), str(tmp_path / "a"), bogus=1)
            with pytest.raises(ValueError, match="color_scheme"):
                func(io.StringIO(DRAWING), str(tmp_path / "a"), color_scheme="rainbow")

    def test_draw_takes_style(self):
        code = gtdraw.draw(io.StringIO(DRAWING), style=Style(edge_thickness=2.0)).tikz
        assert treethickn(code) == "2.0"


class TestExampleBlocks:
    """The examples that carry a block: it is what ``gui_settings.yaml`` held for them."""

    @pytest.mark.parametrize("name", ["kuhn-4-card", "kuhn-3-card-v1", "MAS_Fig6_2"])
    def test_blocks_read(self, name):
        from pathlib import Path

        path = Path(__file__).parent.parent / "games" / f"{name}.ef"
        style = Style.from_block(path.read_text())
        assert style != Style()
        assert style.iset_curved is True
        assert style.iset_fill is True
