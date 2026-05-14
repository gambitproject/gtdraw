"""
converter.py -- Bidirectional EF <-> EFG format conversion.

Provides:
  - ef_to_efg(): Convert a .ef file to Gambit .efg format.
  - efg_to_ef(): Convert a .efg file (or pygambit Game) to .ef format.

The EF parser is self-contained and does not depend on the rendering
pipeline in core.py.
"""

from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    import pygambit


# ---------------------------------------------------------------------------
# Data structures for the in-memory game tree
# ---------------------------------------------------------------------------

@dataclass
class ISet:
    """An information set grouping nodes that share the same actions."""
    id: int
    player: int = 0
    actions: List[str] = field(default_factory=list)
    chance_probs: List[str] = field(default_factory=list)
    node_ids: List[str] = field(default_factory=list)


@dataclass
class Node:
    """A node in the game tree."""
    nodeid: str  # composite id like "2,1"
    level: float = 0.0
    nodenum: str = ""
    player: int = -1
    parent_id: Optional[str] = None
    move: str = ""
    payoffs: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    iset_ref: Optional[ISet] = None


@dataclass
class Game:
    """In-memory representation of an extensive-form game."""
    players: List[str] = field(default_factory=lambda: ["Chance"])
    nodes: dict[str, Node] = field(default_factory=dict)
    isets: List[ISet] = field(default_factory=list)
    root_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# EF file parser
# ---------------------------------------------------------------------------

def _clean_nodeid(s: str) -> str:
    """Normalise a node reference like '2,1' by stripping whitespace."""
    return s.strip().replace(" ", "")


def _parse_move_label(word: str) -> str:
    """
    Extract the move label from a 'move' token.

    EF move syntax is ``move[:pos[:convex]] label``, but the label is the
    *next* word, not part of the keyword token.  This function is only used
    to detect if the token is a 'move' keyword (starts with 'move').
    """
    return word


def parse_ef_file(filepath: str) -> Game:
    """
    Parse an .ef file into a Game object.

    Handles ``player``, ``level``, and ``iset`` lines.  Builds the tree
    structure (parent–child links) and assigns information sets.

    Args:
        filepath: Path to the .ef file.

    Returns:
        A fully-populated Game object.
    """
    game = Game()

    with open(filepath, "r") as f:
        raw_lines = f.read().splitlines()

    # Strip blanks, skip empty/comment lines
    lines: List[str] = []
    for line in raw_lines:
        line = line.strip()
        if line and not line.startswith("%"):
            lines.append(line)

    # --- First pass: player declarations ---
    for line in lines:
        words = line.split()
        if words[0] == "player":
            _parse_player_line(game, words)

    # --- Second pass: level (node) declarations ---
    for line in lines:
        words = line.split()
        if words[0] == "level":
            _parse_level_line(game, words)

    # --- Third pass: iset declarations ---
    for line in lines:
        words = line.split()
        if words[0] == "iset":
            _parse_iset_line(game, words)

    # --- Post-processing ---
    # Build tree structure (parent-child links)
    for nid, node in game.nodes.items():
        if node.parent_id and node.parent_id in game.nodes:
            parent = game.nodes[node.parent_id]
            if nid not in parent.children:
                parent.children.append(nid)

    # Assign information sets to nodes
    _assign_isets(game)

    # Find root (node with no parent)
    for nid, node in game.nodes.items():
        if node.parent_id is None or node.parent_id not in game.nodes:
            game.root_id = nid
            break

    return game


def _parse_player_line(game: Game, words: List[str]) -> None:
    """Parse a ``player N name NAME`` line."""
    try:
        p = int(words[1])
    except (IndexError, ValueError):
        return

    # Ensure players list is big enough
    while len(game.players) <= p:
        game.players.append(str(len(game.players)))

    # Look for 'name' keyword
    i = 2
    while i < len(words):
        if words[i] == "name":
            if i + 1 < len(words):
                game.players[p] = words[i + 1].replace("~", " ")
            break
        i += 1


