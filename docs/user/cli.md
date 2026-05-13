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
| | `--action-label-dist=X.X` | Distance of action labels from the edge (default: 1.0). |
| **Information Sets**| `--iset-fill` | Fill information sets with player colors. |
| | `--iset-fill-opacity=X.X` | Opacity of information set fill (0.0-1.0, default: 0.2). |
| | `--iset-boundary=X` | Boundary style: `solid`, `dotted`, `none` (default: `solid`). |
| **Aesthetics** | `--font=[serif\|sans-serif\|monospace]`| Set the global LaTeX font family. |
| | `--font-size=[small\|normalsize\|large\|Large]`| Set the LaTeX font size command. |
| | `--bold`, `--italic` | Use bold or italic text for labels and payoffs. |
| | `--custom-colors="0:#HEX,..."` | Map player indices (0=chance) to hex colors. |
| | `--node-size=X.X` | Size of player nodes in mm (default: 1.5). |
| | `grid` | Show helper grid in the background. |
