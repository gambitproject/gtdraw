"""
The style of a drawing: every option, its default and its check, in one place.

``Style`` is the single statement of the 30 style options. The public functions
(``tikz``, ``pdf``, ...), the style block in a drawing, the command line and the
app all take their option names and defaults from it.

A drawing can carry its own style as a *style block*: lines of the form::

    % gtdraw: <option> <value>

before the drawing's first non-comment line. The value is a JSON value (``1.5``,
``true``, ``"#759138"``, ``[4, 5]``, ``{"1": "#000000"}``) or a bare word, read as a
string (``colorblind``). In a JSON object, a key that is an integer in digits
(``"1"``, ``"-3"``) is read as an ``int``, because player and level keys are ints.
Other readers of the format see comments.
"""

from __future__ import annotations

import dataclasses
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

__all__ = ["Style"]


# ── Checks ───────────────────────────────────────────────────────────────────
#
# A check takes a value and returns it, normalised (a list becomes a tuple, a dict
# is copied), or raises ValueError with a message that does not name the option.


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _number(value: Any) -> Any:
    if not _is_number(value):
        raise ValueError(f"expected a number, got {value!r}")
    return value


def _boolean(value: Any) -> Any:
    if not isinstance(value, bool):
        raise ValueError(f"expected true or false, got {value!r}")
    return value


def _string(value: Any) -> Any:
    if not isinstance(value, str):
        raise ValueError(f"expected a string, got {value!r}")
    return value


def _one_of(*choices: str) -> Callable[[Any], Any]:
    def check(value: Any) -> Any:
        if value not in choices:
            raise ValueError(f"expected one of {', '.join(choices)}, got {value!r}")
        return value

    return check


def _int_key_map(item: Callable[[Any], Any]) -> Callable[[Any], dict]:
    """A check for a dict from int keys (a player or a level) to values passing ``item``."""

    def check(value: Any) -> dict:
        if not isinstance(value, dict):
            raise ValueError(f"expected an object, got {value!r}")
        result = {}
        for key, item_value in value.items():
            if not isinstance(key, int) or isinstance(key, bool):
                raise ValueError(f"expected integer keys, got {key!r}")
            try:
                result[key] = item(item_value)
            except ValueError as e:
                raise ValueError(f"key {key}: {e}") from None
        return result

    return check


def _or(
    first: Callable[[Any], Any], second: Callable[[Any], Any]
) -> Callable[[Any], Any]:
    def check(value: Any) -> Any:
        if isinstance(value, dict):
            return second(value)
        return first(value)

    return check


def _optional(check: Callable[[Any], Any]) -> Callable[[Any], Any]:
    return lambda value: None if value is None else check(value)


def _int_tuple(value: Any) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"expected a list of integers, got {value!r}")
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ValueError(f"expected a list of integers, got {value!r}")
    return tuple(value)


_COLOR_SCHEMES = ("default", "gambit", "distinctipy", "colorblind", "custom")
_FONT_FAMILIES = ("rmfamily", "sffamily", "ttfamily")
_FONT_SIZES = (
    "tiny",
    "scriptsize",
    "footnotesize",
    "small",
    "normalsize",
    "large",
    "Large",
    "LARGE",
    "huge",
    "Huge",
)
_LEGEND_POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")

_CHECKS: dict[str, Callable[[Any], Any]] = {
    "scale_factor": _number,
    "show_grid": _boolean,
    "color_scheme": _one_of(*_COLOR_SCHEMES),
    "edge_thickness": _number,
    "action_label_position": _or(_number, _int_key_map(_number)),
    "font_family": _one_of(*_FONT_FAMILIES),
    "font_bold": _boolean,
    "font_italic": _boolean,
    "font_size": _one_of(*_FONT_SIZES),
    "custom_colors": _optional(_int_key_map(_string)),
    "horizontal": _boolean,
    "mirror": _boolean,
    "legend_position": _one_of(*_LEGEND_POSITIONS),
    "action_label_dist": _number,
    "iset_fill": _boolean,
    "iset_fill_opacity": _number,
    "iset_boundary": _one_of("solid", "dotted", "none"),
    "iset_curved": _boolean,
    "iset_curved_bend": _or(_number, _int_key_map(_number)),
    "iset_curved_bend_by": _one_of("player", "level"),
    "node_size": _number,
    "label_bg": _or(_boolean, _int_key_map(_boolean)),
    "label_bg_color": _string,
    "label_bg_opacity": _number,
    "label_bg_by": _one_of("player", "level"),
    "label_bg_style": _one_of("player_bg", "white_bg"),
    "vary_action_label_positions": _boolean,
    "action_label_position_by": _one_of("player", "level"),
    "vary_action_label_positions_by": _one_of("all", "player", "level"),
    "vary_action_label_positions_choices": _optional(_int_tuple),
}


