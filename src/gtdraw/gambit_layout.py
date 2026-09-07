import pygambit
from typing import Optional


def _is_history(node) -> bool:
    """Whether `node` is a root-anchored `History` tuple of action labels
    (newest pygambit, once `Node`/`Game.root` are no longer public), rather
    than a `Node` object (older pygambit)."""
    return isinstance(node, tuple)


def _selector(history: tuple) -> pygambit.gambit.Selector:
    """The `pygambit.H` Selector resolving to exactly the node `history`
    (a root-anchored tuple of action labels) identifies."""
    return pygambit.H.path(*history)


def _partition(node, game):
    """Return a value identifying the information set or event `node` currently
    belongs to, whichever applies, or a falsy value if neither does. Two nodes in
    the same information set/event return equal values; the value itself carries
    no other meaning.

    Works across four pygambit APIs: oldest, `Node.infoset` alone covers both
    personal information sets and chance events; post-Infoset/Event-split, chance
    nodes need `Node.event` instead; after that split was itself removed, a
    node's partition was identified instead by its own `Node.members` (identical,
    in content and order, for every node sharing a partition -- and raising
    `AttributeError` for a terminal node, matching the falsy behaviour of the
    older `Node.infoset`/`Node.event`); now that `Node` itself is no longer
    public and `node` is a root-anchored `History` tuple, the equivalent is
    `Game.get_members`, which returns `[]` (not an exception) for a terminal
    node.
    """
    if _is_history(node):
        members = game.get_members(_selector(node))
        return tuple(members) if members else None
    try:
        return node.infoset or node.event
    except AttributeError:
        pass
    try:
        return node.infoset
    except AttributeError:
        pass
    try:
        return tuple(node.members)
    except AttributeError:
        return None


def _prior_action_prob(node, game):
    """Return the probability of the chance action leading to `node`.

    Works across pygambit's pre- and post-Action-removal APIs: before the
    removal, `Node.prior_action` is an `Action` with a `.prob` property; after
    it, `Node.prior_action` no longer carries probability information, and it
    must be read via the parent's `Node.action_probs` instead; now that `Node`
    is no longer public and `node` is a `History` tuple, the equivalent is
    `Game.get_action_probs` on the parent's own `History` (`node[:-1]`), keyed
    by `node`'s own last action label (`node[-1]`).
    """
    if _is_history(node):
        return game.get_action_probs(_selector(node[:-1]))[node[-1]]
    try:
        return node.prior_action.prob
    except AttributeError:
        return node.parent.action_probs[node.prior_action.label]


def _player_label(player):
    """Return the label of a player.

    Works with both pre- and post-Player-removal pygambit: before the removal,
    `player` is a `Player` object with a `.label` property; after it, `player`
    already is the label itself.
    """
    return getattr(player, "label", player)


def _node_player(node, game):
    """Return the label (or `Player` object, on older pygambit -- see
    `_player_label`) of the player who owns `node`, personal or chance, or
    `None` for a terminal node.

    Works across `Node.player` (older pygambit) and, once `Node` is no longer
    public and `node` is a `History` tuple, `Game.get_player`.
    """
    if _is_history(node):
        return game.get_player(_selector(node))
    return node.player


def _is_chance_node(node, game):
    """Return whether `node` is a chance node.

    Works across pygambit's Infoset/Event split, the later removal of
    `Player.is_chance`, and the eventual removal of `Node.event` itself: once
    neither `Player` nor `Node.event` remain, the chance player is identified
    by its fixed (never user-assigned) label, "Chance" -- `_node_player`
    already resolves that label across both `Node`- and `History`-based
    `node`.
    """
    try:
        return bool(node.event)
    except AttributeError:
        pass
    player = _node_player(node, game)
    try:
        return player.is_chance
    except AttributeError:
        return player == "Chance"


def _node_is_terminal(node, game):
    """Return whether `node` has no further moves.

    Works across `Node.is_terminal` (older pygambit) and, once `Node` is no
    longer public and `node` is a `History` tuple, `Game.get_actions`
    returning an empty list for a terminal node.
    """
    if _is_history(node):
        return not game.get_actions(_selector(node))
    return node.is_terminal


def _node_outcome(node, game):
    """Return the outcome attached at terminal `node`, or a falsy value
    (`None`) if it has none.

    Works across `Node.outcome` (an indexable, node-anchored view, older
    pygambit) and, once `Node.outcome` and `Outcome` are both removed and
    `node` is a `History` tuple, `Game.get_outcome` (returning only the
    outcome's label) combined with `Game.get_outcome_payoffs(label)` to
    recover a mapping indexable by player, matching the older `Node.outcome`'s
    shape.
    """
    if _is_history(node):
        label = game.get_outcome(_selector(node))
        return game.get_outcome_payoffs(label) if label is not None else None
    return node.outcome


