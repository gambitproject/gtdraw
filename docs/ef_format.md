# The EF Format Specification

The `.ef` (extensive form) file format describes a game tree layout textually. You can write these files by hand or generate them using [Game Theory Explorer](https://gametheoryexplorer-a68c7.web.app/).

The file consists of lines starting with keywords: `player`, `level`, or `iset`. Additional information follows on the same line, separated by whitespace (spaces or tabs).
No spaces are allowed in move names, player names, or payoffs (use `~` instead).
You can add comments by prefixing a line with `%`.

::::{grid} 1 1 12 12

:::{grid-item}
:columns: 7

An example EF file:
```text
% Example game (EF 3.0 — globally unique node identifiers)
player 1 name I
player 2 name II
level 0 node 1 player 1
level 2 node 2 player 0 xshift a=1.5 from 1 move R
level 4 node 3 xshift -2a from 1 move::0.25 L
level 2 node 4 xshift -.5 from 1 move:r: M payoffs 3 3
level 4 node 5 xshift -b=1.2 from 2 move \frac{1}{3}
level 4 node 6 xshift b from 2 move \frac{2}{3} payoffs 1 -1
level 6 node 7 xshift -c=.8 from 3 move a payoffs 5 1
level 6 node 8 xshift c from 3 move b payoffs 2 0
level 6 node 9 xshift -c from 5 move a payoffs 6 0
level 6 node 10 xshift c from 5 move b payoffs 0 2
iset 3 5 player 2
```
:::

:::{grid-item}
:columns: 5

The game it generates:
```{image} ../img/example.svg
:alt: EF file format example game tree
```
:::

::::

## Players
Use the `player` keyword to define player names. By default, player 0 is "chance", and other players are just their numbers.

```text
player 1 name I
player 2 name II
```

If the chance player is meant to have no name, write `player 0 name ~`. The `~` symbol acts as a non-breakable space.

## Nodes and Levels
The `level` keyword encodes game tree nodes. The tree starts at `level 0` for the root. Each subsequent level is typically an even number, representing standard level distances of 2 centimeters.

Each node requires a **globally unique** identifier — unique across the *entire* file, not just within its level.  This is the EF 3.0 default, and it means you can freely adjust a node's `level` value for layout reasons without having to rename the node or update any references to it.

```text
level 0 node 1 player 1
level 2 node 2 from 1 move Left
level 2 node 3 from 1 move Right payoffs 1 0
```

Omit the `player` specification if the node is a terminal node (with payoffs) or if the player will be specified later via an information set (`iset`). A chance node needs `player 0` to get the square node symbol.

### Legacy EF 2.x format (backward compatible)

Older `.ef` files use a per-level numbering scheme where the same node number may appear at different levels (e.g., `level 2 node 1` and `level 4 node 1` are two different nodes). In that scheme, nodes are identified by the composite `level,nodeid` pair — and `from` / `iset` references also use that composite form:

```text
level 0 node 1 player 1
level 2 node 1 from 0,1 move Left
level 2 node 2 from 0,1 move Right payoffs 1 0
```

GTDraw automatically detects the format: if any `from` reference contains a comma (e.g. `from 2,1`), the file is treated as EF 2.x; otherwise EF 3.0 is assumed. All existing files continue to work without modification.

## Parenting
Specify the parent of a node using `from`, followed by the parent node's identifier.

**EF 3.0 (globally unique IDs):**
```text
level 2 node 2 from 1
```

**EF 2.x (per-level IDs):**
```text
level 2 node 1 from 0,1
```

## Positioning (xshift)
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
The `iset` keyword defines an information set connecting multiple nodes. Provide a list of node identifiers, and optionally end with the `player` number.

**EF 3.0 (globally unique IDs):**
```text
iset 3 5 player 2
```

**EF 2.x (per-level IDs):**
```text
iset 4,1 4,2 player 2
```

When using the `default` color scheme (which lacks the legend used by other color schemes), the player name will be placed between the two middle nodes for an even number of nodes, or before the middle node for an odd number. You can place the player specifier between the respective nodes in the list to position the label differently.

