"""Shared test-only shims for building pygambit games across incompatible API
generations.

pygambit's API has moved through several incompatible shapes over the course of
the 17.0 development cycle (Player objects, then Infoset/Event objects, then
H-expression Selectors, all being removed or introduced in turn; most recently,
`Node`/`Game.root` themselves were removed from the public API). These helpers
let the test suite build games under any of them: each tries the newest pygambit
behaviour first and falls back to older ones on TypeError/AttributeError,
mirroring the shims in gtdraw.gambit_layout.

Every function here takes a `history` (or `reference_history`): a plain,
root-anchored tuple of action labels (e.g. `()` for the root, `("Left",)` for
its "Left" child) identifying a node -- not a `Node` object, since `Game.root`/
`Node.children` (the only way to obtain one) are themselves no longer public on
the newest pygambit. `_node_from_history` reconstructs an actual `Node` from
one of these tuples, for the older-pygambit branches that still need one.
"""

import itertools

import pygambit

_outcome_labels = itertools.count(1)


def _node_from_history(game, history):
    """Resolve `history` (a root-anchored tuple of action labels) to the
    `Node` it identifies. Only used for pygambit generations old enough that
    `Game.root`/`Node.children` are still public and some mutation method
    still requires a literal `Node` rather than a `Selector`.
    """
    node = game.root
    for label in history:
        node = node.children[label]
    return node


def selector_for_history(history):
    """The `pygambit.H` Selector resolving to exactly the node `history` (a
    root-anchored tuple of action labels) identifies.
    """
    return pygambit.H.path(*history)


def append_move(game, history, player, actions):
    """Add a personal move at the node identified by `history` for `player`
    (a label, `str`).

    Works across pygambit's evolving `append_move`: newest takes a `Selector`
    and a player label directly; oldest takes a bare `Node` and a `Player`
    object (`game.players[player]`).
    """
    try:
        game.append_move(selector_for_history(history), player, actions)
        return
    except (TypeError, AttributeError):
        pass
    game.append_move(_node_from_history(game, history), game.players[player], actions)


def append_chance_move(game, history, action_probs):
    """Add a chance move at the node identified by `history`, with actions
    and probabilities given by the `action_probs` mapping (action label ->
    probability, as `str`).

    Works across pygambit's chance-move APIs: newest uses a dedicated
    `append_event` taking a `Selector` and the probability mapping directly;
    older pygambit added the move via `append_move` with `game.players.chance`
    and set probabilities separately via `set_chance_probs`.
    """
    try:
        game.append_event(selector_for_history(history), action_probs)
        return
    except (TypeError, AttributeError):
        pass
    node = _node_from_history(game, history)
    game.append_move(node, game.players.chance, list(action_probs.keys()))
    game.set_chance_probs(node.infoset, list(action_probs.values()))


def set_outcome(game, history, payoffs):
    """Attach an outcome with `payoffs` (a positional list, one per player, in
    `game.players` order) at the node identified by `history`.

    Works across pygambit's outcome-creation APIs: newest combines creation and
    attachment into a single `make_outcome(location, payoffs_mapping, label)`
    call, which requires a nonempty, game-unique label -- a synthetic one is
    generated, since these tests don't care about its content; older pygambit
    created the outcome via `add_outcome(payoffs_list)` and attached it
    separately via `set_outcome(node, outcome)`.
    """
    try:
        mapping = dict(zip(game.players, payoffs, strict=True))
        game.make_outcome(
            selector_for_history(history), mapping, f"outcome{next(_outcome_labels)}"
        )
        return
    except (TypeError, AttributeError):
        pass
    node = _node_from_history(game, history)
    game.set_outcome(node, game.add_outcome(payoffs))


def join_infoset(game, history, reference_history):
    """Attach the move at the node identified by `history` to the same
    information set as the node identified by `reference_history`.

    Works across pygambit's evolving `append_infoset`: newest requires both
    `nodes` and `infoset` to be `Selector`s; the post-Infoset-redesign,
    pre-Selector-only version took a `Node` and a `Node` directly; the oldest
    took a `Node` and an `Infoset`.
    """
    try:
        game.append_infoset(
            selector_for_history(history), selector_for_history(reference_history)
        )
        return
    except (TypeError, AttributeError):
        pass
    node = _node_from_history(game, history)
    reference_node = _node_from_history(game, reference_history)
    try:
        game.append_infoset(node, reference_node)
        return
    except TypeError:
        pass
    game.append_infoset(node, reference_node.infoset)
