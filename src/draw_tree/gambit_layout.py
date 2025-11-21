import pygambit


def determine_node_level(gbt_level, gbt_sublevel):
    return (gbt_level * 2) + gbt_sublevel


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
    for node, node_coords in layout.items():
        levels_nodecount[
            determine_node_level(node_coords.level, node_coords.sublevel)
        ] = 1
    for node, node_coords in layout.items():
        level = determine_node_level(node_coords.level, node_coords.sublevel)
        player = None
        if node.player:
            if node.player.is_chance:
                player = 0
            else:
                player = player_ids[node.player]
        ef += f"level {level} node {levels_nodecount[level]} "
        if player:
            ef += f"player {player}"
        ef += "\n"
        levels_nodecount[level] += 1

    return ef