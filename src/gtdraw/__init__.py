"""
GTDraw - Game tree drawing tool for extensive form games

This package compiles drawings in gtdraw's format (.ef, and the LaTeX body of a
strategic game) to TikZ, LaTeX, PDF, PNG and SVG, with support for Jupyter
notebooks. It reads no game format but its own: to draw a Gambit game, convert it
to a drawing with pygambit first.
"""

from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("gtdraw")  # the version is stated once, in pyproject.toml
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "unknown"

from .core import (
    draw,
    tikz,
    tex,
    pdf,
    png,
    svg,
    latex_wrapper,
)
from .style import Style

__all__ = [
    "draw",
    "tikz",
    "tex",
    "pdf",
    "png",
    "svg",
    "latex_wrapper",
    "Style",
]
