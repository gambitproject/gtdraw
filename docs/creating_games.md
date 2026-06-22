# Creating Games

GTDraw cannot be used to generate games directly. Games can be specified via `.ef` [format](ef_format.md) files which include layout formatting, or via Gambit's `.efg` [format](https://gambitproject.readthedocs.io/en/stable/formats.efg.html) files (requires `pygambit`).
`.ef` files can be created via [Game Theory Explorer](https://gametheoryexplorer-a68c7.web.app/), or by hand.

Games can alternatively be specified via `pygambit` game objects; see the [Python API](python_api.md) section for details, or read the tutorial in the Gambit documentation: [Tutorial 4) Creating publication-ready game images](https://gambitproject.readthedocs.io/en/latest/tutorials/04_creating_images.html).

GTDraw also supports **Normal Form Games** (`.nfg` files) — see the [NFG section](#normal-form-games-nfg) below.

GTDraw serves as a bridge between game theory file formats and high-quality visualizations. The diagram below illustrates how data flows from various sources through GTDraw to produce publication-ready graphics.

```{mermaid}
flowchart TD
    %% Source Inputs
    GTE["GTE <br/> (Game Theory Explorer)"] --> EF((EF))
    Gambit["Gambit <br/> (PyGambit, GUI, CLI)"] --> EFG((EFG))

    subgraph GTDraw
        direction TB

        %% Conversion Layer
        EF <--> |"converter.py <br/> (ef_to_efg / efg_to_ef)"| EFG

        %% core.py entry point
        EF --> |"core.py"| tikz_fn["tikz()"]
        EFG --> |"gambit_layout.py <br/> (to EF)"| tikz_fn

        %% Functions that build directly on tikz()
        tikz_fn --> draw_fn["draw()"]
        tikz_fn --> tex_fn["tex()"]
        tikz_fn --> pdf_fn["pdf()"]

        %% Functions that build on pdf()
        pdf_fn --> png_fn["png()"]
        pdf_fn --> svg_fn["svg()"]

        %% Output nodes
        draw_fn --> OUT1["TikZ Code /<br/>Jupyter display"]
        tex_fn  --> OUT2[LaTeX Doc]
        pdf_fn  --> OUT3[PDF Document]
        png_fn  --> OUT4[PNG Image]
        svg_fn  --> OUT5[SVG Image]
    end

    %% Styling
    style GTE fill:#f9f,stroke:#333,stroke-width:2px
    style Gambit fill:#f9f,stroke:#333,stroke-width:2px
    style EF fill:#bbf,stroke:#333,stroke-width:2px
    style EFG fill:#bfb,stroke:#333,stroke-width:2px
    style tikz_fn fill:#f96,stroke:#333,stroke-width:2px
    style draw_fn fill:#ffd,stroke:#333
    style tex_fn fill:#ffd,stroke:#333
    style pdf_fn fill:#ffd,stroke:#333
    style png_fn fill:#ffd,stroke:#333
    style svg_fn fill:#ffd,stroke:#333
    style GTDraw fill:#fff,stroke:#333,stroke-dasharray: 5 5
    style OUT1 fill:#eee,stroke:#333
    style OUT2 fill:#eee,stroke:#333
    style OUT3 fill:#eee,stroke:#333
    style OUT4 fill:#eee,stroke:#333
    style OUT5 fill:#eee,stroke:#333
```

## Data Flow
1. **Sources**: Games can be designed in **GTE (Game Theory Explorer)** or managed via the **Gambit** suite (PyGambit, GUI, or CLI).
2. **Formats**: 
   - **EF**: The native GTDraw format, optimized for manual layout and TikZ rendering.
   - **EFG**: The standard Gambit format.
3. **Conversion**: The `converter.py` module provides robust two-way conversion between EF and EFG formats to ensure compatibility between different tools.
4. **Generation**: GTDraw can natively ingest **either EF or EFG** files to generate output.
   - **EFG files** are internally converted to an EF representation via `gambit_layout.py`.
   - All drawing functions live in `core.py`. `tikz()` is the foundation — it produces raw TikZ code from the EF data. `draw()`, `tex()`, and `pdf()` each call `tikz()` internally; `png()` and `svg()` build on `pdf()`.

## Normal Form Games (NFG)

GTDraw renders normal form (strategic form) games from Gambit's `.nfg` file format or from `pygambit` NFG game objects.

For NFG inputs, `tikz()` returns the raw `\begin{game}...\end{game}` LaTeX body produced by pygambit's `game.to_latex()`. This uses the [`sgame`](https://ctan.org/pkg/sgame) LaTeX package to typeset the payoff matrix.

Rendering to PDF, PNG, or SVG compiles this LaTeX body with `pdflatex` and requires the `sgame` package (provided by `texlive-games` on Ubuntu, or included in full TeX Live / MiKTeX distributions).

