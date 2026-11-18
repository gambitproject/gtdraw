# Installation

Install GTDraw from PyPI:

```bash
pip install gtdraw
```

To use the interactive GUI, install the optional `gui` extra (`pip install "gtdraw[gui]"`); see [Interactive GUI](gui.md).

See the [developer guide](developer/development.md) for developer installation.

## Requirements

- Python 3.11+
- `pdflatex` with TikZ and the `sgame` package (TeX Live or MiKTeX), for PDF, PNG and SVG generation
- `pdftocairo` (Poppler), for PNG and SVG generation

## Installing LaTeX

To use GTDraw, a working LaTeX installation is required. The below offers the minimal installation that has been tested to work on **Ubuntu**. Other Linux distributions have not been tested and the Mac/Windows options have only been tested with larger full LaTeX installations:

```bash
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-pictures texlive-games
```

For a full distribution on any OS try one of the below:

- **macOS**:
    - Install [MacTEX](https://www.tug.org/mactex/mactex-download.html) or
    - ```
        brew install --cask mactex
        ```
- **Ubuntu**:
    - ```
        sudo apt-get install texlive-full
        ```
- **Windows**: Install [MiKTeX](https://miktex.org/download)

```{note}
PDF, PNG and SVG generation require `pdflatex` to be installed and available in PATH.
```

## PNG and SVG generation

PNG and SVG generation convert the compiled PDF with `pdftocairo`, which is part of Poppler. It must be installed and available in PATH:

- **macOS**:
    - ```
        brew install poppler
        ```
- **Ubuntu**:
    - ```
        sudo apt-get install poppler-utils
        ```
- **Windows**: Install Poppler, for example from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases), and add its `Library/bin` folder to PATH.