def _parse_level_line(game: Game, words: List[str]) -> None:
    """
    Parse a ``level L node N [player P] [xshift X] [from L,N] [move M] [payoffs ...]``
    line and create the corresponding Node.
    """
    try:
        lev = float(words[1])
    except (IndexError, ValueError):
        return
    try:
        assert words[2] == "node"
        nodenum = words[3]
    except (IndexError, AssertionError):
        return

    nodeid = _clean_nodeid(f"{int(lev) if lev == int(lev) else lev},{nodenum}")
    node = Node(nodeid=nodeid, level=lev, nodenum=nodenum)

    i = 4
    while i < len(words):
        if words[i] == "player":
            try:
                node.player = int(words[i + 1])
                i += 2
            except (IndexError, ValueError):
                i += 1
        elif words[i] == "xshift":
            # Skip the xshift value (not needed for EFG conversion)
            i += 2
        elif words[i] == "from":
            try:
                node.parent_id = _clean_nodeid(words[i + 1])
                i += 2
            except IndexError:
                i += 1
        elif words[i][:4] == "move":
            # Parse move[:pos[:convex]] label
            if i + 1 < len(words) and words[i + 1] != "payoffs":
                move_label = words[i + 1]
                # Handle chance probability notation: "label~(prob)" or "label~prob"
                node.move = move_label
                i += 2
            else:
                i += 1
        elif words[i] == "payoffs":
            node.payoffs = list(words[i + 1:])
            break
        else:
            i += 1

    game.nodes[nodeid] = node


def _parse_iset_line(game: Game, words: List[str]) -> None:
    """Parse an ``iset L1,N1 L2,N2 ... player P`` line."""
    p = -1
    node_ids: List[str] = []

    i = 1
    while i < len(words):
        if words[i] == "player":
            try:
                p = int(words[i + 1])
                i += 2
            except (IndexError, ValueError):
                i += 1
        else:
            node_ids.append(_clean_nodeid(words[i]))
            i += 1

    if node_ids and p >= 0:
        iset = ISet(
            id=len(game.isets) + 1,
            player=p,
            node_ids=list(node_ids),
        )
        game.isets.append(iset)


def _assign_isets(game: Game) -> None:
    """
    Assign information sets to nodes.  For nodes in explicit iset groups,
    collect their actions (child move labels) and assign the same ISet to
    each member.  For standalone decision nodes (those with a player but
    not in any explicit iset), create a singleton ISet.
    """
    # Track which nodes are already covered by explicit isets
    covered: set[str] = set()

    next_iset_id = 1

    # Process explicit iset declarations
    for iset in game.isets:
        iset.id = next_iset_id
        next_iset_id += 1

        # Collect actions from the first node in the iset that has children
        for nid in iset.node_ids:
            if nid in game.nodes:
                node = game.nodes[nid]
                # Set the player on the node if not already set
                if node.player < 0:
                    node.player = iset.player

                # Collect child move labels as actions
                if not iset.actions:
                    _collect_actions_from_children(
                        node, game, iset, is_chance=(iset.player == 0)
                    )

                node.iset_ref = iset
                covered.add(nid)

    # Create singleton isets for standalone decision/chance nodes
    for nid, node in game.nodes.items():
        if nid in covered:
            continue
        if node.player < 0:
            continue  # terminal or unassigned
        if not node.children:
            continue  # terminal node

        iset = ISet(
            id=next_iset_id,
            player=node.player,
            node_ids=[nid],
        )
        next_iset_id += 1

        _collect_actions_from_children(
            node, game, iset, is_chance=(node.player == 0)
        )

        node.iset_ref = iset
        game.isets.append(iset)


def _collect_actions_from_children(
    node: Node, game: Game, iset: ISet, is_chance: bool
) -> None:
    """
    Populate ``iset.actions`` (and ``iset.chance_probs`` for chance nodes)
    from the move labels of *node*'s children.
    """
    for child_id in node.children:
        if child_id not in game.nodes:
            continue
        child = game.nodes[child_id]
        action = _extract_action_label(child.move)
        iset.actions.append(action)
        if is_chance:
            prob = _extract_chance_prob(child.move)
            iset.chance_probs.append(prob)


def _extract_action_label(move: str) -> str:
    """
    Extract the action label from a move string.

    Handles two annotation styles:

    1. **Tilde-separated** (generated by ``gambit_layout_to_ef``):
       ``H~(\\frac{1}{2})`` → ``H``
    2. **Raw label** (hand-written EF):
       ``\\frac{1}{3}`` → ``\\frac{1}{3}``
    """
    if not move:
        return ""
    # Split off chance probability annotation (tilde form)
    parts = move.split("~", 1)
    return parts[0]


