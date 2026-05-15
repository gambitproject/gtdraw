# Creating Games

DrawTree cannot be used to generate games directly. Games can be specified via `.ef` [format](ef_format.md) files which include layout formatting, or via Gambit's `.efg` [format](https://gambitproject.readthedocs.io/en/stable/formats.efg.html) files (requires `pygambit`).
`.ef` files can be created via [Game Theory Explorer](https://gametheoryexplorer-a68c7.web.app/), or by hand.

Games can alternatively be specified via `pygambit` game objects; see the [Python API](python_api.md) section for details, or read the tutorial in the Gambit documentation: [Tutorial 4) Creating publication-ready game images](https://gambitproject.readthedocs.io/en/latest/tutorials/04_creating_images.html).

DrawTree serves as a bridge between game theory file formats and high-quality visualizations. The diagram below illustrates how data flows from various sources through DrawTree to produce publication-ready graphics.

```{mermaid}
flowchart TD
    %% Source Inputs
    GTE["GTE <br/> (Game Theory Explorer)"] --> EF((EF))
    Gambit["Gambit <br/> (PyGambit, GUI, CLI)"] --> EFG((EFG))

    subgraph DrawTree
        direction TB
        
        %% Conversion Layer
        EF <--> |"converter.py <br/> (ef_to_efg / efg_to_ef)"| EFG
        
        %% Processing Layer
        EF --> |"core.py"| Gen[Generate]
        EFG --> |"gambit_layout.py <br/> (to EF)"| Gen
        
        %% Output Layer
        Gen --> |"generate_tikz()"| TikZ[TikZ Code]
        Gen --> |"generate_tex()"| TeX[LaTeX Doc]
        Gen --> |"generate_svg()"| SVG[SVG Image]
        Gen --> |"generate_png()"| PNG[PNG Image]
        Gen --> |"generate_pdf()"| PDF[PDF Document]
    end

    %% Styling
    style GTE fill:#f9f,stroke:#333,stroke-width:2px
    style Gambit fill:#f9f,stroke:#333,stroke-width:2px
    style EF fill:#bbf,stroke:#333,stroke-width:2px
    style EFG fill:#bfb,stroke:#333,stroke-width:2px
    style Gen fill:#f96,stroke:#333,stroke-width:2px
    style DrawTree fill:#fff,stroke:#333,stroke-dasharray: 5 5
    style TikZ fill:#eee,stroke:#333
    style TeX fill:#eee,stroke:#333
    style SVG fill:#eee,stroke:#333
    style PNG fill:#eee,stroke:#333
    style PDF fill:#eee,stroke:#333
```

## Data Flow
1. **Sources**: Games can be designed in **GTE (Game Theory Explorer)** or managed via the **Gambit** suite (PyGambit, GUI, or CLI).
2. **Formats**: 
   - **EF**: The native DrawTree format, optimized for manual layout and TikZ rendering.
   - **EFG**: The standard Gambit format.
3. **Conversion**: The `converter.py` module provides robust two-way conversion between EF and EFG formats to ensure compatibility between different tools.
4. **Generation**: DrawTree can natively ingest **either EF or EFG** files to generate output. 
   - **EFG files** are internally converted to an EF representation via `gambit_layout.py`.
   - **Generation functions** in `core.py` then process the EF data to produce multiple formats including **TikZ**, **TeX**, **SVG**, **PNG**, and **PDF**.
