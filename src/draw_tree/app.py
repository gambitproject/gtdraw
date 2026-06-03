import streamlit as st
import tempfile
from pathlib import Path
import os
import sys
import warnings
import yaml

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
    get_game_levels,
    ef_to_efg,
    efg_to_ef,
)


def _get_scheme_colors(color_scheme: str, num_players: int) -> dict[int, str]:
    """Return {player_index: '#RRGGBB'} for the named colour scheme."""
    CHANCE = "#759138"
    if color_scheme == "gambit":
        palette = {
            0: CHANCE, 1: "#EA3323", 2: "#0000FF", 3: "#FF7F00",
            4: "#800080", 5: "#00FFFF", 6: "#FF00FF",
        }
        return {k: v for k, v in palette.items() if k <= num_players}
    if color_scheme in ("distinctipy", "colorblind"):
        try:
            import distinctipy
            colorblind_type = "Deuteranomaly" if color_scheme == "colorblind" else None
            chance_rgb = (117 / 255, 145 / 255, 56 / 255)
            colors = distinctipy.get_colors(
                num_players,
                exclude_colors=[(0, 0, 0), (1, 1, 1), chance_rgb],
                rng=42,
                colorblind_type=colorblind_type,
            )
            result = {0: CHANCE}
            for i, (r, g, b) in enumerate(colors):
                result[i + 1] = f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"
            return result
        except Exception:
            return {i: "#000000" for i in range(num_players + 1)}
    return {i: "#000000" for i in range(num_players + 1)}


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
        "Welcome to DrawTree! Load a game in EF, EFG, or NFG format, then download your publication-ready image."
    )

    # Try to find games directory
    base_path = Path(__file__).parent.parent.parent
    example_dir = base_path / "games"

    game_source = None
    is_efg = False
    is_nfg = False

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

            nfg_examples = sorted(list((example_dir / "nfg").glob("*.nfg")))
            for e in nfg_examples:
                rel_path = str(e.relative_to(base_path))
                options.append(("NFG", e.name, rel_path))

        def format_option(i):
            cat, name, _ = options[i]
            if cat == "None":
                return "None"
            return f"[{cat}] {name}"

        # Default selection
        default_idx = 0
        target_example_path = "games/example.ef"
        for i, opt in enumerate(options):
            if opt[2] == target_example_path:
                default_idx = i
                break

        help_text = (
            "**Catalog**: Games from Gambit's catalog.\n\n"
            "**EF**: DrawTree .ef format games.\n\n"
            "**EFG**: Gambit .efg files.\n\n"
            "**NFG**: Gambit .nfg normal form (strategic form) games."
        )

        selected_idx = st.selectbox(
            "Select an example",
            range(len(options)),
            index=default_idx,
            format_func=format_option,
            help=help_text,
        )
        example_selection = options[selected_idx]
        if example_selection[0] != "None":
            cat, name, val = example_selection
            if cat == "Catalog":
                game_source = gbt.catalog.load(val)
                is_efg = True
            else:
                game_source = str(base_path / val)
                if game_source.lower().endswith(".efg"):
                    is_efg = True
                elif game_source.lower().endswith(".nfg"):
                    is_nfg = True

        uploaded_file = st.file_uploader(
            "Or upload your own .ef, .efg, or .nfg file", type=["ef", "efg", "nfg"]
        )

    base_filename = "game_tree"
    if uploaded_file:
        base_filename = Path(uploaded_file.name).stem
        suffix = f".{uploaded_file.name.split('.')[-1]}"
        if suffix.lower() == ".efg":
            is_efg = True
        elif suffix.lower() == ".nfg":
            is_nfg = True
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
    # Tree-specific layout options (not applicable to NFG)
    horizontal = False
    mirror = False
    scale_factor = 1.0
    level_scaling = 1.0
    sublevel_scaling = 1.0
    width_scaling = 1.0
    hide_action_labels = False
    shared_terminal_depth = False
    edge_thickness = 1.0
    node_size = 1.5
    action_label_position = 0.5
    action_label_dist = 1.0
    iset_fill = False
    iset_fill_opacity = 0.2
    iset_boundary = "solid"
    label_bg = False
    label_bg_by = "player"
    label_bg_style = "player_bg"
    label_bg_color = "white"
    label_bg_opacity = 0.8

    if not is_nfg:
        with st.sidebar.expander("📐 Layout", expanded=False):
            horizontal = st.checkbox(
                "Horizontal Layout",
                value=False,
                help="Switch between vertical (top-down) and horizontal (left-right) layout.",
            )
            mirror = st.checkbox(
                "Mirror Layout",
                value=False,
                help="Mirror the tree left-to-right by flipping xshift values.",
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

            if is_efg:
                level_scaling = st.slider("Level Spacing", 0.0, 5.0, 1.0, 0.05)
                sublevel_scaling = st.slider("Sublevel Spacing", 0.0, 5.0, 1.0, 0.05)
                width_scaling = st.slider("Width Spacing", 0.0, 5.0, 1.0, 0.05)

    # Defaults used when aesthetics expander is hidden (NFG path)
    color_scheme = "colorblind"
    legend_position = "top-left"
    custom_colors = None
    font_family = "rmfamily"
    font_bold = False
    font_italic = False
    font_size = "normalsize"

    if not is_nfg:
        with st.sidebar.expander("🎨 Aesthetics", expanded=False):
            # Session-state init: default to colorblind
            if "scheme_selector" not in st.session_state:
                st.session_state["scheme_selector"] = "colorblind"

            _num_p = count_players(game_source) if game_source else 2

            # Step 2: scheme-change → reset pickers to new scheme's defaults
            _prev = st.session_state.get("_prev_scheme")
            _cur = st.session_state["scheme_selector"]
            if _prev != _cur and _cur not in ("default", "custom"):
                for _pnum, _hex in _get_scheme_colors(_cur, _num_p).items():
                    _pk = "cp_chance" if _pnum == 0 else f"cp_p{_pnum}"
                    st.session_state[_pk] = _hex
            st.session_state["_prev_scheme"] = _cur

            # Step 3: colour-change → auto-switch to custom
            if _cur not in ("default", "custom"):
                _defs = _get_scheme_colors(_cur, _num_p)
                for _pnum in range(_num_p + 1):
                    _pk = "cp_chance" if _pnum == 0 else f"cp_p{_pnum}"
                    _val = st.session_state.get(_pk)
                    if _val is not None and _val.upper() != _defs.get(_pnum, "#000000").upper():
                        st.session_state["scheme_selector"] = "custom"
                        break

            # Step 4: render scheme selector and legend position
            color_scheme = st.selectbox(
                "Color Scheme",
                ["default", "gambit", "distinctipy", "colorblind", "custom"],
                key="scheme_selector",
            )
            legend_position = st.selectbox(
                "Legend Position",
                ["top-left", "top-right", "bottom-left", "bottom-right"],
                index=0,
                help="Corner of the diagram where the player colour legend appears.",
                disabled=(color_scheme == "default"),
            )

            # Step 5: palette — shown for all non-default schemes
            custom_colors = None
            if color_scheme != "default":
                st.markdown("---")
                st.markdown("##### Palette")
                if color_scheme != "custom":
                    _disp = _get_scheme_colors(color_scheme, _num_p)
                else:
                    _disp = {0: "#759138", 1: "#E41A1C", 2: "#377EB8", 3: "#4DAF4A"}
                _picked = {}
                _picked[0] = st.color_picker(
                    "Chance Node", value=_disp.get(0, "#759138"), key="cp_chance"
                )
                for _i in range(1, _num_p + 1):
                    _picked[_i] = st.color_picker(
                        f"Player {_i}",
                        value=_disp.get(_i, "#000000"),
                        key=f"cp_p{_i}",
                    )
                # Determine rendering scheme and custom_colors
                if color_scheme != "custom":
                    _rdefs = _get_scheme_colors(color_scheme, _num_p)
                    if all(_picked[k].upper() == _rdefs.get(k, "#000000").upper() for k in _picked):
                        custom_colors = None  # unchanged — use named scheme
                    else:
                        color_scheme = "custom"
                        custom_colors = _picked
                else:
                    custom_colors = _picked

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

            st.markdown("---")
            st.markdown("##### Label Styling")

            num_players = count_players(game_source) if game_source else 2
            game_levels = get_game_levels(game_source, level_scaling=level_scaling, sublevel_scaling=sublevel_scaling) if game_source else list(range(5))

            label_bg_enabled = st.checkbox(
                "Enable Label Background",
                value=False,
                help="Adds a filled background behind label text to improve readability.",
            )
            if label_bg_enabled:
                label_bg_scope = st.selectbox(
                    "Background applies to",
                    ["All", "By Player", "By Level"],
                    index=0,
                    help="Apply to all labels, or selectively per player or per level.",
                )
                if label_bg_scope == "All":
                    label_bg = True
                    label_bg_by = "player"
                elif label_bg_scope == "By Player":
                    label_bg_by = "player"
                    selected_bg_players = st.multiselect(
                        "Apply to players",
                        options=list(range(num_players + 1)),
                        default=list(range(num_players + 1)),
                        format_func=lambda x: "Chance" if x == 0 else f"Player {x}",
                        help="Select which players' labels should have a background.",
                        key="lbg_players",
                    )
                    label_bg = {i: True for i in selected_bg_players}
                else:  # By Level
                    label_bg_by = "level"
                    selected_bg_levels = st.multiselect(
                        "Apply to levels",
                        options=game_levels,
                        default=game_levels,
                        format_func=lambda x: f"Level {x}",
                        help="Select which tree levels' labels should have a background.",
                        key="lbg_levels",
                    )
                    label_bg = {lv: True for lv in selected_bg_levels}

                label_bg_style_name = st.selectbox(
                    "Background Style",
                    ["Player colour (white text)", "White (player colour text)"],
                    index=0,
                    help="Player colour background with white text, or white background with player-colour text.",
                )
                label_bg_style = "white_bg" if label_bg_style_name.startswith("White") else "player_bg"
                label_bg_opacity = st.slider("Background Opacity", 0.0, 1.0, 0.8, 0.05)
            label_bg_color = "white"  # fallback; player colors used automatically

            st.markdown("---")
            st.markdown("##### Action Label Positioning")

            # Vary action label positions
            vary_action_label_positions = st.checkbox(
                "Vary Action Label Positions",
                value=False,
                help="Vary action label positions based on the number of outgoing edges to avoid clashes.",
            )
            if vary_action_label_positions:
                vary_by = st.selectbox(
                    "Vary by",
                    ["All", "By Player", "By Level"],
                    index=0,
                    help="Apply varying positions to all nodes, or selectively to specific players or levels.",
                )
                vary_action_label_positions_by = {"All": "all", "By Player": "player", "By Level": "level"}[vary_by]
                if vary_by == "By Player":
                    selected_players = st.multiselect(
                        "Apply vary to players",
                        options=list(range(num_players + 1)),
                        default=list(range(num_players + 1)),
                        format_func=lambda x: "Chance" if x == 0 else f"Player {x}",
                        help="Select which players' outgoing edges should have varied label positions.",
                    )
                    vary_action_label_positions_choices = (
                        selected_players if selected_players else None
                    )
                elif vary_by == "By Level":
                    selected_levels = st.multiselect(
                        "Apply vary to levels",
                        options=game_levels,
                        default=game_levels,
                        format_func=lambda x: f"Level {x}",
                        help="Select which tree levels should have varied label positions.",
                    )
                    vary_action_label_positions_choices = (
                        selected_levels if selected_levels else None
                    )
                else:
                    vary_action_label_positions_choices = None
            else:
                vary_action_label_positions_by = "all"
                vary_action_label_positions_choices = None

            # Positioning mode
            positioning_mode = st.selectbox(
                "Positioning Mode",
                ["Global", "By Player", "By Level"],
                index=0,
                disabled=vary_action_label_positions,
                help="Set a single global position, or customise per-player or per-level.",
            )
            action_label_position_by = (
                "player"
                if positioning_mode == "By Player"
                else "level"
                if positioning_mode == "By Level"
                else "player"
            )

            if positioning_mode == "Global" or vary_action_label_positions:
                action_label_position = st.slider(
                    "Action Label Position",
                    0.0,
                    1.0,
                    0.5,
                    0.05,
                    help="Position of action labels along the edge (0=start, 1=end).",
                    disabled=vary_action_label_positions,
                )
            elif positioning_mode == "By Player":
                action_label_position = {}
                pos_chance = st.slider(
                    "Chance Actions Position", 0.0, 1.0, 0.5, 0.05, key="alp_chance"
                )
                action_label_position[0] = pos_chance
                for i in range(1, num_players + 1):
                    pos_p = st.slider(
                        f"Player {i} Actions Position",
                        0.0,
                        1.0,
                        0.5,
                        0.05,
                        key=f"alp_p{i}",
                    )
                    action_label_position[i] = pos_p
            else:  # By Level
                action_label_position = {}
                for lv in game_levels:
                    pos_lv = st.slider(
                        f"Level {lv} Position", 0.0, 1.0, 0.5, 0.05, key=f"alp_lv{lv}"
                    )
                    action_label_position[lv] = pos_lv

            action_label_dist = st.slider(
                "Action Label Distance",
                1.0,
                5.0,
                1.0,
                0.1,
                help="Distance of action labels from the edge.",
                disabled=bool(label_bg),
            )

            st.markdown("---")
            st.markdown("##### Edge & Node Styling")
            edge_thickness = st.slider("Edge Thickness", 0.1, 5.0, 1.0, 0.1)
            node_size = st.slider(
                "Node Size", 0.5, 5.0, 1.5, 0.1, help="Size of player nodes in mm."
            )

            st.markdown("---")
            st.markdown("##### Information Sets")
            iset_fill = st.checkbox("Fill Information Sets", value=False)
            iset_fill_opacity = st.slider(
                "Fill Opacity", 0.0, 1.0, 0.2, 0.05, disabled=not iset_fill
            )
            iset_boundary = st.selectbox(
                "Boundary Style", ["solid", "dotted", "none"], index=0
            )

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
            output_base = str(work_dir / base_name)

            if is_nfg:
                # NFG: get the LaTeX body (always available, no pdflatex needed)
                tikz_code = generate_tikz(game=game_source)
                tex_path = generate_tex(game=game_source, save_to=output_base + ".tex")
                with open(tex_path, "r") as f:
                    tex_data = f.read()

                # Try to render as PNG; fall back gracefully if pdflatex/sgame unavailable
                png_data = None
                pdf_data = None
                nfg_render_error = None
                try:
                    png_path = str(work_dir / f"{base_name}.png")
                    generate_png(game=game_source, save_to=png_path)
                    with open(png_path, "rb") as f:
                        png_data = f.read()
                    import base64

                    b64 = base64.b64encode(png_data).decode()
                    st.markdown(
                        f'<img src="data:image/png;base64,{b64}" '
                        f'style="max-width:100%;max-height:85vh;'
                        f'object-fit:contain;display:block;margin:auto;" />',
                        unsafe_allow_html=True,
                    )
                    pdf_path = generate_pdf(
                        game=game_source, save_to=output_base + ".pdf"
                    )
                    with open(pdf_path, "rb") as f:
                        pdf_data = f.read()
                except RuntimeError as e:
                    nfg_render_error = str(e)

                if nfg_render_error:
                    st.warning(
                        "⚠️ Could not compile payoff table to image — pdflatex or the "
                        "`sgame` LaTeX package may not be installed.\n\n"
                        "Install with: `sudo apt-get install texlive-games` (Ubuntu) or "
                        "use a full TeX distribution."
                    )
                    with st.expander("Show pdflatex error details"):
                        st.code(nfg_render_error)
                    st.markdown(
                        "**LaTeX source** (copy into a `.tex` file to compile locally):"
                    )
                    st.code(tex_data, language="latex")

                with st.sidebar.expander("📥 Downloads", expanded=False):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button(
                            "LaTeX",
                            tex_data,
                            f"{base_filename}.tex",
                            "text/x-tex",
                            width="stretch",
                        )
                        if pdf_data is not None:
                            st.download_button(
                                "PDF",
                                pdf_data,
                                f"{base_filename}.pdf",
                                "application/pdf",
                                width="stretch",
                            )
                    with c2:
                        st.download_button(
                            "Game Env",
                            tikz_code,
                            f"{base_filename}.tex",
                            "text/plain",
                            width="stretch",
                            help="Raw \\begin{game}...\\end{game} LaTeX body.",
                        )
                        if png_data is not None:
                            st.download_button(
                                "PNG",
                                png_data,
                                f"{base_filename}.png",
                                "image/png",
                                width="stretch",
                            )
                return

            svg_path = str(work_dir / f"{base_name}.svg")

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
                mirror=mirror,
                legend_position=legend_position,
                action_label_dist=action_label_dist,
                iset_fill=iset_fill,
                iset_fill_opacity=iset_fill_opacity,
                iset_boundary=iset_boundary,
                node_size=node_size,
                label_bg=label_bg,
                label_bg_color=label_bg_color,
                label_bg_opacity=label_bg_opacity,
                label_bg_by=label_bg_by,
                label_bg_style=label_bg_style,
                vary_action_label_positions=vary_action_label_positions,
                action_label_position_by=action_label_position_by,
                vary_action_label_positions_by=vary_action_label_positions_by,
                vary_action_label_positions_choices=vary_action_label_positions_choices,
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
                mirror=mirror,
                legend_position=legend_position,
                action_label_dist=action_label_dist,
                iset_fill=iset_fill,
                iset_fill_opacity=iset_fill_opacity,
                iset_boundary=iset_boundary,
                node_size=node_size,
                label_bg=label_bg,
                label_bg_color=label_bg_color,
                label_bg_opacity=label_bg_opacity,
                label_bg_by=label_bg_by,
                label_bg_style=label_bg_style,
                vary_action_label_positions=vary_action_label_positions,
                action_label_position_by=action_label_position_by,
                vary_action_label_positions_by=vary_action_label_positions_by,
                vary_action_label_positions_choices=vary_action_label_positions_choices,
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
                mirror=mirror,
                legend_position=legend_position,
                action_label_dist=action_label_dist,
                iset_fill=iset_fill,
                iset_fill_opacity=iset_fill_opacity,
                iset_boundary=iset_boundary,
                node_size=node_size,
                label_bg=label_bg,
                label_bg_color=label_bg_color,
                label_bg_opacity=label_bg_opacity,
                label_bg_by=label_bg_by,
                label_bg_style=label_bg_style,
                vary_action_label_positions=vary_action_label_positions,
                action_label_position_by=action_label_position_by,
                vary_action_label_positions_by=vary_action_label_positions_by,
                vary_action_label_positions_choices=vary_action_label_positions_choices,
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
                mirror=mirror,
                legend_position=legend_position,
                action_label_dist=action_label_dist,
                iset_fill=iset_fill,
                iset_fill_opacity=iset_fill_opacity,
                iset_boundary=iset_boundary,
                node_size=node_size,
                label_bg=label_bg,
                label_bg_color=label_bg_color,
                label_bg_opacity=label_bg_opacity,
                label_bg_by=label_bg_by,
                label_bg_style=label_bg_style,
                vary_action_label_positions=vary_action_label_positions,
                action_label_position_by=action_label_position_by,
                vary_action_label_positions_by=vary_action_label_positions_by,
                vary_action_label_positions_choices=vary_action_label_positions_choices,
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
                mirror=mirror,
                legend_position=legend_position,
                action_label_dist=action_label_dist,
                iset_fill=iset_fill,
                iset_fill_opacity=iset_fill_opacity,
                iset_boundary=iset_boundary,
                node_size=node_size,
                label_bg=label_bg,
                label_bg_color=label_bg_color,
                label_bg_opacity=label_bg_opacity,
                label_bg_by=label_bg_by,
                label_bg_style=label_bg_style,
                vary_action_label_positions=vary_action_label_positions,
                action_label_position_by=action_label_position_by,
                vary_action_label_positions_by=vary_action_label_positions_by,
                vary_action_label_positions_choices=vary_action_label_positions_choices,
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
                            width="stretch",
                        )
                    st.download_button(
                        "TikZ",
                        tikz_code,
                        f"{base_filename}.tikz",
                        "text/plain",
                        width="stretch",
                    )
                    st.download_button(
                        "SVG",
                        svg_content,
                        f"{base_filename}.svg",
                        "image/svg+xml",
                        width="stretch",
                    )
                    st.download_button(
                        "PDF",
                        pdf_data,
                        f"{base_filename}.pdf",
                        "application/pdf",
                        width="stretch",
                    )
                with c2:
                    if efg_data is not None:
                        st.download_button(
                            "EFG",
                            efg_data,
                            f"{base_filename}.efg",
                            "text/plain",
                            width="stretch",
                        )
                    st.download_button(
                        "LaTeX",
                        tex_data,
                        f"{base_filename}.tex",
                        "text/x-tex",
                        width="stretch",
                    )
                    st.download_button(
                        "PNG",
                        png_data,
                        f"{base_filename}.png",
                        "image/png",
                        width="stretch",
                    )

                settings = {
                    "scale_factor": scale_factor,
                    "level_scaling": level_scaling,
                    "sublevel_scaling": sublevel_scaling,
                    "width_scaling": width_scaling,
                    "horizontal": horizontal,
                    "mirror": mirror,
                    "shared_terminal_depth": shared_terminal_depth,
                    "color_scheme": color_scheme,
                    "edge_thickness": edge_thickness,
                    "action_label_position": action_label_position,
                    "action_label_position_by": action_label_position_by,
                    "action_label_dist": action_label_dist,
                    "vary_action_label_positions": vary_action_label_positions,
                    "vary_action_label_positions_by": vary_action_label_positions_by,
                    "font_family": font_family,
                    "font_bold": font_bold,
                    "font_italic": font_italic,
                    "font_size": font_size,
                    "node_size": node_size,
                    "label_bg": label_bg,
                    "label_bg_color": label_bg_color,
                    "label_bg_opacity": label_bg_opacity,
                    "iset_fill": iset_fill,
                    "iset_fill_opacity": iset_fill_opacity,
                    "iset_boundary": iset_boundary,
                    "legend_position": legend_position,
                }
                if custom_colors:
                    settings["custom_colors"] = custom_colors
                if vary_action_label_positions_choices:
                    settings["vary_action_label_positions_choices"] = (
                        vary_action_label_positions_choices
                    )
                settings_yaml = yaml.dump(
                    {base_filename: settings},
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
                with c2:
                    st.download_button(
                        "Settings",
                        settings_yaml,
                        f"{base_filename}_settings.yaml",
                        "text/plain",
                        width="stretch",
                    )

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)


if __name__ == "__main__":
    run_app()