def _extract_chance_prob(move: str) -> str:
    r"""
    Extract chance probability from a move string.

    Handles three cases:

    1. **Tilde-annotated** (generated EF): ``L~(\frac{1}{2})`` → ``1/2``
    2. **Label IS a probability** (raw EF): ``\frac{1}{3}`` → ``1/3``
    3. **Plain numeric label**: ``0.5`` → ``0.5``

    Falls back to ``1`` only if the label is clearly non-numeric and has
    no tilde annotation.
    """
    if not move:
        return "1"

    frac_re = re.compile(r"^\\frac\{(-?\d+)\}\{(-?\d+)\}$")

    # Case 1: tilde-annotated probability
    if "~" in move:
        parts = move.split("~", 1)
        prob_str = parts[1].strip().strip("()")
        m = frac_re.match(prob_str)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
        return prob_str

    # Case 2: the entire label is a LaTeX fraction
    m = frac_re.match(move)
    if m:
        return f"{m.group(1)}/{m.group(2)}"

    # Case 3: the label is a plain number or ratio
    if _INT_RE.match(move) or _DEC_RE.match(move) or _RATIO_RE.match(move):
        return move

    # Not a recognisable probability — default to 1
    return "1"


def preorder(game: Game) -> List[str]:
    """
    Return node IDs in pre-order traversal (parent before children).

    Args:
        game: The Game object.

    Returns:
        List of node IDs in pre-order.
    """
    if game.root_id is None:
        return list(game.nodes.keys())

    result: List[str] = []

    def _visit(nid: str) -> None:
        result.append(nid)
        node = game.nodes[nid]
        for child_id in node.children:
            if child_id in game.nodes:
                _visit(child_id)

    _visit(game.root_id)

    # Include any orphaned nodes not reached from root
    for nid in game.nodes:
        if nid not in result:
            result.append(nid)

    return result


# ---------------------------------------------------------------------------
# EFG writer (adapted from efg_writer.py)
# ---------------------------------------------------------------------------

_FRAC_RE = re.compile(r"^(-?)\\frac\{(-?\d+)\}\{(-?\d+)\}$")
_RATIO_RE = re.compile(r"^(-?\d+)/(-?\d+)$")
_INT_RE = re.compile(r"^-?\d+$")
_DEC_RE = re.compile(r"^-?\d+\.\d*$|^-?\.\d+$|^-?\d+\.\d*[eE]-?\d+$")


def _parse_payoff(s: str) -> Optional[str]:
    """
    Interpret a payoff string as an EFG-acceptable number.

    Returns the normalized form (e.g. ``\\frac{1}{2}`` → ``1/2``) or
    None if *s* is not numeric.
    """
    if s is None or s == "":
        return None
    s = s.strip()
    m = _FRAC_RE.match(s)
    if m:
        sign, a, b = m.group(1), m.group(2), m.group(3)
        return "%s%s/%s" % (sign, a, b)
    if _RATIO_RE.match(s):
        return s
    if _INT_RE.match(s):
        return s
    if _DEC_RE.match(s):
        return s
    return None


def _encoded_symbolic(s: str) -> str:
    """
    Encode a non-numeric payoff as 9900 + ord(first_char).

    Used as a workaround when EFG format requires numeric payoffs but the
    EF source contains a symbolic value.  The resulting integer is far
    above any plausible real payoff so it stands out as synthetic.
    """
    if not s:
        return "9900"
    return str(9900 + ord(s[0]))


def _normalize_payoffs(game: Game) -> None:
    """
    Validate and normalize every terminal's payoff list in place.

    Numeric payoffs are kept (with ``\\frac{a}{b}`` → ``a/b``);
    non-numeric ones are replaced with the 9900+ord encoding and a
    warning is appended to ``game.warnings``.
    """
    for nid, n in game.nodes.items():
        if not n.payoffs:
            continue
        new = []
        for s in n.payoffs:
            norm = _parse_payoff(s)
            if norm is not None:
                new.append(norm)
            else:
                enc = _encoded_symbolic(s)
                new.append(enc)
                game.warnings.append(
                    "node '%s': non-numeric payoff %r encoded as %s "
                    "(EFG requires numeric payoffs)" % (nid, s, enc)
                )
        n.payoffs = new


