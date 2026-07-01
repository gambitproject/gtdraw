"""Helpers for editing GTDraw EF layouts from the GUI.

The Streamlit GUI needs a layout layer that can move nodes without changing
the underlying game.  EF layout is encoded by each node's ``level`` and
parent-relative ``xshift``; information sets refer to node ids and therefore
survive layout rewrites as long as those ids remain stable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


_EPS = 1e-9


@dataclass
class EditableNode:
    """One EF node with absolute layout coordinates."""

    id: str
    label: str
    level: float
    x: float
    y: float
    parent_id: Optional[str] = None
    player: int = -1
    move: str = ""
    payoffs: list[str] = field(default_factory=list)
    terminal: bool = False


@dataclass
class EditableISet:
    """Information set membership for the layout editor component."""

    id: int
    node_ids: list[str]
    player: int = -1


@dataclass
class _LineEntry:
    raw: str
    words: list[str]
    kind: str = "raw"
    node_id: Optional[str] = None


@dataclass
class EditableLayout:
    """Parsed EF layout plus enough source metadata to rewrite it."""

    nodes: list[EditableNode]
    isets: list[EditableISet]
    entries: list[_LineEntry] = field(default_factory=list)
    version: int = 1
    id_map: dict[str, str] = field(default_factory=dict)
    player_names: dict[int, str] = field(default_factory=dict)

    @property
    def node_map(self) -> dict[str, EditableNode]:
        return {node.id: node for node in self.nodes}

    def to_component_payload(
        self, player_colors: Optional[dict[int | str, str]] = None
    ) -> dict[str, Any]:
        """Return JSON-serialisable data for the Streamlit component."""
        node_map = self.node_map
        colors = {int(k): v for k, v in (player_colors or {}).items()}

        def color_for(player: int) -> str:
            return colors.get(player, "#000000" if player >= 0 else "#ffffff")

        def player_label(player: int) -> str:
            if player in self.player_names:
                return self.player_names[player]
            return "Chance" if player == 0 else str(player)

        legend_players = sorted(
            {node.player for node in self.nodes if node.player >= 0}
        )

        return {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "x": node.x,
                    "y": node.y,
                    "player": node.player,
                    "terminal": node.terminal,
                    "color": color_for(node.player),
                    "payoffs": [
                        {
                            "text": payoff,
                            "color": color_for(idx + 1),
                        }
                        for idx, payoff in enumerate(node.payoffs)
                    ],
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "parent": node.parent_id,
                    "child": node.id,
                    "label": node.move,
                    "color": color_for(node_map[node.parent_id].player),
                }
                for node in self.nodes
                if node.parent_id in node_map
            ],
            "isets": [
                {
                    "id": iset.id,
                    "node_ids": iset.node_ids,
                    "player": iset.player,
                    "color": color_for(iset.player),
                }
                for iset in self.isets
            ],
            "legend": [
                {
                    "player": player,
                    "label": player_label(player),
                    "color": color_for(player),
                    "shape": "square" if player == 0 else "circle",
                }
                for player in legend_players
            ],
        }


def _fmt(num: float) -> str:
    """Format EF numeric values compactly while avoiding negative zero."""
    if abs(num) < _EPS:
        num = 0.0
    text = f"{num:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def _clean_legacy_ref(ref: str) -> str:
    """Normalise an EF0 ``level,node`` reference."""
    text = ref.strip().replace(" ", "")
    if "," not in text:
        return text
    level, node = text.split(",", 1)
    try:
        return f"{_fmt(float(level))},{node}"
    except ValueError:
        return text


def _detect_ef_version_from_entries(entries: list[_LineEntry]) -> int:
    for entry in entries:
        words = entry.words
        if len(words) >= 4 and words[0] == "level" and "from" in words:
            idx = words.index("from")
            if idx + 1 < len(words) and "," in words[idx + 1]:
                return 0
    return 1


def _split_num_text(text: str) -> tuple[float, str]:
    nodotyet = True
    tonum = ""
    remainder = ""
    for idx, char in enumerate(text):
        if nodotyet and char == ".":
            nodotyet = False
            tonum += char
        elif char.isdigit():
            tonum += char
        else:
            remainder = text[idx:]
            break
    if tonum and tonum != ".":
        return float(tonum), remainder
    return 1.0, remainder


def _parse_xshift_value(value: str, xshifts: dict[str, float]) -> float:
    """Parse GTDraw's xshift syntax, including named assignments."""
    text = value.strip()
    if not text:
        return 0.0

    neg = text.startswith("-")
    if neg:
        text = text[1:]

    parts = text.split("=", 1)
    if len(parts) == 2:
        coeff, name = _split_num_text(parts[0])
        num = float(parts[1])
        if name:
            xshifts[name] = num
        value_num = coeff * num
    else:
        coeff, name = _split_num_text(parts[0])
        if name:
            if name not in xshifts:
                raise ValueError(f"xshift '{name}' undefined")
            value_num = coeff * xshifts[name]
        else:
            value_num = coeff

    return -value_num if neg else value_num


