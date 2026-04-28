import streamlit as st
import tempfile
from pathlib import Path
import os
import sys

# Add src to path if running from local dev
sys.path.append(str(Path(__file__).parent.parent))

from draw_tree import generate_svg, generate_tikz

def run_app():
    st.set_page_config(page_title="DrawTree GUI", layout="wide", page_icon="🎨")

    st.title("🎨 DrawTree - Interactive Game Tree Drawing")
    st.markdown("""
    Visualize game trees from `.ef` or `.efg` files interactively. 
    Adjust parameters in the sidebar to see changes in real-time.
    """)

    # Sidebar for configuration
    st.sidebar.header("📐 Diagram Options")

    scale_factor = st.sidebar.slider("Overall Scale", 0.1, 5.0, 1.0, 0.1, help="Scale factor for the entire TikZ diagram.")
    
    st.sidebar.subheader("🕹️ Layout Scaling")
    st.sidebar.info("Scaling options only apply to .efg files or Game objects.")
    level_scaling = st.sidebar.slider("Level Scaling", 0.0, 10.0, 1.0, 0.5)
    sublevel_scaling = st.sidebar.slider("Sublevel Scaling", 0.0, 10.0, 1.0, 0.5)
    width_scaling = st.sidebar.slider("Width Scaling", 0.0, 10.0, 1.0, 0.5)

    st.sidebar.subheader("🎨 Aesthetics")
    color_scheme = st.sidebar.selectbox("Color Scheme", ["default", "gambit", "distinctipy", "colorblind"])
    edge_thickness = st.sidebar.slider("Edge Thickness", 0.1, 5.0, 1.0, 0.1)
    action_label_position = st.sidebar.slider("Action Label Pos", 0.0, 1.0, 0.5, 0.05, help="Position of action labels along the edge (0=start, 1=end).")

    st.sidebar.subheader("⚙️ Flags")
    hide_action_labels = st.sidebar.checkbox("Hide Action Labels", False)
    shared_terminal_depth = st.sidebar.checkbox("Shared Terminal Depth", False)
    show_grid = st.sidebar.checkbox("Show Helper Grid", False)

    # Main area
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📂 Input Game")
        
        # Try to find games directory
        base_path = Path(__file__).parent.parent.parent
        example_dir = base_path / "games"
        
        game_source = None
        
        if example_dir.exists():
            ef_examples = list(example_dir.glob("*.ef"))
            efg_examples = list((example_dir / "efg").glob("*.efg"))
            all_examples = sorted([f.relative_to(base_path) for f in ef_examples + efg_examples])
            
            example_selection = st.selectbox("Select an example", ["None"] + [str(e) for e in all_examples])
            if example_selection != "None":
                game_source = str(base_path / example_selection)
        
        uploaded_file = st.file_uploader("Or upload your own .ef or .efg file", type=["ef", "efg"])

        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                tmp.write(uploaded_file.getvalue())
                game_source = tmp.name

    with col2:
        if game_source:
            st.subheader("🖼️ Preview")
            
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    svg_path = os.path.join(tmp_dir, "output.svg")
                    # generate_svg handles .ef and .efg files automatically now
                    generate_svg(
                        game=game_source,
                        save_to=svg_path,
                        scale_factor=scale_factor,
                        level_scaling=level_scaling,
                        sublevel_scaling=sublevel_scaling,
                        width_scaling=width_scaling,
                        hide_action_labels=hide_action_labels,
                        shared_terminal_depth=shared_terminal_depth,
                        show_grid=show_grid,
                        color_scheme=color_scheme,
                        edge_thickness=edge_thickness,
                        action_label_position=action_label_position
                    )
                    
                    if os.path.exists(svg_path):
                        with open(svg_path, "r") as f:
                            svg_content = f.read()
                        
                        st.image(svg_path, use_column_width=True)
                        
                        st.divider()
                        
                        # Download buttons in columns
                        dl_col1, dl_col2 = st.columns(2)
                        with dl_col1:
                            st.download_button(
                                label="📥 Download SVG",
                                data=svg_content,
                                file_name="game_tree.svg",
                                mime="image/svg+xml",
                                use_container_width=True
                            )
                        
                        with dl_col2:
                            tikz_code = generate_tikz(
                                game=game_source,
                                scale_factor=scale_factor,
                                level_scaling=level_scaling,
                                sublevel_scaling=sublevel_scaling,
                                width_scaling=width_scaling,
                                hide_action_labels=hide_action_labels,
                                shared_terminal_depth=shared_terminal_depth,
                                show_grid=show_grid,
                                color_scheme=color_scheme,
                                edge_thickness=edge_thickness,
                                action_label_position=action_label_position
                            )
                            st.download_button(
                                label="📄 Download TikZ",
                                data=tikz_code,
                                file_name="game_tree.tikz",
                                mime="text/plain",
                                use_container_width=True
                            )
                    else:
                        st.error("SVG file was not generated.")
                        
            except Exception as e:
                st.error(f"Error generating image: {e}")
                st.exception(e)
        else:
            st.info("Select an example or upload a file to see the preview.")

if __name__ == "__main__":
    run_app()
