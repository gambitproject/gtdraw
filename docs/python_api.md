# Python API

You can use `gtdraw` as a Python library to generate game trees programmatically.
When working in a Jupyter Notebook, you should use the `gtdraw` function to display the game tree directly in the notebook output:

```python
from gtdraw import gtdraw
gtdraw('games/example.ef')
```

:::{warning}
Images may not render correctly in notebooks opened in VSCode; we recommend opening notebooks in Jupyter Lab.
:::

To generate other output formats, use the `generate_tex`, `generate_pdf`, `generate_png`, and `generate_svg` functions, all of which (including `gtdraw` above) accept the same keyword arguments (see below).

Example usage:

```python
from gtdraw import generate_tex, generate_pdf, generate_png, generate_svg

generate_pdf(
    "game.ef",
    font_family="sffamily",
    font_bold=True,
    font_size="large",
    horizontal=True,
)
generate_svg(
    "game.efg",
    color_scheme="custom",
    custom_colors={0: "#FF0000", 1: "#0000FF"},
    iset_fill=True,
    iset_fill_opacity=0.3,
)
generate_png(
    "game.ef",
    iset_boundary="dotted",
    node_size=2.0,
)
```

## API Keyword Arguments

All `generate_*` functions and the main `gtdraw` function accept a variety of keyword arguments to customize the output.

| Category | Argument | Description |
| :--- | :--- | :--- |
| **Formatting** | `save_to="filename"` | Specify output filename (with or without extension). |
| | `dpi=X` | Set PNG resolution in DPI for `generate_png` (72-2400, default: 300). |
| | `responsive_sizing=True/False` | Make SVG output responsive for `generate_svg` (default: False). |
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
| | `level_scaling=X.X` | Level spacing multiplier (for pygambit, default: 1.0). |
| | `sublevel_scaling=X.X` | Sublevel spacing multiplier (for pygambit, default: 1.0). |
| | `width_scaling=X.X` | Width spacing multiplier (for pygambit, default: 1.0). |
| | `shared_terminal_depth=True/False`| Enforce shared terminal node depth (for pygambit, default: False). |
| **Information Sets**| `iset_fill=True/False` | Fill information sets with player colors (default: False). |
| | `iset_fill_opacity=X.X` | Opacity of information set fill (0.0-1.0, default: 0.2). |
| | `iset_boundary="X"` | Boundary style: `"solid"`, `"dotted"`, `"none"` (default: `"solid"`). |
| **Label Background** | `label_bg=True/False` | Add a filled background behind all label text to improve readability. Also accepts a `dict[int, bool]` to enable per-player or per-level (use with `label_bg_by`, default: False). |
| | `label_bg_by="X"` | Interpret a dictionary `label_bg` as keyed by player index (`"player"`, default) or by tree level index (`"level"`). |
| | `label_bg_style="X"` | Background style: `"player_bg"` (player-colour background with white text, default) or `"white_bg"` (white background with player-colour text). |
| | `label_bg_color="X"` | Fallback colour of the label background when no player colour applies. Accepts any named xcolor colour (e.g. `"white"`) or a hex string (e.g. `"#ffcc00"`) (default: `"white"`). |
| | `label_bg_opacity=X.X` | Opacity of the label background (0.0-1.0, default: 0.8). |
| **Aesthetics** | `color_scheme="X"` | Set color scheme (`"default"`, `"gambit"`, `"distinctipy"`, `"colorblind"`, `"custom"`). |
| | `edge_thickness=X.X` | Set thickness of edges (default: 1.0). |
| | `font_family="X"` | Set the global LaTeX font family (`"rmfamily"`, `"sffamily"`, `"ttfamily"`). |
| | `font_size="X"` | Set the LaTeX font size command (`"small"`, `"normalsize"`, `"large"`, `"Large"`). |
| | `font_bold=True/False`, `font_italic=True/False` | Use bold or italic text for labels and payoffs. |
| | `custom_colors={0: "#HEX",...}` | Map player indices (0=chance) to hex colors. |
| | `node_size=X.X` | Size of player nodes in mm (default: 1.5). |
| | `show_grid=True/False` | Show helper grid in the background (default: False). |


