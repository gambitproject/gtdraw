# Creating Games

DrawTree cannot be used to generate games directly. Games can be specified via `.ef` [format](ef_format.md) files which include layout formatting, or via Gambit's `.efg` [format](https://gambitproject.readthedocs.io/en/stable/formats.efg.html) files (requires `pygambit`).
`.ef` files can be created via [Game Theory Explorer](https://gametheoryexplorer-a68c7.web.app/), or by hand.

Games can alternatively be specified via `pygambit` game objects; see the [Python API](python_api.md) section for details, or read the tutorial in the Gambit documentation: [Tutorial 4) Creating publication-ready game images](https://gambitproject.readthedocs.io/en/latest/tutorials/04_creating_images.html).

DrawTree also supports **Normal Form Games** (`.nfg` files) — see the [NFG section](#normal-form-games-nfg) below.

DrawTree serves as a bridge between game theory file formats and high-quality visualizations. The diagram below illustrates how data flows from various sources through DrawTree to produce publication-ready graphics.

```{mermaid}
flowchart TD
    %% Source Inputs
    GTE["GTE <br/> (Game Theory Explorer)"] --> EF((EF))
    Gambit["Gambit <br/> (PyGambit, GUI, CLI)"] --> EFG((EFG))
    Gambit --> NFG((NFG))

    subgraph DrawTree
        direction TB
        
        %% Conversion Layer
        EF <--> |"converter.py <br/> (ef_to_efg / efg_to_ef)"| EFG
        
        %% Processing Layer
        EF --> |"core.py"| Gen[Generate]
        EFG --> |"gambit_layout.py <br/> (to EF)"| Gen
        NFG --> |"game.to_latex()"| GenNFG[Generate NFG]
        
        %% Output Layer
        Gen --> |"generate_tikz()"| TikZ[TikZ Code]
        Gen --> |"generate_tex()"| TeX[LaTeX Doc]
        Gen --> |"generate_svg()"| SVG[SVG Image]
        Gen --> |"generate_png()"| PNG[PNG Image]
        Gen --> |"generate_pdf()"| PDF[PDF Document]
        GenNFG --> |"generate_tikz()"| GameEnv["\\begin{game} body"]
        GenNFG --> |"generate_tex()"| TeXNFG[LaTeX Doc]
        GenNFG --> |"generate_pdf/png/svg()"| ImgNFG[Image]
    end

    %% Styling
    style GTE fill:#f9f,stroke:#333,stroke-width:2px
    style Gambit fill:#f9f,stroke:#333,stroke-width:2px
    style EF fill:#bbf,stroke:#333,stroke-width:2px
    style EFG fill:#bfb,stroke:#333,stroke-width:2px
    style NFG fill:#fdb,stroke:#333,stroke-width:2px
    style Gen fill:#f96,stroke:#333,stroke-width:2px
    style GenNFG fill:#f96,stroke:#333,stroke-width:2px
    style DrawTree fill:#fff,stroke:#333,stroke-dasharray: 5 5
    style TikZ fill:#eee,stroke:#333
    style TeX fill:#eee,stroke:#333
    style SVG fill:#eee,stroke:#333
    style PNG fill:#eee,stroke:#333
    style PDF fill:#eee,stroke:#333
    style GameEnv fill:#eee,stroke:#333
    style TeXNFG fill:#eee,stroke:#333
    style ImgNFG fill:#eee,stroke:#333
```

## Data Flow
1. **Sources**: Games can be designed in **GTE (Game Theory Explorer)** or managed via the **Gambit** suite (PyGambit, GUI, or CLI).
2. **Formats**: 
   - **EF**: The native DrawTree format, optimized for manual layout and TikZ rendering.
   - **EFG**: The standard Gambit extensive form format.
   - **NFG**: Gambit's normal form (strategic form) format.
3. **Conversion**: The `converter.py` module provides robust two-way conversion between EF and EFG formats to ensure compatibility between different tools.
4. **Generation**: DrawTree can natively ingest **EF, EFG, or NFG** files to generate output.
   - **EFG files** are internally converted to an EF representation via `gambit_layout.py`.
   - **NFG files** are rendered via pygambit's `game.to_latex()`, which produces a payoff table using the LaTeX `sgame` package.
   - **Generation functions** in `core.py` then produce multiple formats including **TikZ/game body**, **TeX**, **SVG**, **PNG**, and **PDF**.

## Normal Form Games (NFG)

DrawTree renders normal form (strategic form) games from Gambit's `.nfg` file format or from `pygambit` NFG game objects.

### How it works

For NFG inputs, `generate_tikz()` returns the raw `\begin{game}...\end{game}` LaTeX body produced by pygambit's `game.to_latex()`. This uses the [`sgame`](https://ctan.org/pkg/sgame) LaTeX package to typeset the payoff matrix.

Rendering to PDF, PNG, or SVG compiles this LaTeX body with `pdflatex` and requires the `sgame` package (provided by `texlive-games` on Ubuntu, or included in full TeX Live / MiKTeX distributions).

### Example output

A 2-player game produces a table like:

```latex
\begin{game}{2}{2}[Row][Column]
&Left & Right\\
Top &  $3,2$  &  $0,0$ \\
Bottom &  $0,0$  &  $2,3$ 
\end{game}
```

For games with more than 2 players, multiple tables are concatenated (one per strategy profile of the remaining players).

### Notes

- Tree-specific parameters (`horizontal`, `mirror`, `scale_factor`, `iset_fill`, etc.) are not applicable to NFG inputs and are silently ignored.
- See the [Python API](python_api.md) and [CLI](cli.md) documentation for usage examples.