def _q(s: Optional[str]) -> str:
    """Quote a string for EFG output."""
    if s is None:
        s = ""
    return '"' + s.replace('"', '\\"') + '"'


def _negate_payoff(s: str) -> str:
    """Return the string negation of a payoff value."""
    s = s.strip()
    if s == "0" or s == "0.0":
        return "0"
    if s.startswith("-"):
        return s[1:]
    return "-" + s


def _resolve_player_count(game: Game) -> tuple[int, bool]:
    """
    Determine how many personal players to declare in the EFG prologue.

    Returns (n_players, zero_sum_expand) where zero_sum_expand is True
    iff each terminal's single payoff should be doubled to (v, -v).
    """
    n_mentioned = 0
    for n in game.nodes.values():
        if n.player > n_mentioned:
            n_mentioned = n.player
    for iset in game.isets:
        if iset.player > n_mentioned:
            n_mentioned = iset.player
    for i in range(1, len(game.players)):
        nm = game.players[i]
        if nm and nm != str(i):
            if i > n_mentioned:
                n_mentioned = i

    payoff_lengths: set[int] = set()
    for n in game.nodes.values():
        if n.payoffs:
            payoff_lengths.add(len(n.payoffs))
    if len(payoff_lengths) > 1:
        game.errors.append(
            "inconsistent payoff list lengths across terminals: %s"
            % sorted(payoff_lengths)
        )
    n_payoffs = max(payoff_lengths) if payoff_lengths else 0

    zero_sum_expand = False
    if n_payoffs == 1 and n_mentioned >= 2:
        if n_mentioned == 2:
            zero_sum_expand = True
        else:
            game.errors.append(
                "single-payoff zero-sum form requires exactly 2 players, "
                "but %d players are mentioned" % n_mentioned
            )

    if zero_sum_expand:
        n_players = 2
    else:
        n_players = max(n_mentioned, n_payoffs)
        if n_mentioned > n_payoffs and n_payoffs > 0:
            game.errors.append(
                "%d players are mentioned but terminals carry only %d payoffs"
                % (n_mentioned, n_payoffs)
            )

    if n_players < 1:
        n_players = 1

    return n_players, zero_sum_expand


def _player_label(game: Game, p: int) -> str:
    """Player label for the prologue; falls back to str(p) if empty."""
    name = game.players[p] if 0 <= p < len(game.players) else None
    if not name:
        return str(p)
    return name


def _outcome_tail(
    n: Node, outcome_num: int, n_players: int, zero_sum_expand: bool
) -> str:
    """Build the trailing outcome part of any EFG node line."""
    if outcome_num == 0:
        return "0"
    payoffs = list(n.payoffs)
    if zero_sum_expand and len(payoffs) == 1:
        payoffs.append(_negate_payoff(payoffs[0]))
    while len(payoffs) < n_players:
        payoffs.append("0")
    payoffs = payoffs[:n_players]
    return '%d %s { %s }' % (outcome_num, _q(""), " ".join(payoffs))


def _node_line(
    n: Node,
    game: Game,
    outcome_num: int,
    emitted_iset: set[int],
    n_players: int,
    zero_sum_expand: bool,
) -> str:
    """Format one line of EFG body for node n."""
    iset = n.iset_ref

    # Terminal nodes
    if iset is None:
        return "t %s %s" % (
            _q(n.nodeid),
            _outcome_tail(n, outcome_num, n_players, zero_sum_expand),
        )

    first = id(iset) not in emitted_iset

    if iset.player == 0:
        # Chance node
        head = "c %s %d" % (_q(n.nodeid), iset.id)
        if first:
            actions = " ".join(
                "%s %s" % (_q(a), p)
                for a, p in zip(iset.actions, iset.chance_probs)
            )
            head += " %s { %s }" % (_q(""), actions)
            emitted_iset.add(id(iset))
        return "%s %s" % (
            head,
            _outcome_tail(n, outcome_num, n_players, zero_sum_expand),
        )

    # Personal node
    head = "p %s %d %d" % (_q(n.nodeid), iset.player, iset.id)
    if first:
        actions = " ".join(_q(a) for a in iset.actions)
        head += " %s { %s }" % (_q(""), actions)
        emitted_iset.add(id(iset))
    return "%s %s" % (
        head,
        _outcome_tail(n, outcome_num, n_players, zero_sum_expand),
    )