## Interoperability with pygambit

`gtdraw` supports `pygambit` game objects directly. Check out the `pygambit` documentation which contains tutorials that use `gtdraw` to render game trees. In particular, read [Tutorial 4) Creating publication-ready game images](https://gambitproject.readthedocs.io/en/latest/tutorials/04_creating_images.html).

You can pass a `pygambit` game object to the drawing functions:

```python
import pygambit as gbt
from gtdraw import gtdraw, generate_tex, generate_pdf, generate_png, generate_svg

g = gbt.read_efg('somegame.efg')
gtdraw(g)
generate_tex(g)
generate_pdf(g)
generate_png(g)
generate_svg(g)
```

Or pass the path to an `.efg` file directly:

```python
from gtdraw import generate_pdf
generate_pdf('somegame.efg')
```

::: {note}
Without setting the `save_to` parameter, the saved file will be based on the title field of the `pygambit` game object.
:::

## Format Conversion

`gtdraw` provides two functions for converting between `.ef` and `.efg` file formats:

```python
from gtdraw import ef_to_efg, efg_to_ef

# Convert EF to Gambit EFG
ef_to_efg("game.ef")
ef_to_efg("game.ef", save_to="output.efg", title="My Game")

# Convert EFG to EF (requires pygambit)
efg_to_ef("game.efg")
efg_to_ef("game.efg", save_to="output.ef", level_scaling=1.5)

# You can also pass a pygambit Game object
import pygambit as gbt
g = gbt.read_efg("game.efg")
efg_to_ef(g, save_to="output.ef")
```

### Conversion Arguments

| Function | Argument | Description |
| :--- | :--- | :--- |
| **`ef_to_efg`** | `game` | Path to the `.ef` file (required). |
| | `save_to="filename"` | Output filename. Defaults to the input filename with `.efg` extension. |
| | `title="My Game"` | Title string for the EFG prologue. Defaults to the input filename stem. |
| **`efg_to_ef`** | `game` | Path to the `.efg` file, or a `pygambit.gambit.Game` object (required). |
| | `save_to="filename"` | Output filename. Defaults to the game title with `.ef` extension. |
| | `level_scaling=X.X` | Level spacing multiplier (default: 1.0). |
| | `sublevel_scaling=X.X` | Sublevel spacing multiplier (default: 1.0). |
| | `width_scaling=X.X` | Width spacing multiplier (default: 1.0). |
| | `shared_terminal_depth=True/False` | Enforce shared terminal node depth (default: False). |

Both functions return the path to the generated output file.

## Normal Form Games (NFG)

`gtdraw` also supports normal form (strategic form) games via pygambit:

```python
import pygambit as gbt
from gtdraw import gtdraw, generate_tex, generate_pdf, generate_png, generate_svg

# From a pygambit NFG object
g = gbt.read_nfg("games/nfg/example.nfg")
gtdraw(g)       # returns \begin{game}...\end{game} body; displays image in Jupyter
generate_pdf(g)    # compiles payoff table to PDF
generate_png(g)    # compiles payoff table to PNG
generate_svg(g)    # compiles payoff table to SVG

# Or directly from the .nfg file path
generate_pdf("games/nfg/example.nfg", save_to="battle_of_sexes.pdf")
```

`generate_tikz()` on an NFG returns the raw `\begin{game}...\end{game}` LaTeX body (not TikZ code). PDF/PNG/SVG compilation requires `pdflatex` and the `sgame` LaTeX package (`texlive-games` on Ubuntu).

Tree-specific keyword arguments (`horizontal`, `mirror`, `iset_fill`, `scale_factor`, etc.) are accepted but silently ignored for NFG inputs.