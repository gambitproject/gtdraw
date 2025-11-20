from draw_tree.layout import DefaultLayout


def make_descriptor(kind, player=None, moves=None, probs=None, payoffs=None, iset_id=None, raw=""):
    return {
        'kind': kind,
        'player': player,
        'moves': moves or [],
        'probs': probs or [],
        'payoffs': payoffs or [],
        'iset_id': iset_id,
        'raw': raw,
    }


def test_defaultlayout_simple_player_tree():
    # Root player with two moves leading to two terminals
    desc = [
        make_descriptor('p', player=1, moves=['A', 'B']),
        make_descriptor('t', payoffs=[1, 0]),
        make_descriptor('t', payoffs=[0, 1]),
    ]
    layout = DefaultLayout(desc, ['P1'])
    lines = layout.to_lines()
    # Must contain player name and two terminal payoffs lines
    assert any(line.startswith('player 1 name') for line in lines)
    # find lines with payoffs
    payoff_lines = [line for line in lines if 'payoffs' in line]
    assert len(payoff_lines) == 2
    assert '1 0' in payoff_lines[0] or '1 0' in payoff_lines[1]


def test_defaultlayout_chance_fraction_probabilities():
    # Chance root with two moves using fractional probs 1/2 and 1/2
    desc = [
        make_descriptor('c', moves=['X', 'Y'], probs=['1/2', '1/2']),
        make_descriptor('t', payoffs=[1, -1]),
        make_descriptor('t', payoffs=[-1, 1]),
    ]
    layout = DefaultLayout(desc, ['Chance'])
    lines = layout.to_lines()
    # Should include the moved label with \frac printed literally
    move_lines = [line for line in lines if 'move' in line]
    # either the LaTeX \frac is present or a plain (1/2) form
    assert any('\\frac{1}{2}' in line or '(1/2)' in line for line in move_lines)
