import pygambit
from typing import Optional


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

    # Get the layout from pygambit
    layout = pygambit.layout_tree(game)

    # Start building the .ef string
    ef = ""

    # Add the player lines to the .ef string
    player_ids = {}
    p = 1
    for player in game.players:
        player_name = player.label.replace(" ", "~")
        ef += f"player {p} name {player_name}\n"
        player_ids[player] = p
        p += 1

    # Group nodes by their infosets
    # Also collect parent node levels for level determination
    # Also collect highest level for level determination
    infoset_groups = {}
    gbt_parent_levels = {}
    gbt_highest_level = 0
    gbt_highest_sublevel = 0
    for node, node_coords in layout.items():
        if node.infoset:
            if node.infoset not in infoset_groups:
                infoset_groups[node.infoset] = []
            infoset_groups[node.infoset].append(node)
        # Get the level of a parent node, if applicable
        if not node == game.root:
            parent_coords = layout[node.parent]
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
        if node.is_terminal and shared_terminal_depth:
            level = determine_node_level(gbt_highest_level, gbt_highest_sublevel, level_multiplier, sublevel_multiplier)
        else:
            level = determine_node_level(node_coords.level, node_coords.sublevel, level_multiplier, sublevel_multiplier)

        # Ensure child nodes have levels greater than their parents
        if not node == game.root:
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
        if node.player:
            if node.player.is_chance:
                player = "0"
            else:
                player = player_ids[node.player]

        # Add the level and globally unique node ID (EF 3.0)
        level = node_levels[node]
        node_id = node_global_ids[node]
        ef += f"level {level} node {node_id} "

        # Add player if applicable to this node
        # Do not add player if in infoset with multiple nodes (will be defined by `iset` later)
        if player and len(infoset_groups[node.infoset]) == 1:
            ef += f"player {player} "

        # Calculate xshift and add to .ef string not root node
        if level > 0:
            xshift = nodes_with_normalised_offsets[node] - (
                nodes_with_normalised_offsets[node.parent] if node.parent else 0
            )
            ef += f"xshift {xshift} "

        # Determine where the node comes from (its parent and prior action)
        if node.parent:
            parent_id = node_global_ids[node.parent]
            ef += f"from {parent_id} "
            if not hide_action_labels:
                prior_action_label = node.prior_action.label.replace(" ", "~")
                ef += f"move {prior_action_label}"

            # Add probability if the parent is a chance player
            if node.parent.player.is_chance:
                prob = str(node.prior_action.prob).split("/")
                if len(prob) == 2:
                    ef += f"~(\\frac{{{prob[0]}}}{{{prob[1]}}})"
                elif len(prob) == 1:
                    ef += f"~{prob[0]}"
                else:
                    # Throw error for unexpected probability format
                    raise ValueError(f"Unexpected probability format: {node.prior_action.prob}")
            ef += " "

        # Add payoffs to terminal nodes, if applicable
        if node.is_terminal:
            ef += "payoffs "
            if node.outcome:
                for player in game.players:
                    ef += f"{node.outcome.__getitem__(player)} "
        ef += "\n"

    # Build the infoset lines in the .ef string with `iset`
    for _, nodes in infoset_groups.items():
        if len(nodes) > 1:
            ef += "iset "
            for node in nodes:
                ef += f"{node_global_ids[node]} "
            ef += f"player {player_ids[node.player]} "
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
