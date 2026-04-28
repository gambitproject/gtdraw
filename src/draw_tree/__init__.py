"""
Draw Tree - Game tree drawing tool

This package provides functionality to generate TikZ code for game trees
from extensive form (.ef) files, with support for Jupyter notebooks.
"""

__version__ = "0.5.1"

from .core import (
    draw_tree,
    generate_tikz,
    generate_tex,
    generate_pdf,
    generate_png,
    generate_svg,
    ef_to_tex,
    latex_wrapper,
)

from .gambit_layout import gambit_layout_to_ef

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
]
