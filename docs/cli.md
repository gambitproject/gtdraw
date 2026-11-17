# CLI

By default, `gtdraw` generates TikZ code and prints it to standard output.
There are also options to generate a complete LaTeX document, an SVG, PDF or a PNG directly, either by specifying the desired format or by using the output filename extension:

```bash
gtdraw games/example.ef --pdf
```

:::{note}
The input is a drawing in gtdraw's `.ef` format, or the LaTeX body of a strategic game as a `.tex` file. `gtdraw` does not read Gambit's game files; to draw one, convert it to a drawing with `pygambit` first (see [Creating Games](creating_games.md)).
:::

## Style block

A drawing can carry its own style as a block of `% gtdraw: <option> <value>` lines (see the [style block](ef_format.md#style-block)), and `gtdraw` applies it. An option given on the command line overrides the block, including one equal to the default: `--edge-thickness=1.0` draws with thickness 1.0 whatever the block says. A flag with an invalid value is ignored with a warning and leaves the block's value.

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
| **Label Background** | `--label-bg` | Add a filled background behind all label text. Use `--label-bg=1,2,3` to enable only for specific player or level indices (combine with `--label-bg-by`). |
| | `--label-bg-by=[player\|level]` | Interpret `--label-bg=...` indices as player indices (default: `player`) or tree level indices (`level`). |
| | `--label-bg-style=[player_bg\|white_bg]` | Background style: `player_bg` (player-colour background, white text, default) or `white_bg` (white background, player-colour text). |
| | `--label-bg-color=X` | Fallback colour of the label background (named xcolor colour or `#RRGGBB`, default: `white`). |
| | `--label-bg-opacity=X.X` | Opacity of the label background (0.0-1.0, default: 0.8). |
| **Information Sets**| `--iset-fill` | Fill information sets with player colors. |
| | `--iset-fill-opacity=X.X` | Opacity of information set fill (0.0-1.0, default: 0.2). |
| | `--iset-boundary=X` | Boundary style: `solid`, `dotted`, `none` (default: `solid`). |
| | `--iset-curved` | Draw information sets as curved ovals using a TikZ `to[bend left]` open path with double-stroke ribbon style. |
| | `--iset-curved-bend=X.X` | Bend angle in degrees (-90 to 90, default: 10.0). Also accepts a player/level-keyed dict: `0:5.0,1:20.0`. |
| | `--iset-curved-bend-by=[player\|level]` | Interpret a dict `--iset-curved-bend` as keyed by player index (default) or level index. |
| **Aesthetics** | `--color-scheme=X` | Set color scheme (`default`, `gambit`, `distinctipy`, `colorblind`, `custom`). |
| | `--edge-thickness=X.X` | Set thickness of edges (default: 1.0). |
| | `--font=[serif\|sans-serif\|monospace]`| Set the global LaTeX font family. |
| | `--font-size=[small\|normalsize\|large\|Large]`| Set the LaTeX font size command. |
| | `--bold`, `--italic` | Use bold or italic text for labels and payoffs. |
| | `--custom-colors="0:#HEX,..."` | Map player indices (0=chance) to hex colors. |
| | `--node-size=X.X` | Size of player nodes in mm (default: 1.5). |
| | `grid` | Show helper grid in the background. |


## Strategic Games

A strategic game is the LaTeX body of an [`sgame`](https://ctan.org/pkg/sgame) table (`\begin{game}...\end{game}`) in a `.tex` file. The default output (no format flag) prints that body unchanged; PDF/PNG/SVG compilation wraps it in a document and requires `pdflatex` and the `sgame` package (`texlive-games`).

```bash
# Print \begin{game}...\end{game} body to stdout
gtdraw games/nau2004_sec3.tex

# Compile payoff table to PDF
gtdraw games/nau2004_sec3.tex --pdf

# Compile payoff table to PNG
gtdraw games/nau2004_sec3.tex --png

# Compile payoff table to SVG with custom output name
gtdraw games/nau2004_sec3.tex --svg --output=battle_of_sexes.svg
```
