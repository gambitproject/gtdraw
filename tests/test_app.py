"""Tests for the Streamlit app's use of ``Style``. Skipped unless ``gtdraw[gui]`` is installed."""

import warnings
from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

from gtdraw import Style  # noqa: E402

APP = Path(__file__).parent.parent / "src" / "gtdraw" / "app.py"
GAMES = Path(__file__).parent.parent / "games"


@pytest.fixture(scope="module")
def app_module():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import gtdraw.app as app
    return app


class TestStyleHelpers:
    def test_the_base_style_is_the_colour_blind_one(self, app_module):
        assert app_module.BASE_STYLE == Style(color_scheme="colorblind")

    def test_a_drawing_without_a_block_has_the_base_style(self, app_module):
        text = (GAMES / "example.ef").read_text()
        assert app_module._drawing_style(text) == app_module.BASE_STYLE

    def test_a_drawing_with_a_block_has_the_block_on_the_base(self, app_module):
        style = app_module._drawing_style((GAMES / "kuhn-4-card.ef").read_text())
        assert style.color_scheme == "colorblind"
        assert style.node_size == 3.1

    def test_a_download_records_what_differs_from_the_base(self, app_module):
        text = (GAMES / "kuhn-4-card.ef").read_text()
        style = app_module._drawing_style(text).replace(
            node_size=2.0, color_scheme="default"
        )
        out = app_module._drawing_with_block(text, style)
        assert out.count("% gtdraw: node_size") == 1
        assert "% gtdraw: node_size 2.0\n" in out
        assert "% gtdraw: color_scheme default\n" in out
        assert app_module._drawing_style(out) == style
        # the drawing itself is untouched
        assert out.endswith(text[text.index("player 1 name") :])


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    return at


def select(at, name):
    box = at.selectbox[0]
    index = [i for i, o in enumerate(box.options) if f"] {name}" in str(o)][0]
    box.select_index(index)
    at.run()


class TestApp:
    def test_loads_with_the_base_style_in_the_widgets(self, app):
        assert not app.exception
        assert app.session_state["scheme_selector"] == "colorblind"
        assert app.session_state["gui_node_size"] == 1.5

    def test_a_drawings_block_sets_the_widgets(self, app):
        select(app, "kuhn-4-card.ef")
        assert not app.exception
        assert app.session_state["gui_node_size"] == 3.1
        assert app.session_state["gui_font_family"] == "Sans-Serif"
        assert app.session_state["gui_iset_curved"] is True
        assert app.session_state["gui_vary_alp"] is True
        assert app.session_state["gui_vary_alp_by"] == "By Level"

    def test_the_next_drawing_goes_back_to_the_base_style(self, app):
        select(app, "kuhn-4-card.ef")
        select(app, "example.ef")
        assert not app.exception
        assert app.session_state["gui_node_size"] == 1.5
        assert app.session_state["gui_iset_curved"] is False