# ── Style ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class Style:
    """
    The style of a drawing: every option that changes how it looks.

    Every field has a default; ``Style()`` is gtdraw's own look. A value is checked
    when the style is made, and a bad one raises ``ValueError`` that names the
    option. The fields are:

    Size and layout:
        scale_factor: Scale factor for the diagram.
        show_grid: Whether to show helper grid lines.
        horizontal: Grow the tree left to right instead of top down.
        mirror: Mirror the layout left to right.

    Colours:
        color_scheme: ``"default"``, ``"gambit"``, ``"distinctipy"``,
            ``"colorblind"`` or ``"custom"``.
        custom_colors: For ``"custom"``: a dict from player (0 is chance) to a hex
            colour such as ``"#759138"``; or ``None``.
        legend_position: Corner of the player legend: ``"top-left"``,
            ``"top-right"``, ``"bottom-left"`` or ``"bottom-right"``.

    Text:
        font_family: ``"rmfamily"`` (serif), ``"sffamily"`` or ``"ttfamily"``.
        font_bold, font_italic: Bold or italic text.
        font_size: A LaTeX size command: ``"tiny"``, ``"scriptsize"``,
            ``"footnotesize"``, ``"small"``, ``"normalsize"``, ``"large"``,
            ``"Large"``, ``"LARGE"``, ``"huge"`` or ``"Huge"``.

    Edges, nodes and action labels:
        edge_thickness: Thickness of edges, in pt.
        node_size: Size of player nodes, in mm.
        action_label_position: Position of action labels along an edge, 0 to 1:
            one number, or a dict keyed by player or level (see
            ``action_label_position_by``).
        action_label_position_by: ``"player"`` or ``"level"``: what the keys of a
            dict ``action_label_position`` are.
        action_label_dist: Distance of action labels from their edges.
        vary_action_label_positions: Vary label positions with the number of edges.
        vary_action_label_positions_by: ``"all"``, ``"player"`` or ``"level"``.
        vary_action_label_positions_choices: The players or levels it applies to,
            or ``None`` for all.

    Label backgrounds:
        label_bg: ``True`` for every label, or a dict from player or level to
            ``True`` (see ``label_bg_by``).
        label_bg_by: ``"player"`` or ``"level"``.
        label_bg_style: ``"player_bg"`` or ``"white_bg"``.
        label_bg_color: A colour name or ``"#RRGGBB"``.
        label_bg_opacity: Opacity of the background, 0 to 1.

    Information sets:
        iset_fill: Fill information sets with the player's colour.
        iset_fill_opacity: Opacity of the fill, 0 to 1.
        iset_boundary: ``"solid"``, ``"dotted"`` or ``"none"``.
        iset_curved: Draw information sets as curves.
        iset_curved_bend: Bend angle of a curve: one number, or a dict keyed by
            player or level (see ``iset_curved_bend_by``).
        iset_curved_bend_by: ``"player"`` or ``"level"``.

    Ranges (0 to 1, positive) are not checked; the types and the choices are.
    """

    scale_factor: float = 1.0
    show_grid: bool = False
    color_scheme: str = "default"
    edge_thickness: float = 1.0
    action_label_position: float | dict[int, float] = 0.5
    font_family: str = "rmfamily"
    font_bold: bool = False
    font_italic: bool = False
    font_size: str = "normalsize"
    custom_colors: Optional[dict[int, str]] = None
    horizontal: bool = False
    mirror: bool = False
    legend_position: str = "top-left"
    action_label_dist: float = 1.0
    iset_fill: bool = False
    iset_fill_opacity: float = 0.2
    iset_boundary: str = "solid"
    iset_curved: bool = False
    iset_curved_bend: float | dict[int, float] = 10.0
    iset_curved_bend_by: str = "player"
    node_size: float = 1.5
    label_bg: bool | dict[int, bool] = False
    label_bg_color: str = "white"
    label_bg_opacity: float = 0.8
    label_bg_by: str = "player"
    label_bg_style: str = "player_bg"
    vary_action_label_positions: bool = False
    action_label_position_by: str = "player"
    vary_action_label_positions_by: str = "all"
    vary_action_label_positions_choices: Optional[tuple[int, ...]] = None

    def __post_init__(self) -> None:
        for name, check in _CHECKS.items():
            value = getattr(self, name)
            try:
                checked = check(value)
            except ValueError as e:
                raise ValueError(f"{name}: {e}") from None
            object.__setattr__(self, name, checked)

    def replace(self, **options: Any) -> "Style":
        """
        A copy of this style with some options changed.

        Raises:
            TypeError: If an option name is unknown; the message lists the valid names.
            ValueError: If a value is not valid for its option.
        """
        _check_names(options)
        return dataclasses.replace(self, **options)

    @classmethod
    def from_block(cls, lines: str | Iterable[str]) -> "Style":
        """
        Read a style block.

        Args:
            lines: A drawing's text, or its lines. Only the block, which is the
                ``% gtdraw: <option> <value>`` lines before the first non-comment
                line, is read. Options the block does not name keep their defaults.

        Raises:
            ValueError: If a block line is malformed, names an unknown option or
                repeats one, or has a bad value. The message gives the line number
                (counting from 1 in ``lines``).
        """
        return cls(**_read_block(lines))

    def to_block(self, base: Optional["Style"] = None) -> str:
        """
        The style block that gives this style when read onto ``base``.

        Args:
            base: The style the block is read onto: ``Style()`` unless given. Only
                the options that differ from ``base`` are written, one line each,
                so a style equal to ``base`` gives ``""``.

        Returns:
            The ``% gtdraw: <option> <value>`` lines, each ending in a newline.
        """
        base = Style() if base is None else base
        out = []
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if value != getattr(base, field.name):
                out.append(f"% gtdraw: {field.name} {_format_value(value)}\n")
        return "".join(out)


