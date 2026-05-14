import streamlit as st
import tempfile
from pathlib import Path
import os
import sys
import warnings

# Suppress warnings in the GUI
warnings.filterwarnings("ignore")


# Add src to path if running from local dev
sys.path.insert(0, str(Path(__file__).parent.parent))

from draw_tree import (
    generate_svg,
    generate_tikz,
    generate_tex,
    generate_pdf,
    generate_png,
    count_players,
    ef_to_efg,
    efg_to_ef,
)


def run_app():
    # Use the project favicon if available
    icon_path = (
        Path(__file__).parent.parent.parent
        / "img"
        / "favicon_48x48_light green background.png"
    )
    icon = "🎨"
    if icon_path.exists():
        icon = str(icon_path)

    st.set_page_config(page_title="DrawTree", layout="wide", page_icon=icon)

    # Sidebar: Title and Input
    if icon_path.exists():
        col1, col2 = st.sidebar.columns([0.25, 0.75])
        with col1:
            st.image(str(icon_path), width=50)
        with col2:
            st.title("DrawTree")
    else:
        st.sidebar.title("🎨 DrawTree")
    st.sidebar.markdown(
        "##### Part of the [Gambit project](https://www.gambit-project.org/)."
    )
    st.sidebar.markdown(
        "📖 **[Documentation](https://www.gambit-project.org/draw_tree/)**"
    )
    st.sidebar.markdown(
        "Welcome to DrawTree! Load a Game in EFG or EF format, then adjust the layout and download your publication-ready image."
    )

    # Try to find games directory
    base_path = Path(__file__).parent.parent.parent
    example_dir = base_path / "games"

    game_source = None
    is_efg = False

    with st.sidebar.expander("📂 Input Game", expanded=True):
        import pygambit as gbt

        try:
            catalog_games_df = gbt.catalog.games()
            catalog_games = catalog_games_df["Game"].tolist()
        except Exception:
            catalog_games = []

        options = [("None", "None", "None")]

        for g in catalog_games:
            options.append(("Catalog", g, g))

        if example_dir.exists():
            ef_examples = sorted(list(example_dir.glob("*.ef")))
            for e in ef_examples:
                rel_path = str(e.relative_to(base_path))
                options.append(("EF", e.name, rel_path))

            efg_examples = sorted(list((example_dir / "efg").glob("*.efg")))
            for e in efg_examples:
                rel_path = str(e.relative_to(base_path))
                options.append(("EFG", e.name, rel_path))

        def format_option(opt):
            cat, name, val = opt
            if cat == "None":
                return "None"
            return f"[{cat}] {name}"

        # Default selection
        default_idx = 0
        target_example_path = "games/efg/one_card_poker.efg"
        for i, opt in enumerate(options):
            if opt[2] == target_example_path:
                default_idx = i
                break

        help_text = (
            "**Catalog**: Games Gambit's catalog.\n\n"
            "**EF**: DrawTree .ef format games.\n\n"
            "**EFG**: Gambit .efg files."
        )

        example_selection = st.selectbox(
            "Select an example",
            options,
            index=default_idx,
            format_func=format_option,
            help=help_text,
        )
        if example_selection[0] != "None":
            cat, name, val = example_selection
            if cat == "Catalog":
                game_source = gbt.catalog.load(val)
                is_efg = True
            else:
                game_source = str(base_path / val)
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
        if isinstance(game_source, str):
            base_filename = Path(game_source).stem
        else:
            base_filename = (
                getattr(game_source, "title", "catalog_game")
                .replace(" ", "_")
                .replace("/", "_")
            )
            if not base_filename:
                base_filename = "catalog_game"

    # Sidebar: Configuration
    with st.sidebar.expander("📐 Layout", expanded=False):
        horizontal = st.checkbox(
            "Horizontal Layout",
            value=False,
            help="Switch between vertical (top-down) and horizontal (left-right) layout.",
        )

        if is_efg:
            shared_terminal_depth = st.checkbox("Shared Terminal Node Depth", False)

        scale_factor = st.slider(
            "Scale factor",
            0.5,
            2.0,
            1.0,
            0.05,
            help="Scale factor for the entire TikZ diagram.",
        )

        # Conditional Layout Scaling
        if is_efg:
            level_scaling = st.slider("Level Spacing", 0.0, 5.0, 1.0, 0.05)
            sublevel_scaling = st.slider("Sublevel Spacing", 0.0, 5.0, 1.0, 0.05)
            width_scaling = st.slider("Width Spacing", 0.0, 5.0, 1.0, 0.05)
            hide_action_labels = False
        else:
            # Defaults for .ef files
            level_scaling = 1.0
            sublevel_scaling = 1.0
            width_scaling = 1.0
            hide_action_labels = False
            shared_terminal_depth = False

        edge_thickness = st.slider("Edge Thickness", 0.1, 5.0, 1.0, 0.1)
        node_size = st.slider(
            "Node Size", 0.5, 5.0, 1.5, 0.1, help="Size of player nodes in mm."
        )
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
            1.0,
            5.0,
            1.0,
            0.1,
            help="Distance of action labels from the edge.",
        )

    with st.sidebar.expander("🔵 Information Sets", expanded=False):
        iset_fill = st.checkbox("Fill Information Sets", value=False)
        iset_fill_opacity = st.slider(
            "Fill Opacity", 0.0, 1.0, 0.2, 0.05, disabled=not iset_fill
        )
        iset_boundary = st.selectbox(
            "Boundary Style", ["solid", "dotted", "none"], index=0
        )

    with st.sidebar.expander("🎨 Aesthetics", expanded=False):
        color_scheme = st.selectbox(
            "Color Scheme",
            ["default", "gambit", "distinctipy", "colorblind", "custom"],
            index=4,  # custom
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
        if icon_path.exists():
            c1, c2 = st.columns([0.1, 0.9])
            with c1:
                st.image(str(icon_path), width=80)
            with c2:
                st.title("DrawTree")
            st.markdown(
                "### Part of the [Gambit project](https://www.gambit-project.org/)"
            )
        else:
            st.title("🎨 DrawTree")
            st.markdown(
                "### Part of the [Gambit project](https://www.gambit-project.org/)"
            )
        st.info("Select a game from the sidebar to begin.")
        return

    try:
        # Use a temporary directory for all GUI-generated files to ensure cleanup
        with tempfile.TemporaryDirectory() as work_dir_str:
            work_dir = Path(work_dir_str)

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
                iset_fill=iset_fill,
                iset_fill_opacity=iset_fill_opacity,
                iset_boundary=iset_boundary,
                node_size=node_size,
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
                iset_fill=iset_fill,
                iset_fill_opacity=iset_fill_opacity,
                iset_boundary=iset_boundary,
                node_size=node_size,
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
                iset_fill=iset_fill,
                iset_fill_opacity=iset_fill_opacity,
                iset_boundary=iset_boundary,
                node_size=node_size,
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
                iset_fill=iset_fill,
                iset_fill_opacity=iset_fill_opacity,
                iset_boundary=iset_boundary,
                node_size=node_size,
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
                iset_fill=iset_fill,
                iset_fill_opacity=iset_fill_opacity,
                iset_boundary=iset_boundary,
                node_size=node_size,
            )
            with open(png_path, "rb") as f:
                png_data = f.read()

            # Sidebar: Download Buttons
            with st.sidebar.expander("📥 Downloads", expanded=False):
                # Pre-generate EF and EFG data for download
                ef_data = None
                efg_data = None
                try:
                    if is_efg:
                        # Input was EFG/catalog: generate the EF file
                        ef_download_path = efg_to_ef(
                            game_source,
                            save_to=output_base + ".ef",
                            level_scaling=level_scaling,
                            sublevel_scaling=sublevel_scaling,
                            width_scaling=width_scaling,
                            shared_terminal_depth=shared_terminal_depth,
                        )
                        with open(ef_download_path, "r") as f:
                            ef_data = f.read()
                        # For EFG, read the original or generate from game
                        if isinstance(game_source, str) and os.path.exists(game_source):
                            with open(game_source, "r") as f:
                                efg_data = f.read()
                        else:
                            # Catalog game: convert EF back to EFG
                            efg_download_path = ef_to_efg(
                                ef_download_path,
                                save_to=output_base + ".efg",
                            )
                            with open(efg_download_path, "r") as f:
                                efg_data = f.read()
                    else:
                        # Input was EF: read the original file
                        with open(game_source, "r") as f:
                            ef_data = f.read()
                        # Convert to EFG
                        efg_download_path = ef_to_efg(
                            game_source,
                            save_to=output_base + ".efg",
                        )
                        with open(efg_download_path, "r") as f:
                            efg_data = f.read()
                except Exception as conv_err:
                    st.caption(f"⚠️ Format conversion unavailable: {conv_err}")

                c1, c2 = st.columns(2)
                with c1:
                    if ef_data is not None:
                        st.download_button(
                            "EF",
                            ef_data,
                            f"{base_filename}.ef",
                            "text/plain",
                            use_container_width=True,
                        )
                    st.download_button(
                        "TikZ",
                        tikz_code,
                        f"{base_filename}.tikz",
                        "text/plain",
                        use_container_width=True,
                    )
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
                with c2:
                    if efg_data is not None:
                        st.download_button(
                            "EFG",
                            efg_data,
                            f"{base_filename}.efg",
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
                    st.download_button(
                        "PNG",
                        png_data,
                        f"{base_filename}.png",
                        "image/png",
                        use_container_width=True,
                    )

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)


if __name__ == "__main__":
    run_app()
