# CLI

By default, `draw_tree` generates TikZ code and prints it to standard output.
There are also options to generate a complete LaTeX document, an SVG, PDF or a PNG directly, either by specifying the desired format or by using the output filename extension:

```bash
draw_tree games/example.ef --pdf
```

:::{note}
You can also use `.efg` files from Gambit instead of `.ef` files.
:::

## CLI Options

| Category | Option | Description |
| :--- | :--- | :--- |
| **Formatting** | `--pdf`, `--png`, `--svg`, `--tex` | Output format instead of printing TikZ code. |
| | `--output=mygame.pdf` | Specify output filename (extension determines format). |
| | `--dpi=X` | Set PNG resolution in DPI (72-2400, default: 300). |
| **Layout** | `scale=X.X` | Set scale factor (0.01 to 100). |
| | `--horizontal` | Switch from vertical to horizontal layout (left-to-right). |
| | `--mirror` | Mirror the tree left-to-right (flip xshift values). |
| | `--legend-position=X` | Corner for the colour legend: `top-left` (default), `top-right`, `bottom-left`, `bottom-right`. |
| | `--action-label-dist=X.X` | Distance of action labels from the edge (default: 1.0). |
| | `--action-label-position=X` | Position of action labels along the edge. Accepts a single float (0.0 to 1.0, default: 0.5), a player-keyed list (`player_index:position`, e.g. `0:0.3,1:0.7`), or a level-keyed list (`level_index:position`, e.g. `0:0.3,1:0.7`). |
| | `--action-label-position-by=[player\|level]` | Interpret a dictionary `--action-label-position` as keyed by player index (default: `player`) or by tree level index (`level`). |
| | `--vary-action-label-positions`| Vary action label positions along child edges of a node to avoid clashes. |
| | `--vary-action-label-positions-by=[all\|player\|level]` | Apply vary logic to all nodes (default: `all`), or selectively to specific players (`player`) or tree levels (`level`). |
| | `--vary-action-label-positions-choices=X,Y` | Comma-separated list of player or level indices to which vary logic applies (used with `--vary-action-label-positions-by=player` or `level`). |
| | `--level-scaling=X.X` | Level spacing multiplier (for `.efg` files, default: 1.0). |
| | `--sublevel-scaling=X.X` | Sublevel spacing multiplier (for `.efg` files, default: 1.0). |
| | `--width-scaling=X.X` | Width spacing multiplier (for `.efg` files, default: 1.0). |
| | `--shared-terminal-depth` | Enforce shared terminal node depth (for `.efg` files). |
| **Label Background** | `--label-bg` | Add a filled background behind all label text to improve readability. |
| | `--label-bg-color=X` | Colour of the label background (named xcolor colour or `#RRGGBB`, default: `white`). |
| | `--label-bg-opacity=X.X` | Opacity of the label background (0.0-1.0, default: 0.8). |
| **Information Sets**| `--iset-fill` | Fill information sets with player colors. |
| | `--iset-fill-opacity=X.X` | Opacity of information set fill (0.0-1.0, default: 0.2). |
| | `--iset-boundary=X` | Boundary style: `solid`, `dotted`, `none` (default: `solid`). |
| **Aesthetics** | `--color-scheme=X` | Set color scheme (`default`, `gambit`, `distinctipy`, `colorblind`, `custom`). |
| | `--edge-thickness=X.X` | Set thickness of edges (default: 1.0). |
| | `--font=[serif\|sans-serif\|monospace]`| Set the global LaTeX font family. |
| | `--font-size=[small\|normalsize\|large\|Large]`| Set the LaTeX font size command. |
| | `--bold`, `--italic` | Use bold or italic text for labels and payoffs. |
| | `--custom-colors="0:#HEX,..."` | Map player indices (0=chance) to hex colors. |
| | `--node-size=X.X` | Size of player nodes in mm (default: 1.5). |
| | `grid` | Show helper grid in the background. |
| **Conversion** | `--to-efg` | Convert `.ef` file to Gambit `.efg` format (no rendering). |
| | `--to-ef` | Convert `.efg` file to `.ef` format (requires pygambit, no rendering). |


## Format Conversion

The CLI also supports converting between `.ef` and `.efg` formats without rendering:

```bash
# Convert EF to Gambit EFG
draw_tree games/example.ef --to-efg

# Convert EFG to EF
draw_tree games/efg/example.efg --to-ef

# Specify output filename
draw_tree games/example.ef --to-efg --output=my_game.efg
```

## Normal Form Games (NFG)

`.nfg` files are supported directly. The default output (no format flag) prints the raw `\begin{game}...\end{game}` LaTeX body; PDF/PNG/SVG compilation requires `pdflatex` and the `sgame` package (`texlive-games`).

```bash
# Print \begin{game}...\end{game} body to stdout
draw_tree games/nfg/example.nfg

# Compile payoff table to PDF
draw_tree games/nfg/example.nfg --pdf

# Compile payoff table to PNG
draw_tree games/nfg/example.nfg --png

# Compile payoff table to SVG with custom output name
draw_tree games/nfg/example.nfg --svg --output=battle_of_sexes.svg
```