#!/usr/bin/env python3
"""
Command-line interface for draw_tree package.
"""
import sys
from pathlib import Path
from .core import (
    commandline, draw_tree, generate_pdf, generate_png, generate_svg, generate_tex
)


def main():
    """Main entry point for the draw_tree CLI."""
    # Display help if no arguments provided
    if len(sys.argv) == 1:
        print("DrawTree - Game tree drawing tool")
        print()
        print("Usage:")
        print("  draw_tree <file.ef> [options]           # Generate TikZ code")
        print("  draw_tree <file.ef> --pdf [options]     # Generate PDF (requires pdflatex)")
        print("  draw_tree <file.ef> --png [options]     # Generate PNG (requires pdflatex + imagemagick/ghostscript)")
        print("  draw_tree <file.ef> --svg [options]     # Generate SVG (requires pdflatex + pdf2svg)")
        print("  draw_tree <file.ef> --tex [options]     # Generate LaTeX document")
        print("  draw_tree <file.ef> --output=name.ext   # Generate with custom filename (.pdf, .png, .svg, or .tex)")
        print("  draw_tree --gui                         # Launch interactive GUI (requires streamlit)")
        print()
        print("Options:")
        print("  scale=X.X    Set scale factor (0.01 to 100)")
        print("  grid         Show helper grid")
        print("  --pdf        Generate PDF output instead of TikZ")
        print("  --png        Generate PNG output instead of TikZ")
        print("  --svg        Generate SVG output instead of TikZ")
        print("  --tex        Generate LaTeX document instead of TikZ")
        print("  --output=X   Specify output filename (.pdf, .png, .svg, or .tex extension determines format)")
        print("  --dpi=X      Set PNG resolution in DPI (72-2400, default: 300)")
        print("  --font=X     Set font family (serif, sans-serif, monospace)")
        print("  --bold       Use bold text")
        print("  --italic     Use italic text")
        print("  --font-size=X Set font size (small, normalsize, large, Large)")
        print("  --custom-colors=X Set custom colors (e.g. \"0:#FF0000,1:#0000FF\")")
        print("  --horizontal Use horizontal layout (growing left-to-right)")
        print()
        print("Examples:")
        print("  draw_tree games/example.ef --pdf")
        print("  draw_tree games/example.ef --png --dpi=600")
        print("  draw_tree games/example.ef --tex")
        print("  draw_tree games/example.ef --output=mygame.tex scale=0.8")
        print("  draw_tree games/example.ef --pdf --font=sans-serif --bold")
        print("  draw_tree games/example.ef --png --custom-colors=\"0:#FF0000,1:#0000FF\"")
        print()
        print("Note: PDF/PNG/SVG generation requires pdflatex. PNG also needs ImageMagick or Ghostscript. SVG needs pdf2svg.")
        sys.exit(0)
    
    if "--gui" in sys.argv:
        try:
            import streamlit.web.cli as stcli
            import os
            app_path = os.path.join(os.path.dirname(__file__), "app.py")
            sys.argv = ["streamlit", "run", app_path]
            sys.exit(stcli.main())
        except ImportError:
            print("Error: Streamlit is required for the GUI. Install it with: pip install streamlit")
            sys.exit(1)

    # Process command-line arguments
    (
        output_mode,
        pdf_requested,
        png_requested,
        svg_requested,
        tex_requested,
        output_file,
        dpi,
        font_family,
        font_bold,
        font_italic,
        font_size,
        custom_colors,
        horizontal,
        action_label_dist,
    ) = commandline(sys.argv)
    
    # Import the core module to access global variables after commandline() has set them
    from . import core
    current_ef_file = core.ef_file
    current_scale = core.scale
    current_grid = core.grid
    
    try:
        # Use default PDF filename if none specified
        if output_file is None:
            output_file = Path(current_ef_file).stem
        if output_mode == "pdf":
            if output_file.endswith(".pdf"):
                print(f"Generating PDF: {output_file}")
            else:
                print(f"Generating PDF: {output_file}.pdf")
            pdf_path = generate_pdf(
                game=current_ef_file,
                save_to=output_file,
                scale_factor=current_scale,
                show_grid=current_grid,
                font_family=font_family,
                font_bold=font_bold,
                font_italic=font_italic,
                font_size=font_size,
                custom_colors=custom_colors,
                horizontal=horizontal, action_label_dist=action_label_dist,
            )
            print(f"PDF generated successfully: {pdf_path}")
        
        elif output_mode == "png":
            if output_file.endswith(".png"):
                print(f"Generating PNG: {output_file}")
            else:
                print(f"Generating PNG: {output_file}.png")
            png_path = generate_png(
                game=current_ef_file,
                save_to=output_file,
                scale_factor=current_scale,
                show_grid=current_grid,
                dpi=dpi if dpi is not None else 300,
                font_family=font_family,
                font_bold=font_bold,
                font_italic=font_italic,
                font_size=font_size,
                custom_colors=custom_colors,
                horizontal=horizontal, action_label_dist=action_label_dist,
            )
            print(f"PNG generated successfully: {png_path}")

        elif output_mode == "svg":
            if output_file.endswith(".svg"):
                print(f"Generating SVG: {output_file}")
            else:
                print(f"Generating SVG: {output_file}.svg")
            svg_path = generate_svg(
                game=current_ef_file,
                save_to=output_file,
                scale_factor=current_scale,
                show_grid=current_grid,
                font_family=font_family,
                font_bold=font_bold,
                font_italic=font_italic,
                font_size=font_size,
                custom_colors=custom_colors,
                horizontal=horizontal, action_label_dist=action_label_dist,
            )
            print(f"SVG generated successfully: {svg_path}")

        elif output_mode == "tex":
            if output_file.endswith(".tex"):
                print(f"Generating LaTeX: {output_file}")
            else:
                print(f"Generating LaTeX: {output_file}.tex")
            tex_path = generate_tex(
                game=current_ef_file,
                save_to=output_file,
                scale_factor=current_scale,
                show_grid=current_grid,
                font_family=font_family,
                font_bold=font_bold,
                font_italic=font_italic,
                font_size=font_size,
                custom_colors=custom_colors,
                horizontal=horizontal, action_label_dist=action_label_dist,
            )
            print(f"LaTeX generated successfully: {tex_path}")
        
        else:
            # Generate TikZ code (original behavior)
            tikz_code = draw_tree(
                game=current_ef_file, 
                scale_factor=current_scale, 
                show_grid=current_grid,
                font_family=font_family,
                font_bold=font_bold,
                font_italic=font_italic,
                font_size=font_size,
                custom_colors=custom_colors,
                horizontal=horizontal, action_label_dist=action_label_dist,
            )
            
            # Output the complete TikZ code
            print(tikz_code)
        
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


if __name__ == '__main__':
    main()