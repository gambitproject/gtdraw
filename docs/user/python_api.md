# Python API

You can use `draw_tree` as a Python library to generate game trees programmatically:

```python
from draw_tree import generate_tex, generate_pdf, generate_png, generate_svg

generate_tex('games/example.ef')                                    # Creates example.tex
generate_tex('games/example.ef', save_to='custom')                  # Creates custom.tex
generate_pdf('games/example.ef')                                    # Creates example.pdf
generate_png('games/example.ef')                                    # Creates example.png
generate_svg('games/example.ef')                                    # Creates example.svg

# Customize outputs programmatically
generate_pdf('games/example.ef', horizontal=True)                   # Horizontal PDF
generate_png('games/example.ef', dpi=600)                           # High-res example.png (72-2400, default: 300)
generate_png('games/example.ef', save_to='mygame', scale_factor=0.8) # mygame.png with 0.8 scaling
```

## Custom Styling Examples

You can use a variety of keywords to style your outputs:

```python
generate_pdf('game.ef', font_family='sffamily', font_bold=True, font_size='large', horizontal=True)
generate_svg('game.efg', color_scheme='custom', custom_colors={0: '#FF0000', 1: '#0000FF'}, iset_fill=True, iset_fill_opacity=0.3)
generate_pdf('game.ef', iset_boundary='dotted', node_size=2.0)
```

## Rendering in Jupyter Notebooks

In a Jupyter notebook, run:

```python
from draw_tree import draw_tree
draw_tree('games/example.ef')
```

> **⚠️ Warning**: Images may not render correctly in notebooks opened in VSCode; we recommend opening notebooks in Jupyter Lab.

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

> **Note**: Without setting the `save_to` parameter, the saved file will be based on the title field of the `pygambit` game object.
