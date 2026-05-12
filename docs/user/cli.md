# Command Line Interface (CLI)

By default, `draw_tree` generates TikZ code and prints it to standard output.
There are also options to generate a complete LaTeX document, a PDF or a PNG directly, either by specifying the desired format or by using the output filename extension:

```bash
draw_tree games/example.ef                                 # Prints TikZ code to stdout
draw_tree games/example.efg                                # Also works with .efg files!
draw_tree games/example.ef --tex                           # Creates example.tex
draw_tree games/example.ef --output=custom.tex             # Creates custom.tex
draw_tree games/example.ef --pdf                           # Creates example.pdf
draw_tree games/example.ef --png                           # Creates example.png
draw_tree games/example.ef --svg                           # Creates example.svg
draw_tree games/example.ef --png --dpi=600                 # Creates high-res example.png (72-2400, default: 300)
draw_tree games/example.ef --output=mygame.png scale=0.8   # Creates mygame.png with 0.8 scaling (0.01 to 100)
draw_tree games/example.ef --pdf --font=sans-serif --bold  # Sans-serif bold font
draw_tree games/example.ef --png --font-size=large         # Larger text size
draw_tree games/example.ef --pdf --horizontal              # Horizontal layout (left-to-right)
draw_tree games/example.efg --svg --custom-colors="0:#FF0000,1:#0000FF" # Custom player colors
```

## Formatting Options

| Option | CLI Flag | Description |
| :--- | :--- | :--- |
| **Layout** | `--horizontal` | Switch between vertical (top-down) and horizontal (left-right) layout. |
| **Label Dist** | `--action-label-dist=X.X` | Distance of action labels from the edge (default: 1.0). |
| **Font Family** | `--font=[serif\|sans-serif\|monospace]` | Set the global LaTeX font family. |
| **Font Weight** | `--bold` | Use bold text for labels and payoffs. |
| **Font Style** | `--italic` | Use italic text for labels and payoffs. |
| **Font Size** | `--font-size=[small\|normalsize\|large\|Large]` | Set the LaTeX font size command. |
| **Colors** | `--custom-colors="0:#HEX,..."` | Map player indices (0=chance) to hex colors. |
| **Info Sets** | `--iset-fill` | Fill information sets with player colors. |
| **Iset Opacity**| `--iset-fill-opacity=X.X` | Opacity of the information set fill (default: 0.2). |
| **Iset Boundary** | `--iset-boundary=[solid\|dotted\|none]` | Set information set boundary style (default: solid). |
| **Node Size** | `--node-size=X.X` | Set size of player nodes in mm (default: 1.5). |
