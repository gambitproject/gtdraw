# Installation

Clone the repo and install the package using `pip`:

```bash
git clone https://github.com/gambitproject/draw_tree
cd draw_tree
pip install .
```

## Requirements

- Python 3.10+ (tested on 3.13)
- LaTeX with TikZ (for PDF/PNG/SVG generation)
- (optional) ImageMagick or Ghostscript or Poppler (for PNG generation)
- (optional) `pdf2svg` (for SVG generation)

## Installing LaTeX

Note: PDF, PNG and SVG generation require `pdflatex` to be installed and available in PATH.

- **macOS**:
    - Install [MacTEX](https://www.tug.org/mactex/mactex-download.html)
    - `brew install --cask mactex`
- **Ubuntu**:
    - `sudo apt-get install texlive-full`
- **Windows**: Install [MiKTeX](https://miktex.org/download)

## PNG generation

PNG generation will default to using any of ImageMagick or Ghostscript or Poppler that are installed. If none are installed, try one of the following:

- **macOS**:
    - `brew install imagemagick`
    - `brew install ghostscript`
    - `brew install poppler`
- **Ubuntu**:
    - `sudo apt-get install imagemagick`
    - `sudo apt-get install ghostscript`
    - `sudo apt-get install poppler-utils`
- **Windows**: Install ImageMagick or Ghostscript from their websites

## SVG generation

SVG generation requires `pdf2svg` to be installed and available in PATH.

- **macOS**:
    - `brew install pdf2svg`
- **Ubuntu**:
    - `sudo apt-get install pdf2svg`
- **Windows**: Download binaries from [GitHub](https://github.com/dawbarton/pdf2svg)
