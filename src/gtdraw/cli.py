#!/usr/bin/env python3
"""
Command-line interface for GTDraw.
"""

import sys
from pathlib import Path
from .core import (
    commandline,
    pdf,
    png,
    svg,
    tex,
    tikz,
)


def main():
    """Main entry point for the draw CLI."""
    # Display help if no arguments provided
    if len(sys.argv) == 1:
        print("GTDraw - Game tree drawing tool for extensive form games")
        print()
        print("Usage:")
        print("  gtdraw <file.ef> [options]           # Generate TikZ code")
        print(
            "  gtdraw <file.ef> --pdf [options]     # Generate PDF (requires pdflatex)"
        )
        print(
            "  gtdraw <file.ef> --png [options]     # Generate PNG (requires pdflatex + pdftocairo)"
        )
        print(
            "  gtdraw <file.ef> --svg [options]     # Generate SVG (requires pdflatex + pdftocairo)"
        )
        print("  gtdraw <file.ef> --tex [options]     # Generate LaTeX document")
        print(
            "  gtdraw <file.ef> --output=name.ext   # Generate with custom filename (.pdf, .png, .svg, or .tex)"
        )
        print(
            "  gtdraw --gui                         # Launch interactive GUI (requires gtdraw[gui])"
        )
        print()
        print("Options:")
        print("  scale=X.X    Set scale factor (0.01 to 100)")
        print("  grid         Show helper grid")
        print("  --pdf        Generate PDF output instead of TikZ")
        print("  --png        Generate PNG output instead of TikZ")
        print("  --svg        Generate SVG output instead of TikZ")
        print("  --tex        Generate LaTeX document instead of TikZ")
        print(
            "  --output=X   Specify output filename (.pdf, .png, .svg, or .tex extension determines format)"
        )
        print("  --dpi=X      Set PNG resolution in DPI (72-2400, default: 300)")
        print("  --font=X     Set font family (serif, sans-serif, monospace)")
        print("  --bold       Use bold text")
        print("  --italic     Use italic text")
        print("  --font-size=X Set font size (small, normalsize, large, Large)")
        print("  --color-scheme=X Set color scheme (default, gambit, distinctipy, colorblind, custom)")
        print('  --custom-colors=X Set custom colors (e.g. "0:#FF0000,1:#0000FF")')
        print("  --horizontal Use horizontal layout (growing left-to-right)")
        print("  --mirror     Mirror the layout left-to-right (flip xshift values)")
        print("  --legend-position=X Set legend corner (top-left, top-right, bottom-left, bottom-right; default: top-left)")
        print(
            "  --action-label-dist=X Set distance of action labels from edges (default: 1.0)"
        )
        print("  --action-label-position=X Set position of action labels along the edge (0.0 to 1.0, default: 0.5)")
        print("  --vary-action-label-positions Vary action label positions based on outgoing edges")
        print("  --edge-thickness=X Set thickness of edges (default: 1.0)")
        print("  --label-bg   Add a filled background behind all label text")
        print("  --label-bg-color=X Set label background colour (named or #RRGGBB, default: white)")
        print("  --label-bg-opacity=X Set label background opacity (0.0-1.0, default: 0.8)")
        print("  --iset-fill  Fill information sets with player colors")
        print(
            "  --iset-fill-opacity=X Set opacity of information set fill (0.0-1.0, default: 0.2)"
        )
        print(
            "  --iset-boundary=X Set information set boundary style (solid, dotted, none, default: solid)"
        )
        print("  --iset-curved  Draw information sets as curved lines using TikZ 'to[bend left]' paths")
        print(
            "  --iset-curved-bend=X Set bend angle for curved information sets (-90 to 90, default: 10.0)"
        )
        print(
            "  --iset-curved-looseness=X Set looseness of curved information set paths (default: 1.0)"
        )
        print(
            "  --iset-curved-bend-by=[player|level|iset] Key for dict --iset-curved-bend (default: player)"
        )
        print(
            "  --iset-curved-looseness-by=[player|level|iset] Key for dict --iset-curved-looseness (default: player)"
        )
        print(
            "  --iset-curved-double-distance=X.X  Width of the curved information set ribbon in mm (default: 3.0)"
        )
        print("  --node-size=X Set size of player nodes in mm (default: 1.5)")
        print()
        print("Strategic games (the LaTeX body of an sgame table, as a .tex file):")
        print("  gtdraw game.tex                      # Print the \\begin{game}...\\end{game} body")
        print("  gtdraw game.tex --pdf                # Compile the payoff table to PDF (requires sgame)")
        print("  gtdraw game.tex --png                # Compile the payoff table to PNG")
        print()
        print("To draw a Gambit game file (.efg, .nfg), convert it to a drawing with pygambit first.")
        print()
        print("Examples:")
        print("  gtdraw games/example.ef --pdf")
        print("  gtdraw games/example.ef --png --dpi=600")
        print("  gtdraw games/example.ef --tex")
        print("  gtdraw games/example.ef --output=mygame.tex scale=0.8")
        print("  gtdraw games/example.ef --pdf --font=sans-serif --bold")
        print(
            '  gtdraw games/example.ef --png --custom-colors="0:#FF0000,1:#0000FF"'
        )
        print()
        print(
            "Note: PDF/PNG/SVG generation requires pdflatex (TeX Live); PNG and SVG also need pdftocairo (poppler-utils)."
        )
        sys.exit(0)

    if "--gui" in sys.argv:
        try:
            import streamlit.web.cli as stcli
            import os

            app_path = os.path.join(os.path.dirname(__file__), "app.py")
            sys.argv = ["streamlit", "run", app_path]
            sys.exit(stcli.main())
        except ImportError:
            print(
                "Error: Streamlit is required for the GUI. Install it with: pip install 'gtdraw[gui]'"
            )
            sys.exit(1)

    # Process command-line arguments. commandline() returns every option, defaults
    # included, and records in core.cli_given which ones the user gave.
    values = commandline(sys.argv)
    output_mode = values[0]
    output_file = values[5]
    dpi = values[6]

    # Import the core module to access global variables after commandline() has set them
    from . import core

    current_ef_file = core.ef_file

    # Pass only the style options the user gave: the rest is left to Style() and to the
    # style block of the drawing, which a flag overrides, even a flag equal to the default.
    style_names = {
        "font_family": values[7],
        "font_bold": values[8],
        "font_italic": values[9],
        "font_size": values[10],
        "custom_colors": values[11],
        "horizontal": values[12],
        "mirror": values[13],
        "legend_position": values[14],
        "action_label_dist": values[15],
        "iset_fill": values[16],
        "iset_fill_opacity": values[17],
        "iset_boundary": values[18],
        "iset_curved": values[19],
        "iset_curved_bend": values[20],
        "iset_curved_bend_by": values[21],
        "node_size": values[22],
        "label_bg": values[23],
        "label_bg_color": values[24],
        "label_bg_opacity": values[25],
        "label_bg_by": values[26],
        "label_bg_style": values[27],
        "color_scheme": values[28],
        "edge_thickness": values[29],
        "action_label_position": values[30],
        "vary_action_label_positions": values[31],
        "action_label_position_by": values[32],
        "vary_action_label_positions_by": values[33],
        "vary_action_label_positions_choices": values[34],
        "scale_factor": core.scale,
        "show_grid": core.grid,
    }
    options = {k: v for k, v in style_names.items() if k in core.cli_given}

    try:
        # Use default filename if none specified
        if output_file is None:
            output_file = Path(current_ef_file).stem
        if output_mode == "pdf":
            if output_file.endswith(".pdf"):
                print(f"Generating PDF: {output_file}")
            else:
                print(f"Generating PDF: {output_file}.pdf")
            pdf_path = pdf(current_ef_file, save_to=output_file, **options)
            print(f"PDF generated successfully: {pdf_path}")

        elif output_mode == "png":
            if output_file.endswith(".png"):
                print(f"Generating PNG: {output_file}")
            else:
                print(f"Generating PNG: {output_file}.png")
            png_path = png(
                current_ef_file,
                save_to=output_file,
                dpi=dpi if dpi is not None else 300,
                **options,
            )
            print(f"PNG generated successfully: {png_path}")

        elif output_mode == "svg":
            if output_file.endswith(".svg"):
                print(f"Generating SVG: {output_file}")
            else:
                print(f"Generating SVG: {output_file}.svg")
            svg_path = svg(current_ef_file, save_to=output_file, **options)
            print(f"SVG generated successfully: {svg_path}")

        elif output_mode == "tex":
            if output_file.endswith(".tex"):
                print(f"Generating LaTeX: {output_file}")
            else:
                print(f"Generating LaTeX: {output_file}.tex")
            tex_path = tex(current_ef_file, save_to=output_file, **options)
            print(f"LaTeX generated successfully: {tex_path}")

        else:
            # Print the complete TikZ code (tikz() returns the code as a string)
            print(tikz(current_ef_file, **options))

    except FileNotFoundError:
        print(f"Error: Could not find file {current_ef_file}", file=sys.stderr)
        print("Make sure the .ef file exists in the current directory", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing {current_ef_file}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
