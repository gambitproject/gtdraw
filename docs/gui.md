# Interactive GUI

`draw_tree` includes a lightweight, interactive GUI built with Streamlit. It allows you to upload `.ef` or `.efg` files and adjust drawing parameters in real-time, previewing changes visually.

:::{card} 🚀 Try DrawTree Online!
:link: https://drawtree.streamlit.app/

**Visualize your game trees instantly.** No installation required.

[![Launch GUI](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://drawtree.streamlit.app/)

+++
[Launch interactive tool →](https://drawtree.streamlit.app/)
:::


To launch the GUI from your terminal, simply run:

```bash
draw_tree --gui
```

This will start a local Streamlit server and automatically open the application in your default web browser at `http://localhost:8501/`. From there, you can:
- Upload game files
- Tinker with formatting options (e.g., node size, layouts, colors)
- Download the resulting Tex, SVG, PDF, or PNG images.

```{image} ../../img/gui_screenshot.png
:alt: GUI screenshot
```