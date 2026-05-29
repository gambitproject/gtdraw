"""
Draw Tree - Game tree drawing tool

This package provides functionality to generate TikZ code for game trees
from extensive form (.ef) files, with support for Jupyter notebooks.
"""

__version__ = "0.10.0"

from .core import (
    draw_tree,
    generate_tikz,
    generate_tex,
    generate_pdf,
    generate_png,
    generate_svg,
    ef_to_tex,
    latex_wrapper,
    count_players,
)

from .gambit_layout import gambit_layout_to_ef

from .converter import ef_to_efg, efg_to_ef

__all__ = [
    "draw_tree",
    "generate_tikz",
    "generate_tex",
    "generate_pdf",
    "generate_png",
    "generate_svg",
    "ef_to_tex",
    "latex_wrapper",
    "gambit_layout_to_ef",
    "count_players",
    "ef_to_efg",
    "efg_to_ef",
]