def _node_is_root(node, game):
    """Return whether `node` is the game's root.

    Works across `Game.root` (older pygambit, compared to a `Node`) and, once
    `Game.root` is removed, the empty `History` tuple.
    """
    if _is_history(node):
        return not node
    return node == game.root


def _node_parent(node, game):
    """Return the parent of `node`, or `None` if it is the root.

    Works across `Node.parent` (older pygambit) and, once `Node` is no longer
    public, dropping the last label of the `History` tuple.
    """
    if _is_history(node):
        return node[:-1] if node else None
    return node.parent


def _prior_action_label(node):
    """Return the label of the action leading to `node` from its parent.

    Works across `Node.prior_action.label` (older pygambit) and the last
    element of the `History` tuple, once `Node` is no longer public --
    `layout_tree`'s own `History` keys are root-anchored paths of exactly the
    action labels taken to reach each node.
    """
    if _is_history(node):
        return node[-1]
    return node.prior_action.label


def determine_node_level(
    gbt_level: int,
    gbt_sublevel: int,
    level_multiplier: int = 4,
    sublevel_multiplier: int = 2,
) -> int:
    """Determine the node level in the .ef format based on Gambit layout levels."""
    if level_multiplier < 0:
        raise ValueError(
            f"level_multiplier must be non-negative, got {level_multiplier}"
        )
    if sublevel_multiplier < 0:
        raise ValueError(
            f"sublevel_multiplier must be non-negative, got {sublevel_multiplier}"
        )
    depth = gbt_level * level_multiplier - (level_multiplier / 2)
    extra_depth = 0
    if gbt_sublevel != 0:
        extra_depth = ((gbt_sublevel - 1) * sublevel_multiplier)
    return depth + extra_depth


