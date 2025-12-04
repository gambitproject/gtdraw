import pygambit
from typing import Optional


def determine_node_level(
    gbt_level: int,
    gbt_sublevel: int,
    level_multiplier: int = 4,
    sublevel_multiplier: int = 2,
) -> int:
    """Determine the node level in the .ef format based on Gambit layout levels."""
    # If node is in an infoset
    if gbt_sublevel != 0:
        return (gbt_level * level_multiplier) + ((gbt_sublevel - 1) * sublevel_multiplier) - (level_multiplier / 2)
    return (gbt_level * level_multiplier) - (level_multiplier / 2)


def gambit_layout_to_ef(
    game: pygambit.gambit.Game,
    save_to: Optional[str] = None,
    level_multiplier: int = 4,
    sublevel_multiplier: int = 2,
    xshift_multiplier: int = 2
) -> str:
    """Convert an extensive form Gambit game to the `.ef` format
    using the layout tree defined by pygambit.layout_tree(game.)

    Args:
        game: A pygambit.gambit.Game object representing the game.
        save_to: Optional path to save the generated `.ef` file.

    Returns:
        The filename of the generated `.ef` file.
    """

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
    infoset_groups = {}
    gbt_parent_levels = {}
    for node, node_coords in layout.items():
        if node.infoset:
            if node.infoset not in infoset_groups:
                infoset_groups[node.infoset] = []
            infoset_groups[node.infoset].append(node)
        # Get the level of a parent node, if applicable
        if not node == game.root:
            parent_coords = layout[node.parent]
            gbt_parent_levels[node] = (parent_coords.level, parent_coords.sublevel)

    # For each node, determine its level and node count within that level
    # Also collect offsets for normalisation
    levels_nodecount = {}
    node_levels = {}
    offsets = []
    for node, node_coords in layout.items():

        # Calculate the node level, using gambit level and sublevel
        # Ignore sublevel for nodes that don't share an infoset
        gbt_sublevel = node_coords.sublevel
        if node.infoset in infoset_groups:
            if len(infoset_groups[node.infoset]) == 1:
                gbt_sublevel = 0
        level = determine_node_level(node_coords.level, gbt_sublevel, level_multiplier, sublevel_multiplier)

        # Ensure child nodes have levels greater than their parents
        if not node == game.root:
            gbt_parent_level, gbt_parent_sublevel = gbt_parent_levels[node]
            parent_level = determine_node_level(gbt_parent_level, gbt_parent_sublevel, level_multiplier, sublevel_multiplier)
            while level <= parent_level:
                level += level_multiplier
        
        # Track node counts per level
        if level not in levels_nodecount:
            levels_nodecount[level] = 1
        else:
            levels_nodecount[level] += 1
        node_levels[node] = (level, levels_nodecount[level])

        # Collect offsets for normalisation
        offsets.append(node_coords.offset)

    # Calculate midpoint for offset normalisation
    midpoint = (min(offsets) + max(offsets)) / 2

    # Normalise offsets based on the midpoint
    nodes_with_normalised_offsets = {}
    for node, node_coords in layout.items():
        nodes_with_normalised_offsets[node] = -(node_coords.offset - midpoint) * xshift_multiplier
    
    # Now, build the node lines in the .ef string
    for node, node_coords in layout.items():

        # Determine the player for the node
        player = None
        if node.player:
            if node.player.is_chance:
                player = "0"
            else:
                player = player_ids[node.player]
        
        # Add the level and node count
        # This is effectively the node ID in .ef format
        level, nodecount = node_levels[node]
        ef += f"level {level} node {nodecount} "

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
            parent_level, parent_nodecount = node_levels[node.parent]
            ef += f"from {parent_level},{parent_nodecount} "
            prior_action_label = node.prior_action.label.replace(" ", "~")
            ef += f"move {prior_action_label}"

            # Add probability if the parent is a chance player
            if node.parent.player.is_chance:
                prob = str(node.prior_action.prob).split("/")
                ef += f"~(\\frac{{{prob[0]}}}{{{prob[1]}}})"
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
                level, nodecount = node_levels[node]
                ef += f"{level},{nodecount} "
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
