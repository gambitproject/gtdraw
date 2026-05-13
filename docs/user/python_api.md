# Python API

You can use `draw_tree` as a Python library to generate game trees programmatically.
When working in a Jupyter Notebook, you should use the `draw_tree` function to display the game tree directly in the notebook output:

```python
from draw_tree import draw_tree
draw_tree('games/example.ef')
```

:::{warning}
Images may not render correctly in notebooks opened in VSCode; we recommend opening notebooks in Jupyter Lab.
:::

To generate other output formats, use the `generate_tex`, `generate_pdf`, `generate_png`, and `generate_svg` functions, all of which (including `draw_tree` above) accept the same keyword arguments (see below).

Example usage:

```python
from draw_tree import generate_tex, generate_pdf, generate_png, generate_svg

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

All `generate_*` functions and the main `draw_tree` function accept a variety of keyword arguments to customize the output.

| Category | Argument | Description |
| :--- | :--- | :--- |
| **Formatting** | `save_to="filename"` | Specify output filename (with or without extension). |
| | `dpi=X` | Set PNG resolution in DPI for `generate_png` (72-2400, default: 300). |
| | `responsive_sizing=True/False` | Make SVG output responsive for `generate_svg` (default: False). |
| **Layout** | `scale_factor=X.X` | Set scale factor (0.01 to 100, default: 1.0). |
| | `horizontal=True/False` | Switch from vertical to horizontal layout (default: False). |
| | `action_label_dist=X.X` | Distance of action labels from the edge (default: 1.0). |
| | `action_label_position=X.X` | Position of action labels along the edge (0.0 to 1.0, default: 0.5). |
| | `level_scaling=X.X` | Level spacing multiplier (for pygambit, default: 1.0). |
| | `sublevel_scaling=X.X` | Sublevel spacing multiplier (for pygambit, default: 1.0). |
| | `width_scaling=X.X` | Width spacing multiplier (for pygambit, default: 1.0). |
| | `shared_terminal_depth=True/False`| Enforce shared terminal node depth (for pygambit, default: False). |
| **Information Sets**| `iset_fill=True/False` | Fill information sets with player colors (default: False). |
| | `iset_fill_opacity=X.X` | Opacity of information set fill (0.0-1.0, default: 0.2). |
| | `iset_boundary="X"` | Boundary style: `"solid"`, `"dotted"`, `"none"` (default: `"solid"`). |
| **Aesthetics** | `color_scheme="X"` | Set color scheme (`"default"`, `"gambit"`, `"distinctipy"`, `"colorblind"`, `"custom"`). |
| | `edge_thickness=X.X` | Set thickness of edges (default: 1.0). |
| | `font_family="X"` | Set the global LaTeX font family (`"rmfamily"`, `"sffamily"`, `"ttfamily"`). |
| | `font_size="X"` | Set the LaTeX font size command (`"small"`, `"normalsize"`, `"large"`, `"Large"`). |
| | `font_bold=True/False`, `font_italic=True/False` | Use bold or italic text for labels and payoffs. |
| | `custom_colors={0: "#HEX",...}` | Map player indices (0=chance) to hex colors. |
| | `node_size=X.X` | Size of player nodes in mm (default: 1.5). |
| | `show_grid=True/False` | Show helper grid in the background (default: False). |


## Interoperability with pygambit

`draw_tree` supports `pygambit` game objects directly. Check out the `pygambit` documentation which contains tutorials that use `draw_tree` to render game trees. In particular, read [Tutorial 4) Creating publication-ready game images](https://gambitproject.readthedocs.io/en/latest/tutorials/04_creating_images.html).

You can pass a `pygambit` game object to the drawing functions:

```python
import pygambit as gbt
from draw_tree import draw_tree, generate_tex, generate_pdf, generate_png, generate_svg

g = gbt.read_efg('somegame.efg')
draw_tree(g)
generate_tex(g)
generate_pdf(g)
generate_png(g)
generate_svg(g)
```

Or pass the path to an `.efg` file directly:

```python
from draw_tree import generate_pdf
generate_pdf('somegame.efg')
```

::: {note}
Without setting the `save_to` parameter, the saved file will be based on the title field of the `pygambit` game object.
:::