def _write_efg(game: Game, title: str = "") -> str:
    """
    Emit the Game as EFG text.

    Returns the complete EFG file content as a string.
    """
    buf = io.StringIO()

    _normalize_payoffs(game)

    n_players, zero_sum_expand = _resolve_player_count(game)
    plist = " ".join(
        _q(_player_label(game, p)) for p in range(1, n_players + 1)
    )
    buf.write("EFG 2 R %s { %s }\n" % (_q(title), plist))

    # Outcome numbering
    outcome_of: dict[str, int] = {}
    next_outcome = 1
    for nid in preorder(game):
        if game.nodes[nid].payoffs:
            outcome_of[nid] = next_outcome
            next_outcome += 1
        else:
            outcome_of[nid] = 0

    emitted_iset: set[int] = set()

    for nid in preorder(game):
        n = game.nodes[nid]
        line = _node_line(
            n, game, outcome_of[nid], emitted_iset, n_players, zero_sum_expand
        )
        buf.write(line + "\n")

    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ef_to_efg(
    game: str,
    save_to: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """
    Convert an EF file to Gambit EFG format.

    Args:
        game: Path to the ``.ef`` file.
        save_to: Output filename.  If not provided, derived from the
            input filename with a ``.efg`` extension.
        title: Title string for the EFG prologue.  Defaults to the
            input filename stem.

    Returns:
        Path to the generated ``.efg`` file.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
        ValueError: If the EF file contains errors that prevent conversion.
    """
    if not os.path.isfile(game):
        raise FileNotFoundError(f"EF file not found: {game}")

    parsed = parse_ef_file(game)

    if title is None:
        title = os.path.splitext(os.path.basename(game))[0]

    efg_text = _write_efg(parsed, title=title)

    if parsed.errors:
        raise ValueError(
            "Errors during EF → EFG conversion:\n"
            + "\n".join("  " + e for e in parsed.errors)
        )

    # Determine output path
    if save_to:
        out_path = save_to
        if not out_path.endswith(".efg"):
            out_path += ".efg"
    else:
        out_path = os.path.splitext(game)[0] + ".efg"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(efg_text)

    return out_path


def efg_to_ef(
    game: "str | pygambit.gambit.Game",
    save_to: Optional[str] = None,
    level_scaling: float = 1.0,
    sublevel_scaling: float = 1.0,
    width_scaling: float = 1.0,
    shared_terminal_depth: bool = False,
) -> str:
    """
    Convert a Gambit EFG file or pygambit Game to EF format.

    Uses the existing ``gambit_layout_to_ef()`` function to perform the
    layout conversion.

    Args:
        game: Path to the ``.efg`` file, or a ``pygambit.gambit.Game`` object.
        save_to: Output filename.  If not provided, derived from the game
            title or input filename.
        level_scaling: Level spacing multiplier (default: 1.0).
        sublevel_scaling: Sublevel spacing multiplier (default: 1.0).
        width_scaling: Width spacing multiplier (default: 1.0).
        shared_terminal_depth: Enforce shared terminal node depth
            (default: False).

    Returns:
        Path to the generated ``.ef`` file.

    Raises:
        FileNotFoundError: If the input ``.efg`` file doesn't exist.
        ImportError: If pygambit is not installed.
    """
    import pygambit

    if isinstance(game, str):
        if not os.path.isfile(game):
            raise FileNotFoundError(f"EFG file not found: {game}")
        game_obj = pygambit.read_efg(game)
    else:
        game_obj = game

    from .gambit_layout import gambit_layout_to_ef

    return gambit_layout_to_ef(
        game_obj,
        save_to=save_to,
        level_multiplier=level_scaling * 4,
        sublevel_multiplier=sublevel_scaling * 2,
        xshift_multiplier=width_scaling * 2,
        shared_terminal_depth=shared_terminal_depth,
    )
