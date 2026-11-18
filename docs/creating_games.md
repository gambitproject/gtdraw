# Creating Games

GTDraw cannot be used to generate games directly. A game is drawn from a text source: a drawing in GTDraw's `.ef` [format](ef_format.md), which includes layout formatting, or the LaTeX body of a strategic game (an `sgame` table) as a `.tex` file. A source is a path or a file-like object; in Python, the kind of a path is its extension (`.ef` or `.tex`) or the `format="ef"` / `format="sgame"` argument, and a text buffer is a drawing unless `format` says otherwise.
`.ef` files can be created via [Game Theory Explorer](https://gametheoryexplorer-a68c7.web.app/), or by hand.

GTDraw does not read Gambit's game files (`.efg`, `.nfg`) and does not depend on `pygambit`. To draw a Gambit game, convert it to a drawing with `pygambit` first, then draw the file; see the Gambit documentation, [Tutorial 4) Creating publication-ready game images](https://gambitproject.readthedocs.io/en/latest/tutorials/04_creating_images.html).

GTDraw serves as a bridge between text descriptions of games and high-quality visualizations. The diagram below illustrates how data flows from various sources through GTDraw to produce publication-ready graphics.

```{mermaid}
flowchart TD
    %% Source Inputs
    GTE["GTE <br/> (Game Theory Explorer)"] --> EF((EF))
    Gambit["Gambit <br/> (pygambit)"] -- "convert to a drawing" --> EF
    SG((sgame .tex))

    subgraph GTDraw
        direction LR

        %% core.py entry point
        EF --> tikz_fn["tikz()"]
        SG --> tikz_fn

        %% Functions that build directly on tikz()
        tikz_fn --> draw_fn["draw()"]
        tikz_fn --> tex_fn["tex()"]
        tikz_fn --> pdf_fn["pdf()"]

        %% Output nodes
        draw_fn --> OUT1["Drawing /<br/>Jupyter display"]
        tex_fn  --> OUT2[LaTeX Doc]
        pdf_fn  --> OUT3[PDF Document]

        %% Functions that build on pdf()
        subgraph raster[ ]
            png_fn["png()"] --> OUT4[PNG Image]
            svg_fn["svg()"] --> OUT5[SVG Image]
        end
        OUT3 --> png_fn
        OUT3 --> svg_fn
    end

    %% Styling
    style GTE fill:#f9f,stroke:#333,stroke-width:2px
    style Gambit fill:#f9f,stroke:#333,stroke-width:2px
    style EF fill:#bbf,stroke:#333,stroke-width:2px
    style SG fill:#bfb,stroke:#333,stroke-width:2px
    style tikz_fn fill:#ffd,stroke:#333
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
    style raster fill:none,stroke:none
```

## Data Flow
1. **Sources**: Games can be designed in **GTE (Game Theory Explorer)**, written by hand, or converted from a Gambit game with `pygambit`.
2. **Formats**:
   - **EF**: The native GTDraw format, optimized for manual layout and TikZ rendering.
   - **sgame**: The LaTeX body of a strategic game table, as a `.tex` file.
3. **Generation**: All drawing functions live in `core.py`. `tikz()` is the foundation: it produces raw TikZ code from the EF data (for an sgame body it returns the body unchanged). `draw()`, `tex()`, and `pdf()` each call `tikz()` internally; `png()` and `svg()` compile with `pdflatex` as `pdf()` does and convert the PDF with `pdftocairo`.

## Strategic Games

GTDraw renders strategic (normal) form games from the LaTeX body of an [`sgame`](https://ctan.org/pkg/sgame) table, given as a `.tex` file (or a buffer with `format="sgame"`): the `\begin{game}...\end{game}` environment, with its payoffs.

For such a source, `tikz()` returns the body unchanged. Rendering to PDF, PNG, or SVG wraps it in a document and compiles it with `pdflatex`, and requires the `sgame` package (provided by `texlive-games` on Ubuntu, or included in full TeX Live / MiKTeX distributions).