def _node_ref(words: list[str], version: int) -> str:
    level = float(words[1])
    node_name = words[3]
    if version == 1:
        return node_name.strip()
    return _clean_legacy_ref(f"{_fmt(level)},{node_name}")


def _find_token(words: list[str], token: str) -> Optional[int]:
    try:
        return words.index(token)
    except ValueError:
        return None


def _ensure_unique(prefix: str, used: set[str]) -> str:
    idx = 1
    while f"{prefix}{idx}" in used:
        idx += 1
    value = f"{prefix}{idx}"
    used.add(value)
    return value


def parse_ef_layout(ef_text: str, normalize_ef0: bool = True) -> EditableLayout:
    """Parse EF text into absolute node coordinates and information sets."""
    entries: list[_LineEntry] = []
    for raw in ef_text.splitlines():
        stripped = raw.strip()
        words = stripped.split() if stripped and not stripped.startswith("%") else []
        kind = words[0] if words else "raw"
        if kind not in {"player", "level", "iset"}:
            kind = "raw"
        entries.append(_LineEntry(raw=raw, words=words, kind=kind))

    version = _detect_ef_version_from_entries(entries)
    id_map: dict[str, str] = {}
    used_ids: set[str] = set()
    player_names: dict[int, str] = {0: "Chance"}

    for entry in entries:
        if (
            entry.kind == "player"
            and len(entry.words) >= 4
            and entry.words[2] == "name"
        ):
            try:
                player_names[int(entry.words[1])] = entry.words[3]
            except ValueError:
                pass

    for entry in entries:
        if entry.kind != "level" or len(entry.words) < 4:
            continue
        old_ref = _node_ref(entry.words, version)
        if version == 0 and normalize_ef0:
            new_ref = _ensure_unique("n", used_ids)
        else:
            new_ref = old_ref
            used_ids.add(new_ref)
        entry.node_id = new_ref
        id_map[old_ref] = new_ref

    xshifts: dict[str, float] = {}
    nodes: list[EditableNode] = []
    node_map: dict[str, EditableNode] = {}

    for entry in entries:
        if entry.kind != "level" or len(entry.words) < 4 or not entry.node_id:
            continue

        words = entry.words
        level = float(words[1])
        player = -1
        player_idx = _find_token(words, "player")
        if player_idx is not None and player_idx + 1 < len(words):
            try:
                player = int(words[player_idx + 1])
            except ValueError:
                player = -1

        xshift_value = 0.0
        xshift_idx = _find_token(words, "xshift")
        if xshift_idx is not None and xshift_idx + 1 < len(words):
            xshift_value = _parse_xshift_value(words[xshift_idx + 1], xshifts)

        parent_id = None
        from_idx = _find_token(words, "from")
        if from_idx is not None and from_idx + 1 < len(words):
            old_parent = (
                _clean_legacy_ref(words[from_idx + 1])
                if version == 0
                else words[from_idx + 1].strip()
            )
            parent_id = id_map.get(old_parent, old_parent)

        parent = node_map.get(parent_id or "")
        x = (parent.x if parent else 0.0) + xshift_value
        y = -level

        move = ""
        for idx, token in enumerate(words):
            if token.startswith("move") and idx + 1 < len(words):
                move = words[idx + 1]
                break
        payoffs: list[str] = []
        payoffs_idx = _find_token(words, "payoffs")
        if payoffs_idx is not None:
            payoffs = words[payoffs_idx + 1 :]

        node = EditableNode(
            id=entry.node_id,
            label=words[3],
            level=level,
            x=x,
            y=y,
            parent_id=parent_id,
            player=player,
            move=move,
            payoffs=payoffs,
            terminal=payoffs_idx is not None,
        )
        nodes.append(node)
        node_map[node.id] = node

    isets: list[EditableISet] = []
    for entry in entries:
        if entry.kind != "iset":
            continue

        node_ids: list[str] = []
        player = -1
        count = 1
        while count < len(entry.words):
            word = entry.words[count]
            if word == "player":
                if count + 1 < len(entry.words):
                    try:
                        player = int(entry.words[count + 1])
                    except ValueError:
                        player = -1
                break
            old_ref = _clean_legacy_ref(word) if version == 0 else word.strip()
            node_ids.append(id_map.get(old_ref, old_ref))
            count += 1

        iset = EditableISet(id=len(isets) + 1, node_ids=node_ids, player=player)
        isets.append(iset)
        if player >= 0:
            for node_id in node_ids:
                node = node_map.get(node_id)
                if node and node.player < 0:
                    node.player = player

    return EditableLayout(
        nodes=nodes,
        isets=isets,
        entries=entries,
        version=version,
        id_map=id_map,
        player_names=player_names,
    )


