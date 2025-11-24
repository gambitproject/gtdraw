from re import sub
import pygambit
from typing import Optional


def determine_node_level(gbt_level, gbt_sublevel) -> int:
    """Determine the node level in the .ef format based on Gambit layout levels."""
    sublevel = (gbt_level * 2) + (gbt_sublevel - 1)
    if gbt_level > 1:
        return sublevel
    return gbt_level * 2


def gambit_layout_to_ef(
    game: pygambit.gambit.Game, output_path: Optional[str] = None
) -> str:
    """Convert an extensive form Gambit game to the `.ef` format
    using the layout tree defined by pygambit.layout_tree(game.)

    Args:
        game: A pygambit.gambit.Game object representing the game.
        output_path: Optional path to save the generated `.ef` file.

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
        ef += f"player {p} name {player.label}\n"
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
        sublevel = node_coords.sublevel
        if node.infoset in infoset_groups:
            if len(infoset_groups[node.infoset]) == 1:
                sublevel = 0
        level = determine_node_level(node_coords.level, sublevel)
        if not node == game.root:
            gbt_parent_level, gbt_parent_sublevel = gbt_parent_levels[node]
            parent_level = determine_node_level(gbt_parent_level, gbt_parent_sublevel)
            while level <= parent_level:
                level += 1
            
        if level not in levels_nodecount:
            levels_nodecount[level] = 1
        else:
            levels_nodecount[level] += 1
        node_levels[node] = (level, levels_nodecount[level])
        offsets.append(node_coords.offset)

    # Calculate midpoint for offset normalisation
    midpoint = (min(offsets) + max(offsets)) / 2

    # Normalise offsets based on the midpoint
    nodes_with_normalised_offsets = {}
    for node, node_coords in layout.items():
        nodes_with_normalised_offsets[node] = -(node_coords.offset - midpoint)
    
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
        if player:
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
            ef += f"move {node.prior_action.label}"

            # Add probability if the parent is a chance player
            if node.parent.player.is_chance:
                prob = str(node.prior_action.prob).split("/")
                ef += f"~(\\frac{{{prob[0]}}}{{{prob[1]}}})"
            ef += " "
        
        # Add payoffs to terminal nodes
        if node.is_terminal:
            ef += "payoffs "
            for player in game.players:
                ef += f"{node.outcome.__getitem__(player.label)} "
        ef += "\n"

    # Build the infoset lines in the .ef string
    for infoset, nodes in infoset_groups.items():
        if len(nodes) > 1:
            ef += "iset "
            for node in nodes:
                level, nodecount = node_levels[node]
                ef += f"{level},{nodecount} "
            ef += f"player {player_ids[node.player]} "
            ef += "\n"

    # Save the constructed .ef string to file based on the game's name
    ef_file = game.title + ".ef"
    if output_path:
        ef_file = output_path + "/" + ef_file
    with open(ef_file, "w", encoding="utf-8") as f:
        f.write(ef)
    return ef_file