def gambit_layout_to_ef(
    game: pygambit.gambit.Game,
    save_to: Optional[str] = None,
    level_multiplier: int = 4,
    sublevel_multiplier: int = 2,
    xshift_multiplier: int = 2,
    hide_action_labels: bool = False,
    shared_terminal_depth: bool = False,
) -> str:
    """Convert an extensive form Gambit game to the `.ef` format
    using the layout tree defined by pygambit.layout_tree(game.)

    Args:
        game: A pygambit.gambit.Game object representing the game.
        save_to: Optional path to save the generated `.ef` file.
        level_multiplier: Multiplier for levels in the layout.
        sublevel_multiplier: Multiplier for sublevels in the layout.
        xshift_multiplier: Multiplier for xshift values in the layout.
        hide_action_labels: Whether to hide action labels in the output.
        shared_terminal_depth: Whether to force all terminal nodes to the same depth.

    Returns:
        The filename of the generated `.ef` file.
    Raises:
        ValueError: If any multiplier argument is not positive.
    """
    if level_multiplier < 0:
        raise ValueError(
            f"level_multiplier must be non-negative, got {level_multiplier}"
        )
    if sublevel_multiplier < 0:
        raise ValueError(
            f"sublevel_multiplier must be non-negative, got {sublevel_multiplier}"
        )
    if xshift_multiplier < 0:
        raise ValueError(
            f"xshift_multiplier must be non-negative, got {xshift_multiplier}"
        )

    # Get the layout from pygambit. `layout.items()` yields either
    # (Node, NodeCoordinates) pairs (older pygambit) or (History,
    # TreeLayoutCoordinates) pairs (once Node/Game.root are no longer public);
    # every node-based helper above dispatches on which one it received.
    layout = pygambit.layout_tree(game)

    # Start building the .ef string
    ef = ""

    # Add the player lines to the .ef string
    player_ids = {}
    p = 1
    for player in game.players:
        player_name = _player_label(player).replace(" ", "~")
        ef += f"player {p} name {player_name}\n"
        player_ids[_player_label(player)] = p
        p += 1

    # Group nodes by their infosets
    # Also collect parent node levels for level determination
    # Also collect highest level for level determination
    infoset_groups = {}
    gbt_parent_levels = {}
    gbt_highest_level = 0
    gbt_highest_sublevel = 0
    for node, node_coords in layout.items():
        partition = _partition(node, game)
        if partition:
            if partition not in infoset_groups:
                infoset_groups[partition] = []
            infoset_groups[partition].append(node)
        # Get the level of a parent node, if applicable
        if not _node_is_root(node, game):
            parent_coords = layout[_node_parent(node, game)]
            gbt_parent_levels[node] = (parent_coords.level, parent_coords.sublevel)
        # Update highest level
        gbt_highest_level = max(node_coords.level, gbt_highest_level)
        gbt_highest_sublevel = max(node_coords.sublevel, gbt_highest_sublevel)

    # For each node, determine its level and globally unique node ID.
    # Also collect offsets for normalisation.
    node_levels = {}
    node_global_ids = {}
    global_counter = 0
    offsets = []
    for node, node_coords in layout.items():

        # Calculate the node level, using gambit level and sublevel
        if _node_is_terminal(node, game) and shared_terminal_depth:
            level = determine_node_level(gbt_highest_level, gbt_highest_sublevel, level_multiplier, sublevel_multiplier)
        else:
            level = determine_node_level(node_coords.level, node_coords.sublevel, level_multiplier, sublevel_multiplier)

        # Ensure child nodes have levels greater than their parents
        if not _node_is_root(node, game):
            gbt_parent_level, gbt_parent_sublevel = gbt_parent_levels[node]
            parent_level = determine_node_level(gbt_parent_level, gbt_parent_sublevel, level_multiplier, sublevel_multiplier)
            if level_multiplier > 0:
                while level <= parent_level:
                    level += level_multiplier

        # Assign globally unique node ID (EF 3.0)
        global_counter += 1
        node_levels[node] = level
        node_global_ids[node] = global_counter

        # Collect offsets for normalisation
        offsets.append(node_coords.offset)

    # Calculate midpoint for offset normalisation
    midpoint = (min(offsets) + max(offsets)) / 2

    # Normalise offsets based on the midpoint
    nodes_with_normalised_offsets = {}
    for node, node_coords in layout.items():
        nodes_with_normalised_offsets[node] = (node_coords.offset - midpoint) * xshift_multiplier

    # Now, build the node lines in the .ef string
    for node, node_coords in layout.items():

        # Determine the player for the node
        player = None
        node_player = _node_player(node, game)
        if node_player:
            if _is_chance_node(node, game):
                player = "0"
            else:
                player = player_ids[_player_label(node_player)]

        # Add the level and globally unique node ID (EF 3.0)
        level = node_levels[node]
        node_id = node_global_ids[node]
        ef += f"level {level} node {node_id} "

        # Add player if applicable to this node
        # Do not add player if in infoset with multiple nodes (will be defined by `iset` later)
        if player and len(infoset_groups[_partition(node, game)]) == 1:
            ef += f"player {player} "

        parent = _node_parent(node, game)

        # Calculate xshift and add to .ef string not root node
        if level > 0:
            xshift = nodes_with_normalised_offsets[node] - (
                nodes_with_normalised_offsets[parent] if parent is not None else 0
            )
            ef += f"xshift {xshift} "

        # Determine where the node comes from (its parent and prior action)
        if parent is not None:
            parent_id = node_global_ids[parent]
            ef += f"from {parent_id} "
            if not hide_action_labels:
                prior_action_label = _prior_action_label(node).replace(" ", "~")
                ef += f"move {prior_action_label}"

            # Add probability if the parent is a chance player
            if _is_chance_node(parent, game):
                action_prob = _prior_action_prob(node, game)
                prob = str(action_prob).split("/")
                if len(prob) == 2:
                    ef += f"~(\\frac{{{prob[0]}}}{{{prob[1]}}})"
                elif len(prob) == 1:
                    ef += f"~{prob[0]}"
                else:
                    # Throw error for unexpected probability format
                    raise ValueError(f"Unexpected probability format: {action_prob}")
            ef += " "

        # Add payoffs to terminal nodes, if applicable
        if _node_is_terminal(node, game):
            ef += "payoffs "
            outcome = _node_outcome(node, game)
            if outcome:
                for player in game.players:
                    ef += f"{outcome.__getitem__(player)} "
        ef += "\n"

    # Build the infoset lines in the .ef string with `iset`
    for _, nodes in infoset_groups.items():
        if len(nodes) > 1:
            ef += "iset "
            for node in nodes:
                ef += f"{node_global_ids[node]} "
            ef += f"player {player_ids[_player_label(_node_player(node, game))]} "
            ef += "\n"

    # Save the constructed .ef string to file based on the game's name
    if save_to:
        ef_file = save_to
        if ".ef" not in save_to:
            ef_file = save_to + ".ef"
    else:
        ef_file = game.title + ".ef"
    with open(ef_file, "w", encoding="utf-8") as f:
        f.write(ef)
    return ef_file
