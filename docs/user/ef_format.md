# The `.ef` Format Specification

The `.ef` (extensive form) file format describes a game tree layout textually. You can write these files by hand or generate them using [Game Theory Explorer](https://gametheoryexplorer-a68c7.web.app/).

The file consists of lines starting with keywords: `player`, `level`, or `iset`. Additional information follows on the same line, separated by whitespace (spaces or tabs). You can add comments by prefixing a line with `%`.

## Players
Use the `player` keyword to define player names. By default, player 0 is "chance", and other players are just their numbers.

```text
player 1 name I
player 2 name II
```

If the chance player is meant to have no name, write `player 0 name ~`. The `~` symbol acts as a non-breakable space.

## Nodes and Levels
The `level` keyword encodes game tree nodes. The tree starts at `level 0` for the root. Each subsequent level is typically an even number, representing standard level distances of 2 centimeters.

Each node requires an identifier, typically numbered per level. The combination of `level,nodeid` without spaces identifies the node uniquely (e.g., `0,1` for the root).

```text
level 0 node 1 player 1
```

Omit the `player` specification if the node is a terminal node (with payoffs) or if the player will be specified later via an information set (`iset`). A chance node needs `player 0` to get the square node symbol.

## Parenting
Specify the parent of a node using `from`, followed by the parent's `level,nodeid`.

```text
level 2 node 1 from 0,1
```

## Positioning (`xshift`)
The `xshift` keyword specifies the horizontal offset in centimeters relative to the parent node. For example, `xshift -1.2` means 1.2 cm to the left.

You can assign and reuse variables:
- `xshift -b=1.2` sets the shift to -1.2 and assigns 1.2 to the variable `b`.
- Later, you can use `xshift b` to shift 1.2 cm to the right.

Variables can be any identifiers not starting with a digit. Multipliers are supported: `xshift -2a` moves -2 times the value of `a`.

## Moves
The move label is specified with `move`:
```text
move L
move \frac{1}{3}
```
*No spaces are allowed in move names, player names, or payoffs. Use `~` instead.*

**Modifiers:**
- `move:l` or `move:r`: Force the move label to the left or right of the connecting line. The default is right for a line going down-right, and left otherwise.
- `move::0.25`: Specifies the location of the move label as a fraction of the distance from parent to child (default is 0.5).

## Payoffs
The `payoffs` keyword comes last on a `level` line. Follow it with space-separated values for each player (up to 4).

```text
payoffs 3 3
payoffs 1 -1
```

## Information Sets
The `iset` keyword defines an information set connecting multiple nodes. Provide a list of nodes, and optionally end with the `player` number.

```text
iset 4,1 4,2 player 2
```

The player name will be placed between the two middle nodes for an even number of nodes, or before the middle node for an odd number. You can place the player specifier between the respective nodes in the list to position the label differently.

## Complete Example

```text
player 1 name I
player 2 name II
level 0 node 1 player 1
level 2 node 1 player 0 xshift a=1.5 from 0,1 move R
level 4 node 1 xshift -2a from 0,1 move::0.25 L
level 2 node x xshift -.5 from 0,1 move:r M payoffs 3 3
level 4 node 2 xshift -b=1.2 from 2,1 move \frac{1}{3}
level 4 node 3 xshift b from 2,1 move \frac{2}{3} payoffs 1 -1
level 6 node 1 xshift -c=.8 from 4,1 move a payoffs 5 1
level 6 node 2 xshift c from 4,1 move b payoffs 2 0
level 6 node 3 xshift -c from 4,2 move a payoffs 6 0
level 6 node 4 xshift c from 4,2 move b payoffs 0 2
iset 4,1 4,2 player 2
```
