# Welcome to DrawTree

*Part of the [Gambit project](https://www.gambit-project.org/).*

DrawTree is a game tree drawing tool for publication-ready extensive form games in Game Theory.
It can generate TikZ code, LaTeX documents, PDFs, PNGs, and SVGs from game specifications.

Games can be specified via `.ef` [format](user/ef_format.md) files which include layout formatting, or via Gambit's `.efg` [format](https://gambitproject.readthedocs.io/en/stable/formats.efg.html) files (requires `pygambit`).
`.ef` files can be created via [Game Theory Explorer](https://gametheoryexplorer-a68c7.web.app/), or by hand.

Games can alternatively be specified via `pygambit` game objects; see the [Python API](user/python_api.md) section for details, or read the tutorial in the Gambit documentation: [Tutorial 4) Creating publication-ready game images](https://gambitproject.readthedocs.io/en/latest/tutorials/04_creating_images.html).

> DrawTree was originally developed by [Bernhard von Stengel](https://www.lse.ac.uk/people/bernhard-von-stengel) at the London School of Economics. It is being developed further as part of the [Gambit project](https://www.gambit-project.org) out of The Alan Turing Institute.

```{image} ../img/Stripped-down_poker_(Reiley_et_al_2008).svg
:alt: Poker example
```

```{tableofcontents}
```
