import pygambit as gbt


def determine_node_level(gbt_level, gbt_sublevel):
    if gbt_level > 1:
        return (gbt_level * 2) + (gbt_sublevel - 1)
    return gbt_level * 2


def gambit_layout_to_ef(game: pygambit.gambit.Game) -> str:
    """Convert an extensive form Gambit game to the `.ef` format
    using the layout tree defined by pygambit.layout_tree(game.)

    Args:
        game: A pygambit.gambit.Game object representing the game.

    Returns:
        A string containing the `.ef` formatted representation of the game.
    """
    layout = gbt.layout_tree(game)
    ef = ""
    # Add the players
    player_ids = {}
    p = 1
    for player in game.players:
        ef += f"player {p} name {player.label}\n"
        player_ids[player] = p
        p += 1

    # Add the nodes
    levels_nodecount = {}
    node_levels = {}
    offsets = []
    for node, node_coords in layout.items():
        level = determine_node_level(node_coords.level, node_coords.sublevel)
        if level not in levels_nodecount:
            levels_nodecount[level] = 1
        else:
            levels_nodecount[level] += 1
        node_levels[node] = (level, levels_nodecount[level])
        offsets.append(node_coords.offset)
    midpoint = (min(offsets) + max(offsets)) / 2
    nodes_with_normalised_offsets = {}
    for node, node_coords in layout.items():
        nodes_with_normalised_offsets[node] = -(node_coords.offset - midpoint)
    infoset_groups = {}
    for node, node_coords in layout.items():
        player = None
        if node.player:
            if node.player.is_chance:
                player = "0"
            else:
                player = player_ids[node.player]
        level, nodecount = node_levels[node]
        ef += f"level {level} node {nodecount} "
        if player:
            ef += f"player {player} "
        if level > 0:
            xshift = nodes_with_normalised_offsets[node] - (
                nodes_with_normalised_offsets[node.parent] if node.parent else 0
            )
            ef += f"xshift {xshift} "

        if node.parent:
            parent_level, parent_nodecount = node_levels[node.parent]
            ef += f"from {parent_level},{parent_nodecount} "
            ef += f"move {node.prior_action.label}"
            if node.parent.player.is_chance:
                prob = str(node.prior_action.prob).split("/")
                ef += f"~(\\frac{{{prob[0]}}}{{{prob[1]}}})"
            ef += " "
        if node.is_terminal:
            ef += "payoffs "
            for player in game.players:
                ef += f"{node.outcome.__getitem__(player.label)} "
        ef += "\n"
        if node.infoset:
            if node.infoset not in infoset_groups:
                infoset_groups[node.infoset] = []
            infoset_groups[node.infoset].append(node)
    for infoset, nodes in infoset_groups.items():
        if len(nodes) > 1:
            ef += "iset "
            for node in nodes:
                level, nodecount = node_levels[node]
                ef += f"{level},{nodecount} "
            ef += f"player {player_ids[node.player]} "
            ef += "\n"
    return ef