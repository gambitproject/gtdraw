import streamlit as st
import tempfile
from pathlib import Path
import os
import sys
import warnings

# Suppress warnings in the GUI
warnings.filterwarnings("ignore")


# Add src to path if running from local dev
sys.path.append(str(Path(__file__).parent.parent))

from draw_tree import (
    generate_svg,
    generate_tikz,
    generate_tex,
    generate_pdf,
    generate_png,
    count_players,
)


def run_app():
    st.set_page_config(page_title="DrawTree GUI", layout="wide", page_icon="🎨")

    # Sidebar: Title and Input
    st.sidebar.title("🎨 DrawTree")
    st.sidebar.markdown(
        "Welcome to DrawTree! Load a Game in EFG or EF format, then adjust the layout and download your publication-ready image."
    )

    # Try to find games directory
    base_path = Path(__file__).parent.parent.parent
    example_dir = base_path / "games"

    game_source = None
    is_efg = False

    with st.sidebar.expander("📂 Input Game", expanded=True):
        if example_dir.exists():
            ef_examples = list(example_dir.glob("*.ef"))
            efg_examples = list((example_dir / "efg").glob("*.efg"))
            all_examples = sorted(
                [f.relative_to(base_path) for f in ef_examples + efg_examples]
            )

            # Default selection
            default_idx = 0
            target_example = "games/efg/one_card_poker.efg"
            example_list = ["None"] + [str(e) for e in all_examples]
            if target_example in example_list:
                default_idx = example_list.index(target_example)

            example_selection = st.selectbox(
                "Select an example", example_list, index=default_idx
            )
            if example_selection != "None":
                game_source = str(base_path / example_selection)
                if game_source.lower().endswith(".efg"):
                    is_efg = True

        uploaded_file = st.file_uploader(
            "Or upload your own .ef or .efg file", type=["ef", "efg"]
        )

    base_filename = "game_tree"
    if uploaded_file:
        base_filename = Path(uploaded_file.name).stem
        suffix = f".{uploaded_file.name.split('.')[-1]}"
        if suffix.lower() == ".efg":
            is_efg = True
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            game_source = tmp.name
    elif game_source:
        base_filename = Path(game_source).stem

    # Sidebar: Configuration
    with st.sidebar.expander("📐 Layout Options", expanded=False):
        horizontal = st.checkbox(
            "Horizontal Layout",
            value=False,
            help="Switch between vertical (top-down) and horizontal (left-right) layout.",
        )

        scale_factor = st.slider(
            "Overall Scale",
            0.0,
            2.0,
            1.0,
            0.05,
            help="Scale factor for the entire TikZ diagram.",
        )

        edge_thickness = st.slider("Edge Thickness", 0.1, 5.0, 1.0, 0.1)
        action_label_position = st.slider(
            "Action Label Position",
            0.0,
            1.0,
            0.5,
            0.05,
            help="Position of action labels along the edge (0=start, 1=end).",
        )
        action_label_dist = st.slider(
            "Action Label Distance",
            0.0,
            5.0,
            1.0,
            0.1,
            help="Distance of action labels from the edge.",
        )

        # Conditional Layout Scaling
        if is_efg:
            st.markdown("**Layout Scaling**")
            level_scaling = st.slider("Level", 0.0, 2.0, 1.0, 0.05)
            sublevel_scaling = st.slider("Sublevel", 0.0, 2.0, 1.0, 0.05)
            width_scaling = st.slider("Width", 0.0, 2.0, 1.0, 0.05)

            hide_action_labels = False
            shared_terminal_depth = st.checkbox("Shared Terminal Node Depth", False)
        else:
            # Defaults for .ef files
            level_scaling = 1.0
            sublevel_scaling = 1.0
            width_scaling = 1.0
            hide_action_labels = False
            shared_terminal_depth = False

    with st.sidebar.expander("🎨 Aesthetics", expanded=False):
        color_scheme = st.selectbox(
            "Color Scheme",
            ["default", "gambit", "distinctipy", "colorblind", "custom"],
            index=2,  # distinctipy
        )

        custom_colors = None
        if color_scheme == "custom":
            st.markdown("---")
            st.markdown("##### Custom Palette")
            num_players = count_players(game_source) if game_source else 2
            custom_colors = {}
            # Chance color
            custom_colors[0] = st.color_picker(
                "Chance Node", value="#759138", key="cp_chance"
            )
            # Player colors
            for i in range(1, num_players + 1):
                default_val = "#000000"
                # Use some sensible defaults for first few players
                if i == 1:
                    default_val = "#E41A1C"
                elif i == 2:
                    default_val = "#377EB8"
                elif i == 3:
                    default_val = "#4DAF4A"

                custom_colors[i] = st.color_picker(
                    f"Player {i}", value=default_val, key=f"cp_p{i}"
                )

        st.markdown("---")
        st.markdown("##### Typography")
        font_family_name = st.selectbox(
            "Font Family",
            ["Serif", "Sans-Serif", "Monospace"],
            index=0,
            help="Global font family for the diagram.",
        )
        font_map = {
            "Serif": "rmfamily",
            "Sans-Serif": "sffamily",
            "Monospace": "ttfamily",
        }
        font_family = font_map[font_family_name]

        col1, col2 = st.columns(2)
        with col1:
            font_bold = st.checkbox("Bold")
        with col2:
            font_italic = st.checkbox("Italic")

        font_size_name = st.selectbox(
            "Text Size",
            ["Small", "Normal", "Large", "Huge"],
            index=1,
            help="Global text size for the diagram.",
        )
        size_map = {
            "Small": "small",
            "Normal": "normalsize",
            "Large": "large",
            "Huge": "Large",
        }
        font_size = size_map[font_size_name]

    # Main Area: Display
    if not game_source:
        st.title("🎨 DrawTree")
        st.info("Select a game from the sidebar to begin.")
        return

    try:
        # Use games/efg/ for intermediate files as requested (gitignored)
        efg_dir = Path(__file__).parent.parent.parent / "games" / "efg"
        if not efg_dir.exists():
            # Fallback to system temp if games/efg/ doesn't exist
            work_dir = Path(tempfile.gettempdir())
        else:
            work_dir = efg_dir

        base_name = f"gui_temp_{os.getpid()}"
        svg_path = str(work_dir / f"{base_name}.svg")
        output_base = str(work_dir / base_name)

        svg_code = generate_svg(
            game=game_source,
            save_to=svg_path,
            scale_factor=scale_factor,
            level_scaling=level_scaling,
            sublevel_scaling=sublevel_scaling,
            width_scaling=width_scaling,
            hide_action_labels=hide_action_labels,
            shared_terminal_depth=shared_terminal_depth,
            show_grid=False,
            color_scheme=color_scheme,
            edge_thickness=edge_thickness,
            action_label_position=action_label_position,
            responsive_sizing=True,
            font_family=font_family,
            font_bold=font_bold,
            font_italic=font_italic,
            font_size=font_size,
            custom_colors=custom_colors,
            horizontal=horizontal,
            action_label_dist=action_label_dist,
        )

        if not os.path.exists(svg_path):
            st.error("SVG generation failed.")
            return

        with open(svg_path, "r") as f:
            svg_content = f.read()

        # Display the responsive SVG directly
        st.markdown(svg_content, unsafe_allow_html=True)

        # Pre-generate all download formats
        tikz_code = generate_tikz(
            game=game_source,
            save_to=output_base + ".tikz",
            scale_factor=scale_factor,
            level_scaling=level_scaling,
            sublevel_scaling=sublevel_scaling,
            width_scaling=width_scaling,
            hide_action_labels=hide_action_labels,
            shared_terminal_depth=shared_terminal_depth,
            show_grid=False,
            color_scheme=color_scheme,
            edge_thickness=edge_thickness,
            action_label_position=action_label_position,
            font_family=font_family,
            font_bold=font_bold,
            font_italic=font_italic,
            font_size=font_size,
            custom_colors=custom_colors,
            horizontal=horizontal,
            action_label_dist=action_label_dist,
        )

        tex_path = generate_tex(
            game=game_source,
            save_to=output_base + ".tex",
            scale_factor=scale_factor,
            level_scaling=level_scaling,
            sublevel_scaling=sublevel_scaling,
            width_scaling=width_scaling,
            hide_action_labels=hide_action_labels,
            shared_terminal_depth=shared_terminal_depth,
            color_scheme=color_scheme,
            edge_thickness=edge_thickness,
            action_label_position=action_label_position,
            font_family=font_family,
            font_bold=font_bold,
            font_italic=font_italic,
            font_size=font_size,
            custom_colors=custom_colors,
            horizontal=horizontal,
            action_label_dist=action_label_dist,
        )
        with open(tex_path, "r") as f:
            tex_data = f.read()

        pdf_path = generate_pdf(
            game=game_source,
            save_to=output_base + ".pdf",
            scale_factor=scale_factor,
            level_scaling=level_scaling,
            sublevel_scaling=sublevel_scaling,
            width_scaling=width_scaling,
            hide_action_labels=hide_action_labels,
            shared_terminal_depth=shared_terminal_depth,
            color_scheme=color_scheme,
            edge_thickness=edge_thickness,
            action_label_position=action_label_position,
            font_family=font_family,
            font_bold=font_bold,
            font_italic=font_italic,
            font_size=font_size,
            custom_colors=custom_colors,
            horizontal=horizontal,
            action_label_dist=action_label_dist,
        )
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()

        png_path = generate_png(
            game=game_source,
            save_to=output_base + ".png",
            scale_factor=scale_factor,
            level_scaling=level_scaling,
            sublevel_scaling=sublevel_scaling,
            width_scaling=width_scaling,
            hide_action_labels=hide_action_labels,
            shared_terminal_depth=shared_terminal_depth,
            color_scheme=color_scheme,
            edge_thickness=edge_thickness,
            action_label_position=action_label_position,
            dpi=300,
            font_family=font_family,
            font_bold=font_bold,
            font_italic=font_italic,
            font_size=font_size,
            custom_colors=custom_colors,
            horizontal=horizontal,
            action_label_dist=action_label_dist,
        )
        with open(png_path, "rb") as f:
            png_data = f.read()

        # Sidebar: Download Buttons
        with st.sidebar.expander("📥 Downloads", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "SVG",
                    svg_content,
                    f"{base_filename}.svg",
                    "image/svg+xml",
                    use_container_width=True,
                )
                st.download_button(
                    "PDF",
                    pdf_data,
                    f"{base_filename}.pdf",
                    "application/pdf",
                    use_container_width=True,
                )
                st.download_button(
                    "PNG",
                    png_data,
                    f"{base_filename}.png",
                    "image/png",
                    use_container_width=True,
                )
            with c2:
                st.download_button(
                    "TikZ",
                    tikz_code,
                    f"{base_filename}.tikz",
                    "text/plain",
                    use_container_width=True,
                )
                st.download_button(
                    "LaTeX",
                    tex_data,
                    f"{base_filename}.tex",
                    "text/x-tex",
                    use_container_width=True,
                )

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)


if __name__ == "__main__":
    run_app()
