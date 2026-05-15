# Architecture & Workflow

DrawTree serves as a bridge between game theory file formats and high-quality visualizations. The diagram below illustrates how data flows from various sources through DrawTree to produce publication-ready graphics.

```{image} ../img/architecture_diagram.png
:alt: DrawTree Architecture Diagram
:align: center
```

## Data Flow
1. **Sources**: Games can be designed in **GTE (Game Theory Explorer)** or managed via the **Gambit** suite (PyGambit, GUI, or CLI).
2. **Formats**: 
   - **EF**: The native DrawTree format, optimized for manual layout and TikZ rendering.
   - **EFG**: The standard Gambit format.
3. **Conversion**: The `converter.py` module provides robust two-way conversion (`ef_to_efg` and `efg_to_ef`) to ensure compatibility between different tools.
4. **Generation**: Once a game is loaded, the generation engine produces multiple output formats including **TikZ**, **TeX**, **SVG**, **PNG**, and **PDF**.
