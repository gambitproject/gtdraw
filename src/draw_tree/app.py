import streamlit as st
import tempfile
from pathlib import Path
import os
import sys

# Add src to path if running from local dev
sys.path.append(str(Path(__file__).parent.parent))

from draw_tree import generate_svg, generate_tikz, generate_tex, generate_pdf, generate_png

def run_app():
    st.set_page_config(page_title="DrawTree GUI", layout="wide", page_icon="🎨")

    # Sidebar: Title and Input
    st.sidebar.title("🎨 DrawTree")
    st.sidebar.markdown("Interactive Game Tree Drawing")
    
    st.sidebar.header("📂 Input Game")
    
    # Try to find games directory
    base_path = Path(__file__).parent.parent.parent
    example_dir = base_path / "games"
    
    game_source = None
    is_efg = False
    
    if example_dir.exists():
        ef_examples = list(example_dir.glob("*.ef"))
        efg_examples = list((example_dir / "efg").glob("*.efg"))
        all_examples = sorted([f.relative_to(base_path) for f in ef_examples + efg_examples])
        
        example_selection = st.sidebar.selectbox("Select an example", ["None"] + [str(e) for e in all_examples])
        if example_selection != "None":
            game_source = str(base_path / example_selection)
            if game_source.lower().endswith(".efg"):
                is_efg = True
    
    uploaded_file = st.sidebar.file_uploader("Or upload your own .ef or .efg file", type=["ef", "efg"])

    if uploaded_file:
        suffix = f".{uploaded_file.name.split('.')[-1]}"
        if suffix.lower() == ".efg":
            is_efg = True
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            game_source = tmp.name

    # Sidebar: Configuration
    st.sidebar.header("📐 Diagram Options")

    scale_factor = st.sidebar.slider("Overall Scale", 0.0, 1.0, 0.5, 0.05, help="Scale factor for the entire TikZ diagram.")
    
    # Conditional Layout Scaling
    if is_efg:
        st.sidebar.subheader("🕹️ Layout Scaling")
        level_scaling = st.sidebar.slider("Level Scaling", 0.0, 1.0, 0.25, 0.05)
        sublevel_scaling = st.sidebar.slider("Sublevel Scaling", 0.0, 1.0, 0.5, 0.05)
        width_scaling = st.sidebar.slider("Width Scaling", 0.0, 1.0, 0.5, 0.05)
        
        st.sidebar.subheader("⚙️ Layout Flags")
        hide_action_labels = st.sidebar.checkbox("Hide Action Labels", False)
        shared_terminal_depth = st.sidebar.checkbox("Shared Terminal Depth", False)
    else:
        # Defaults for .ef files
        level_scaling = 1.0
        sublevel_scaling = 1.0
        width_scaling = 1.0
        hide_action_labels = False
        shared_terminal_depth = False

    st.sidebar.subheader("🎨 Aesthetics")
    color_scheme = st.sidebar.selectbox("Color Scheme", ["default", "gambit", "distinctipy", "colorblind"])
    edge_thickness = st.sidebar.slider("Edge Thickness", 0.1, 5.0, 1.0, 0.1)
    action_label_position = st.sidebar.slider("Action Label Pos", 0.0, 1.0, 0.5, 0.05, help="Position of action labels along the edge (0=start, 1=end).")

    # Main Area: Display
    if not game_source:
        st.title("🎨 DrawTree")
        st.info("Select a game from the sidebar to begin.")
        return

    try:
        # We use a single temporary directory for all generated files
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_name = "output"
            svg_path = os.path.join(tmp_dir, f"{base_name}.svg")
            
            # generate_svg handles .ef and .efg files automatically
            generate_svg(
                game=game_source,
                save_to=svg_path,
                scale_factor=scale_factor * 2,
                level_scaling=level_scaling * 4,
                sublevel_scaling=sublevel_scaling * 2,
                width_scaling=width_scaling * 2,
                hide_action_labels=hide_action_labels,
                shared_terminal_depth=shared_terminal_depth,
                show_grid=False,
                color_scheme=color_scheme,
                edge_thickness=edge_thickness,
                action_label_position=action_label_position
            )
            
            if not os.path.exists(svg_path):
                st.error("SVG generation failed.")
                return

            with open(svg_path, "r") as f:
                svg_content = f.read()
            
            # Main window: Only the image
            st.image(svg_path, use_column_width=True)
            
            # Sidebar: Download Buttons
            st.sidebar.header("📥 Downloads")
            
            # SVG and TikZ
            st.sidebar.download_button(
                label="Download SVG",
                data=svg_content,
                file_name="game_tree.svg",
                mime="image/svg+xml",
                use_container_width=True
            )
            
            tikz_code = generate_tikz(
                game=game_source,
                scale_factor=scale_factor * 2,
                level_scaling=level_scaling * 4,
                sublevel_scaling=sublevel_scaling * 2,
                width_scaling=width_scaling * 2,
                hide_action_labels=hide_action_labels,
                shared_terminal_depth=shared_terminal_depth,
                show_grid=False,
                color_scheme=color_scheme,
                edge_thickness=edge_thickness,
                action_label_position=action_label_position
            )
            st.sidebar.download_button(
                label="Download TikZ",
                data=tikz_code,
                file_name="game_tree.tikz",
                mime="text/plain",
                use_container_width=True
            )

            # Other formats
            if st.sidebar.button("Prepare Other Formats", use_container_width=True):
                with st.status("Generating extra formats..."):
                    # LaTeX (.tex)
                    tex_path = os.path.join(tmp_dir, f"{base_name}.tex")
                    generate_tex(game=game_source, save_to=tex_path, scale_factor=scale_factor*2, color_scheme=color_scheme, edge_thickness=edge_thickness, action_label_position=action_label_position)
                    with open(tex_path, "r") as f:
                        st.sidebar.download_button("Download LaTeX (.tex)", f.read(), "game_tree.tex", "text/x-tex", use_container_width=True)
                    
                    # PDF
                    pdf_path = os.path.join(tmp_dir, f"{base_name}.pdf")
                    generate_pdf(game=game_source, save_to=pdf_path, scale_factor=scale_factor*2, color_scheme=color_scheme, edge_thickness=edge_thickness, action_label_position=action_label_position)
                    with open(pdf_path, "rb") as f:
                        st.sidebar.download_button("Download PDF (.pdf)", f.read(), "game_tree.pdf", "application/pdf", use_container_width=True)
                    
                    # PNG
                    png_path = os.path.join(tmp_dir, f"{base_name}.png")
                    generate_png(game=game_source, save_to=png_path, scale_factor=scale_factor*2, color_scheme=color_scheme, edge_thickness=edge_thickness, action_label_position=action_label_position, dpi=300)
                    with open(png_path, "rb") as f:
                        st.sidebar.download_button("Download PNG (.png)", f.read(), "game_tree.png", "image/png", use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)

if __name__ == "__main__":
    run_app()