_NAMES = tuple(f.name for f in dataclasses.fields(Style))


def _check_names(options: dict[str, Any]) -> None:
    unknown = [name for name in options if name not in _CHECKS]
    if unknown:
        raise TypeError(
            f"unknown style option{'s' if len(unknown) > 1 else ''} "
            f"{', '.join(repr(n) for n in unknown)}; the options are: "
            f"{', '.join(_NAMES)}"
        )


# ── The block ────────────────────────────────────────────────────────────────

_BLOCK_LINE = re.compile(r"^\s*%\s*gtdraw:(.*)$")
_BARE_WORD = re.compile(r"^[^\s\"'\\{}\[\],:]+$")
_INT_KEY = re.compile(r"^-?[0-9]+$")


def _is_comment_or_blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("%")


def _as_lines(lines: str | Iterable[str]) -> list[str]:
    return lines.splitlines() if isinstance(lines, str) else list(lines)


def _json_keys(value: Any) -> Any:
    """In a JSON object, keys that are integers in digits become ints."""
    if isinstance(value, dict):
        return {
            int(key) if isinstance(key, str) and _INT_KEY.match(key) else key: item
            for key, item in value.items()
        }
    return value


def _parse_value(text: str) -> Any:
    """A JSON value, or else a bare word read as a string."""
    try:
        return _json_keys(json.loads(text))
    except json.JSONDecodeError:
        if _BARE_WORD.match(text):
            return text
        raise ValueError(
            f"cannot read the value {text!r}: use a JSON value, or a bare word "
            "(a string without spaces or quotes)"
        ) from None


def _read_block(lines: str | Iterable[str]) -> dict[str, Any]:
    """The checked ``{option: value}`` of a drawing's style block, in order of appearance."""
    options: dict[str, Any] = {}
    for number, line in enumerate(_as_lines(lines), start=1):
        if not _is_comment_or_blank(line):
            break
        match = _BLOCK_LINE.match(line)
        if match is None:
            continue
        try:
            parts = match.group(1).strip().split(None, 1)
            if not parts:
                raise ValueError("expected '% gtdraw: <option> <value>'")
            name = parts[0]
            _check_names({name: None})
            if len(parts) < 2:
                raise ValueError(f"{name}: no value")
            if name in options:
                raise ValueError(f"{name}: given twice")
            value = _parse_value(parts[1])
            try:
                options[name] = _CHECKS[name](value)
            except ValueError as e:
                raise ValueError(f"{name}: {e}") from None
        except TypeError as e:  # an unknown option name
            raise ValueError(f"line {number}: {e}") from None
        except ValueError as e:
            raise ValueError(f"line {number}: {e}") from None
    return options


def _strip_block(lines: str | Iterable[str]) -> list[str]:
    """The lines without the style block's lines."""
    stripped = []
    in_header = True
    for line in _as_lines(lines):
        if in_header and not _is_comment_or_blank(line):
            in_header = False
        if in_header and _BLOCK_LINE.match(line):
            continue
        stripped.append(line)
    return stripped


def _format_value(value: Any) -> str:
    if isinstance(value, str):
        if _BARE_WORD.match(value) and not _is_json(value):
            return value
        return json.dumps(value)
    return json.dumps(value)


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return False
    return True


def _resolve(
    style: Optional[Style], text: str, options: dict[str, Any]
) -> tuple[Style, list[str]]:
    """
    The style a call draws with, and the drawing's lines without the block.

    Lowest first: ``Style()`` < ``style`` < the drawing's block < ``options``.
    """
    if style is not None and not isinstance(style, Style):
        raise TypeError(
            f"style must be a gtdraw.Style or None, not {type(style).__name__}"
        )
    _check_names(options)
    lines = text.splitlines()
    resolved = (Style() if style is None else style).replace(**_read_block(lines))
    return resolved.replace(**options), _strip_block(lines)
