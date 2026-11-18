# Interactive GUI

`gtdraw` includes a lightweight, interactive GUI built with Streamlit. It allows you to choose an example or upload a drawing (`.ef`) or a strategic game table (`.tex`), and adjust drawing parameters in real-time, previewing changes visually. You can run the GUI locally or used our hosted version on the Streamlit Community Cloud:

<!-- Note: GTDraw can be deployed to the Streamlit community hub, but on a free tier will not remain live constantly -->
<!-- :::{card} 🚀 Try GTDraw Online!
:link: https://gtdraw.streamlit.app/

**Visualize your game trees instantly.** No installation required.

```{image} ../img/example.svg
:alt: Example
:width: 300px
:align: center
```
::: -->

## Running the GUI locally

The GUI requires the optional `gui` extra:

```bash
pip install "gtdraw[gui]"
```

To launch the GUI from your terminal, run:

```bash
gtdraw --gui
```

This will start a local Streamlit server and automatically open the application in your default web browser at `http://localhost:8501/`. From there, you can:
- Upload drawings (to draw a Gambit game file, convert it to a drawing with `pygambit` first)
- Tinker with formatting options (e.g., node size, layouts, colors, label backgrounds, curved information sets)
- Download the resulting Tex, SVG, PDF, or PNG images, and the drawing itself with its style.

```{image} ../img/gui_screenshot.png
:alt: GUI screenshot
```

## Saving a style with the drawing

A drawing carries its own style in a [style block](ef_format.md#style-block) of `%` comment lines at its top. When you load a drawing, the GUI reads its block and sets the widgets from it; when you load one without a block, the widgets start from the GUI's own defaults. **↺ Reset** returns the widgets to the style the drawing was loaded with.

Clicking **EF** in the **Downloads** pane downloads the drawing with a style block of what you set: the options that differ from the GUI's defaults, which are gtdraw's defaults with the `colorblind` colour scheme. Any block the drawing had is replaced. Load the downloaded file in the GUI to get the same style back.

Elsewhere (the Python API, the command line) a drawing without a `color_scheme` line is drawn with gtdraw's own default scheme, not `colorblind`. To make a drawing look the same everywhere, add `% gtdraw: color_scheme colorblind` to its block.