def _remove_pair(words: list[str], token: str) -> None:
    idx = _find_token(words, token)
    if idx is not None:
        del words[idx : min(idx + 2, len(words))]


def _set_pair(words: list[str], token: str, value: str) -> None:
    idx = _find_token(words, token)
    if idx is not None:
        if idx + 1 < len(words):
            words[idx + 1] = value
        else:
            words.append(value)
        return

    insert_at = len(words)
    for marker in ("from", "move", "payoffs", "arrow"):
        marker_idx = _find_token(words, marker)
        if marker_idx is not None:
            insert_at = marker_idx
            break
    words[insert_at:insert_at] = [token, value]


def apply_layout_positions(
    ef_text: str,
    positions: dict[str, Any],
) -> str:
    """Return EF text with node ``level`` and ``xshift`` updated.

    ``positions`` maps node id to either ``{"x": number, "y": number}`` or a
    two-item ``(x, y)`` sequence.  The coordinates use GTDraw's canonical
    layout coordinate system where ``level == -y``.
    """
    layout = parse_ef_layout(ef_text)
    original_nodes = layout.node_map

    next_xy: dict[str, tuple[float, float]] = {}
    for node in layout.nodes:
        payload = positions.get(node.id)
        if isinstance(payload, dict):
            x = float(payload.get("x", node.x))
            y = float(payload.get("y", node.y))
        elif payload is not None:
            x = float(payload[0])
            y = float(payload[1])
        else:
            x, y = node.x, node.y
        next_xy[node.id] = (x, y)

    lines: list[str] = []
    for entry in layout.entries:
        if entry.kind == "level" and entry.node_id:
            words = list(entry.words)
            node = original_nodes[entry.node_id]
            x, y = next_xy[entry.node_id]
            level = -y
            words[1] = _fmt(level)
            words[3] = entry.node_id

            if node.parent_id and node.parent_id in next_xy:
                parent_x = next_xy[node.parent_id][0]
                _set_pair(words, "from", node.parent_id)
                _set_pair(words, "xshift", _fmt(x - parent_x))
            else:
                _remove_pair(words, "from")
                if abs(x) > _EPS:
                    _set_pair(words, "xshift", _fmt(x))
                else:
                    _remove_pair(words, "xshift")

            lines.append(" ".join(words))
        elif entry.kind == "iset":
            words = ["iset"]
            count = 1
            while count < len(entry.words):
                word = entry.words[count]
                if word == "player":
                    words.extend(entry.words[count:])
                    break
                old_ref = (
                    _clean_legacy_ref(word) if layout.version == 0 else word.strip()
                )
                words.append(layout.id_map.get(old_ref, old_ref))
                count += 1
            lines.append(" ".join(words))
        elif entry.kind == "player":
            lines.append(" ".join(entry.words))
        else:
            lines.append(entry.raw)

    return "\n".join(lines).rstrip() + "\n"


def normalise_layout_ef(ef_text: str) -> str:
    """Return EF1-style text suitable for drag editing."""
    return apply_layout_positions(ef_text, {})


def positions_changed(
    layout: EditableLayout,
    positions: dict[str, Any],
    eps: float = 1e-6,
) -> bool:
    """Return True if a component payload differs from the parsed layout."""
    for node in layout.nodes:
        payload = positions.get(node.id)
        if not isinstance(payload, dict):
            continue
        if abs(float(payload.get("x", node.x)) - node.x) > eps:
            return True
        if abs(float(payload.get("y", node.y)) - node.y) > eps:
            return True
    return False


def render_layout_editor(
    layout: EditableLayout,
    key: str,
    player_colors: Optional[dict[int | str, str]] = None,
    height: int = 520,
) -> Optional[dict[str, Any]]:
    """Render the Streamlit drag component and return its latest value."""
    import streamlit.components.v1 as components

    component_dir = Path(__file__).parent / "components" / "layout_editor"
    component = components.declare_component(
        "gtdraw_layout_editor",
        path=str(component_dir),
    )
    return component(
        layout=layout.to_component_payload(player_colors=player_colors),
        height=height,
        default=None,
        key=key,
    )
