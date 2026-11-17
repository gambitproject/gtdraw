# Python API

You can use `gtdraw` as a Python library to generate game trees programmatically.
When working in a Jupyter Notebook, you should use the `draw` function to display the game tree directly in the notebook output. It returns a `Drawing`, which a notebook shows when it is the last expression of a cell (this needs `pdflatex` and `pdftocairo`; see [Installation](installation.md)):

```python
from gtdraw import draw
draw('games/example.ef')
```

The `Drawing` has two attributes: `.tikz`, the TikZ code, and `.source`, the complete LaTeX document that is compiled to show it. It compiles once, when first displayed.

:::{warning}
Images may not render correctly in notebooks opened in VSCode; we recommend opening notebooks in Jupyter Lab.
:::

To generate other output formats, use the `tex`, `pdf`, `png`, and `svg` functions, all of which (including `draw` above) take the same style (see [Style](#style)).

## Sources

The first argument, `source`, is a path or a file-like object (a text buffer):

```python
import io
from gtdraw import tikz, pdf

tikz("games/example.ef")                          # a path
tikz(io.StringIO(open("games/example.ef").read())) # a text buffer
pdf("games/nau2004_sec3.tex", save_to="table")     # the body of a strategic game
```

The kind of a source is its `format` argument (`"ef"`, a drawing, or `"sgame"`, the LaTeX body of a strategic game), or if there is none, the extension of a path (`.ef` or `.tex`). A text buffer without `format` is a drawing. A string is always a path, never the text of a drawing.

## Style

The look of a drawing is its *style*: the 30 options of `gtdraw.Style`, each with a default and a check of its value. Every output function takes a style in two ways: as a `Style`, and as options by name.

```python
from gtdraw import Style, tex, pdf, png, svg

house = Style(font_family="sffamily", node_size=2.0)

pdf("game.ef", style=house)                       # a Style
pdf("game.ef", font_bold=True, horizontal=True)   # options by name
svg(
    "game.ef",
    style=house,                                  # both: the options win
    color_scheme="custom",
    custom_colors={0: "#FF0000", 1: "#0000FF"},
    iset_fill=True,
)
png("game.ef", iset_boundary="dotted", dpi=600)
```

`Style` is immutable. `style.replace(node_size=3.0)` gives a changed copy, and `Style()` is gtdraw's own look. An unknown option name raises `TypeError`, which lists the valid names, and a value that is not valid for its option raises `ValueError`.

A drawing can also carry its own style, in a [style block](ef_format.md#style-block) of `%` comment lines. Four layers decide each option, and a later one wins:

1. the default in `Style()`;
2. the `style` argument;
3. the drawing's style block;
4. options passed by name.

So a house style passed as `style=` gives way to what a drawing says about itself, and an option typed in the call has the last word. `Style.from_block(text)` reads a block and `style.to_block()` writes one (`to_block(base)` writes only what differs from `base`).

## Arguments

All output format functions (`draw`, `tikz`, `tex`, `pdf`, `png`, `svg`) take the arguments below, then the style options.

| Argument | Description |
| :--- | :--- |
| `source` | A path or a file-like object (see [Sources](#sources)). |
| `save_to="filename"` | The output filename (with or without extension), for `tex`, `pdf`, `png` and `svg`. Default: the path's stem, or `drawing` for a buffer. |
| `format="ef"` or `"sgame"` | The kind of the source; overrides the extension of a path (see [Sources](#sources)). |
| `style=Style(...)` | The style to draw with; see [Style](#style). |
| `dpi=X` | PNG resolution in DPI, for `png` (default: 300). |
| `responsive_sizing=True/False` | Make SVG output responsive, for `svg` (default: False). |

## Style options

These are the fields of `Style`, and the options by name of every output function. The style block uses the same names.

| Category | Option | Description |
| :--- | :--- | :--- |
| **Layout** | `scale_factor=X.X` | Set scale factor (0.01 to 100, default: 1.0). |
| | `horizontal=True/False` | Switch from vertical to horizontal layout (default: False). |
| | `mirror=True/False` | Mirror the tree left-to-right by flipping xshift values (default: False). |
| | `legend_position="X"` | Corner for the colour legend: `"top-left"` (default), `"top-right"`, `"bottom-left"`, `"bottom-right"`. |
| | `action_label_dist=X.X` | Distance of action labels from the edge (default: 1.0). |
| | `action_label_position=X` | Position of action labels along the edge. Accepts a single float (0.0 to 1.0, default: 0.5), a dictionary keyed by player index (e.g. `{0: 0.3, 1: 0.7}`), or a dictionary keyed by level index (e.g. `{0: 0.3, 1: 0.6}`). |
| | `action_label_position_by=\"X\"` | Interpret a dictionary `action_label_position` as keyed by player index (`"player"`, default) or by tree level index (`"level"`). |
| | `vary_action_label_positions=True/False`| Vary action label positions along child edges of a node to avoid clashes (default: False). |
| | `vary_action_label_positions_by=\"X\"` | Apply vary logic to `"all"` nodes (default), or selectively to specific `"player"` or `"level"` indices. |
| | `vary_action_label_positions_choices=[...]` | List of player or level indices to apply vary logic to (used with `vary_action_label_positions_by="player"` or `"level"`). `None` means all (default). |
| **Information Sets**| `iset_fill=True/False` | Fill information sets with player colors (default: False). |
| | `iset_fill_opacity=X.X` | Opacity of information set fill (0.0-1.0, default: 0.2). |
| | `iset_boundary="X"` | Boundary style: `"solid"`, `"dotted"`, `"none"` (default: `"solid"`). |
| | `iset_curved=True/False` | Draw information sets as curved ovals using a TikZ `to[bend left]` open path with double-stroke ribbon style instead of arc-segment loops (default: False). |
| | `iset_curved_bend=X.X` | Bend angle in degrees (-90 to 90, default: 10.0). Also accepts `dict[int, float]` keyed by player or level index. |
| | `iset_curved_bend_by="X"` | Interpret a dict `iset_curved_bend` as keyed by player index (`"player"`, default) or level index (`"level"`). |
| **Label Background** | `label_bg=True/False` | Add a filled background behind all label text to improve readability. Also accepts a `dict[int, bool]` to enable per-player or per-level (use with `label_bg_by`, default: False). |
| | `label_bg_by="X"` | Interpret a dictionary `label_bg` as keyed by player index (`"player"`, default) or by tree level index (`"level"`). |
| | `label_bg_style="X"` | Background style: `"player_bg"` (player-colour background with white text, default) or `"white_bg"` (white background with player-colour text). |
| | `label_bg_color="X"` | Fallback colour of the label background when no player colour applies. Accepts any named xcolor colour (e.g. `"white"`) or a hex string (e.g. `"#ffcc00"`) (default: `"white"`). |
| | `label_bg_opacity=X.X` | Opacity of the label background (0.0-1.0, default: 0.8). |
| **Aesthetics** | `color_scheme="X"` | Set color scheme (`"default"`, `"gambit"`, `"distinctipy"`, `"colorblind"`, `"custom"`). |
| | `edge_thickness=X.X` | Set thickness of edges (default: 1.0). |
| | `font_family="X"` | Set the global LaTeX font family (`"rmfamily"`, `"sffamily"`, `"ttfamily"`). |
| | `font_size="X"` | Set the LaTeX font size command: `"tiny"`, `"scriptsize"`, `"footnotesize"`, `"small"`, `"normalsize"` (default), `"large"`, `"Large"`, `"LARGE"`, `"huge"`, `"Huge"`. |
| | `font_bold=True/False`, `font_italic=True/False` | Use bold or italic text for labels and payoffs. |
| | `custom_colors={0: "#HEX",...}` | Map player indices (0=chance) to hex colors. |
| | `node_size=X.X` | Size of player nodes in mm (default: 1.5). |
| | `show_grid=True/False` | Show helper grid in the background (default: False). |


## Drawing a Gambit game

`gtdraw` does not read Gambit's game files and does not depend on `pygambit`. To draw a game made or read with `pygambit`, convert it to a drawing with `pygambit` first, then draw the file. Check out the `pygambit` documentation, which contains tutorials that use `gtdraw` to render game trees. In particular, read [Tutorial 4) Creating publication-ready game images](https://gambitproject.readthedocs.io/en/latest/tutorials/04_creating_images.html).

## Strategic Games

The LaTeX body of a strategic game (a `\begin{game}...\end{game}` table for the [`sgame`](https://ctan.org/pkg/sgame) package) is a source of kind `"sgame"`:

```python
from gtdraw import draw, tikz, pdf, png, svg

# From a .tex file
body = tikz("games/nau2004_sec3.tex")   # the body, unchanged
pdf("games/nau2004_sec3.tex", save_to="battle_of_sexes.pdf")   # compiles the payoff table to PDF
png("games/nau2004_sec3.tex")   # compiles the payoff table to PNG
svg("games/nau2004_sec3.tex")   # compiles the payoff table to SVG

# From a buffer
import io
pdf(io.StringIO(body), format="sgame", save_to="table")
```

`tikz()` on a strategic game returns the `\begin{game}...\end{game}` LaTeX body (not TikZ code), and `draw()` returns a `Drawing` whose `.tikz` is that body. PDF/PNG/SVG compilation requires `pdflatex` and the `sgame` LaTeX package (`texlive-games` on Ubuntu).

Style options (`horizontal`, `mirror`, `iset_fill`, `scale_factor`, etc.) and `style` are accepted but silently ignored for strategic games.
