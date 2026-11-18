import streamlit as st
import tempfile
from pathlib import Path
import os
import sys
import warnings
import dataclasses

# Suppress warnings in the GUI
warnings.filterwarnings("ignore")


# Add src to path if running from local dev
sys.path.insert(0, str(Path(__file__).parent.parent))

from gtdraw import Style, svg, tikz, tex, pdf, png
from gtdraw.core import _count_players, _get_game_levels
from gtdraw.style import _read_block, _strip_block


def _get_scheme_colors(color_scheme: str, num_players: int) -> dict[int, str]:
    """Return {player_index: '#RRGGBB'} for the named colour scheme."""
    CHANCE = "#759138"
    if color_scheme == "gambit":
        palette = {
            0: CHANCE,
            1: "#EA3323",
            2: "#0000FF",
            3: "#FF7F00",
            4: "#800080",
            5: "#00FFFF",
            6: "#FF00FF",
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
                result[i + 1] = (
                    f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"
                )
            return result
        except Exception:
            return {i: "#000000" for i in range(num_players + 1)}
    return {i: "#000000" for i in range(num_players + 1)}


# ── Constants ────────────────────────────────────────────────────────────────

# The app's own default style: gtdraw's defaults, with the colour-blind palette.
# A loaded drawing's style block is read onto it, and a downloaded drawing's block
# records what differs from it.
BASE_STYLE = Style(color_scheme="colorblind")

# ── Session-state snapshot helpers ───────────────────────────────────────────


def _snapshot_settings() -> dict:
    """Capture all layout/aesthetics widget session-state values."""
    snap = {}
    for k, v in st.session_state.items():
        if k.startswith(("gui_", "cp_", "alp_", "lbg_")) or k == "scheme_selector":
            snap[k] = v
    return snap


def _apply_snapshot(snap: dict) -> None:
    """Restore widget session-state from a snapshot."""
    for k, v in snap.items():
        st.session_state[k] = v


# ── Style helpers ────────────────────────────────────────────────────────────


def _drawing_style(text: str) -> Style:
    """The app's base style with the drawing's style block read onto it."""
    return BASE_STYLE.replace(**_read_block(text))


def _drawing_with_block(text: str, style: Style) -> str:
    """The drawing with its style block replaced by one recording how ``style`` differs from the base."""
    return style.to_block(BASE_STYLE) + "\n".join(_strip_block(text)) + "\n"


# Font/size display-label ↔ internal-value maps used when applying a style to the widgets
_FONT_FAMILY_TO_KEY = {
    "rmfamily": "Serif",
    "sffamily": "Sans-Serif",
    "ttfamily": "Monospace",
}
_FONT_SIZE_TO_KEY = {
    "small": "Small",
    "normalsize": "Normal",
    "large": "Large",
    "Large": "Huge",
}


def _apply_style_to_session_state(style: Style) -> None:
    """Set the GUI widgets' session-state keys from a style."""
    settings = dataclasses.asdict(style)
    simple = {
        "scale_factor": "gui_scale_factor",
        "horizontal": "gui_horizontal",
        "mirror": "gui_mirror",
        "edge_thickness": "gui_edge_thickness",
        "node_size": "gui_node_size",
        "action_label_dist": "gui_action_label_dist",
        "iset_fill": "gui_iset_fill",
        "iset_fill_opacity": "gui_iset_fill_opacity",
        "iset_boundary": "gui_iset_boundary",
        "iset_curved": "gui_iset_curved",
        "font_bold": "gui_font_bold",
        "font_italic": "gui_font_italic",
        "legend_position": "gui_legend_position",
        "label_bg_opacity": "gui_label_bg_opacity",
        "vary_action_label_positions": "gui_vary_alp",
    }
    for param, key in simple.items():
        if param in settings:
            st.session_state[key] = settings[param]

    if "font_family" in settings:
        st.session_state["gui_font_family"] = _FONT_FAMILY_TO_KEY.get(
            settings["font_family"], "Serif"
        )
    if "font_size" in settings:
        st.session_state["gui_font_size"] = _FONT_SIZE_TO_KEY.get(
            settings["font_size"], "Normal"
        )

    if "color_scheme" in settings:
        st.session_state["scheme_selector"] = settings["color_scheme"]
        st.session_state.pop("_prev_scheme", None)

    if "custom_colors" in settings and settings["custom_colors"]:
        cc = settings["custom_colors"]
        if 0 in cc:
            st.session_state["cp_chance"] = cc[0]
        for i in range(1, 10):
            if i in cc:
                st.session_state[f"cp_p{i}"] = cc[i]
        st.session_state["scheme_selector"] = "custom"

    # action_label_position
    alp = settings.get("action_label_position")
    alp_by = settings.get("action_label_position_by", "player")
    if alp is not None:
        if isinstance(alp, dict):
            if alp_by == "level":
                st.session_state["gui_positioning_mode"] = "By Level"
                for lv, v in alp.items():
                    st.session_state[f"alp_lv{lv}"] = v
            else:
                st.session_state["gui_positioning_mode"] = "By Player"
                if 0 in alp:
                    st.session_state["alp_chance"] = alp[0]
                for i in range(1, 10):
                    if i in alp:
                        st.session_state[f"alp_p{i}"] = alp[i]
        else:
            st.session_state["gui_positioning_mode"] = "Global"
            st.session_state["gui_alp_global"] = float(alp)

    # iset_curved_bend — must set the mode selectbox key so widgets render correctly
    icb = settings.get("iset_curved_bend")
    icb_by = settings.get("iset_curved_bend_by", "player")
    if icb is not None:
        if isinstance(icb, dict):
            if icb_by == "level":
                st.session_state["gui_iset_curved_bend_mode"] = "By Level"
                for lv, v in icb.items():
                    st.session_state[f"icb_lv{lv}"] = float(v)
            else:
                st.session_state["gui_iset_curved_bend_mode"] = "By Player"
                if 0 in icb:
                    st.session_state["icb_chance"] = float(icb[0])
                for i in range(1, 10):
                    if i in icb:
                        st.session_state[f"icb_p{i}"] = float(icb[i])
        else:
            st.session_state["gui_iset_curved_bend_mode"] = "Global"
            st.session_state["gui_iset_curved_bend"] = float(icb)

    # label_bg
    lb = settings.get("label_bg")
    if lb is not None:
        if lb is False:
            st.session_state["gui_label_bg_enabled"] = False
        elif lb is True:
            st.session_state["gui_label_bg_enabled"] = True
            st.session_state["gui_label_bg_scope"] = "All"
        elif isinstance(lb, dict):
            lb_by = settings.get("label_bg_by", "player")
            st.session_state["gui_label_bg_enabled"] = True
            st.session_state["gui_label_bg_scope"] = (
                "By Player" if lb_by == "player" else "By Level"
            )
            key = "lbg_players" if lb_by == "player" else "lbg_levels"
            st.session_state[key] = [k for k, v in lb.items() if v]

    if "label_bg_style" in settings:
        s = settings["label_bg_style"]
        st.session_state["gui_label_bg_style"] = (
            "White (player colour text)"
            if s == "white_bg"
            else "Player colour (white text)"
        )

    if "vary_action_label_positions_by" in settings:
        _vby_map = {"all": "All", "player": "By Player", "level": "By Level"}
        st.session_state["gui_vary_alp_by"] = _vby_map.get(
            settings["vary_action_label_positions_by"], "All"
        )

    if "vary_action_label_positions_choices" in settings:
        vpc = settings["vary_action_label_positions_choices"]
        if vpc:
            vby = settings.get("vary_action_label_positions_by", "all")
            if vby == "player":
                st.session_state["gui_vary_alp_players"] = list(vpc)
            elif vby == "level":
                st.session_state["gui_vary_alp_levels"] = list(vpc)


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

    st.set_page_config(page_title="GTDraw", layout="wide", page_icon=icon)

    # Sidebar: Title and Input
    if icon_path.exists():
        col1, col2 = st.sidebar.columns([0.25, 0.75])
        with col1:
            st.image(str(icon_path), width=50)
        with col2:
            st.title("GTDraw")
    else:
        st.sidebar.title("🎨 GTDraw")
    st.sidebar.markdown(
        "##### Part of the [Gambit project](https://www.gambit-project.org/)."
    )
    st.sidebar.markdown("📖 **[Documentation](https://www.gambit-project.org/draw/)**")
    st.sidebar.markdown(
        "Welcome to GTDraw! Load a drawing (.ef) or a strategic game table (.tex), then download your publication-ready image.\n\n"
        "To draw a game from a Gambit game file (.efg, .nfg), convert it to a drawing with pygambit first."
    )

    # Find the games directory by walking upward from this file.
    # This handles both editable installs (src/gtdraw/app.py) and
    # regular installs (site-packages/gtdraw/app.py) where the repo
    # root is the current working directory.
    def _find_games_dir() -> "Path | None":
        current = Path(__file__).resolve().parent
        for _ in range(6):
            candidate = current / "games"
            if candidate.is_dir():
                return candidate
            current = current.parent
        candidate = Path.cwd() / "games"
        return candidate if candidate.is_dir() else None

    _games_dir = _find_games_dir()
    base_path = _games_dir.parent if _games_dir else Path(__file__).parent
    example_dir = _games_dir or (base_path / "games")

    game_source = None
    is_sgame = False

    with st.sidebar.expander("📂 Input Drawing", expanded=True):
        options = [("None", "None", "None")]

        if example_dir.exists():
            for e in sorted(example_dir.glob("*.ef")):
                options.append(("EF", e.name, str(e.relative_to(base_path))))
            for e in sorted(example_dir.glob("*.tex")):
                options.append(("Strategic game", e.name, str(e.relative_to(base_path))))

        def format_option(i):
            cat, name, _ = options[i]
            if cat == "None":
                return "None"
            return f"[{cat}] {name}"

        # Default selection
        default_idx = 0
        target_example_path = str(Path("games") / "example.ef")
        for i, opt in enumerate(options):
            if opt[2] == target_example_path:
                default_idx = i
                break

        help_text = (
            "**EF**: a drawing in GTDraw's .ef format.\n\n"
            "**Strategic game**: the LaTeX body of a strategic game (an sgame table), as a .tex file.\n\n"
            "To draw a game from a Gambit game file, convert it to a drawing with "
            "pygambit first."
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
            game_source = str(base_path / example_selection[2])
            is_sgame = game_source.lower().endswith(".tex")

        uploaded_file = st.file_uploader(
            "Or upload your own .ef or .tex file",
            type=["ef", "tex"],
            help="To draw a game from a Gambit game file (.efg, .nfg), convert it to a "
            "drawing with pygambit first.",
        )

    base_filename = "game_tree"
    game_slug = None  # names the loaded drawing
    if uploaded_file:
        base_filename = Path(uploaded_file.name).stem
        game_slug = base_filename
        suffix = f".{uploaded_file.name.split('.')[-1]}"
        is_sgame = suffix.lower() == ".tex"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            game_source = tmp.name
    elif game_source:
        base_filename = Path(game_source).stem
        game_slug = base_filename

    # The drawing's style: the app's base style with the drawing's own style block
    drawing_style = BASE_STYLE
    if game_source and not is_sgame:
        try:
            drawing_style = _drawing_style(
                Path(game_source).read_text(encoding="utf-8")
            )
        except ValueError as e:
            st.sidebar.error(f"The drawing's style block is not valid: {e}")

    # Set the widgets from it when the drawing changes
    _drawing_key = (game_slug, drawing_style)
    if st.session_state.get("_current_drawing", "__unset__") != _drawing_key:
        st.session_state["_current_drawing"] = _drawing_key
        if game_slug:
            _apply_style_to_session_state(drawing_style)
        # Reset snapshot so undo tracking starts fresh for the new drawing
        st.session_state.pop("_last_snap", None)

    # Sidebar: Configuration
    # Tree-specific layout options (not applicable to strategic games)
    horizontal = False
    mirror = False
    scale_factor = 1.0
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
    vary_action_label_positions = False
    vary_action_label_positions_by = "all"
    vary_action_label_positions_choices = None
    action_label_position_by = "player"

    # ── Undo / Redo / Reset buttons ─────────────────────────────────────────
    if not is_sgame:
        _col_undo, _col_redo, _col_reset = st.sidebar.columns(3)
        with _col_undo:
            if st.button(
                "↩ Undo",
                disabled=not st.session_state.get("undo_stack"),
                use_container_width=True,
                help="Undo last settings change",
            ):
                _redo_snap = _snapshot_settings()
                _apply_snapshot(st.session_state["undo_stack"].pop())
                st.session_state.setdefault("redo_stack", []).append(_redo_snap)
                st.session_state["_last_snap"] = _snapshot_settings()
                st.rerun()
        with _col_redo:
            if st.button(
                "↪ Redo",
                disabled=not st.session_state.get("redo_stack"),
                use_container_width=True,
                help="Redo last undone change",
            ):
                _undo_snap = _snapshot_settings()
                _apply_snapshot(st.session_state["redo_stack"].pop())
                st.session_state.setdefault("undo_stack", []).append(_undo_snap)
                st.session_state["_last_snap"] = _snapshot_settings()
                st.rerun()
        with _col_reset:
            if st.button(
                "↺ Reset",
                use_container_width=True,
                help="Restore the style the drawing was loaded with",
                disabled=not game_slug,
            ):
                st.session_state.setdefault("undo_stack", []).append(
                    _snapshot_settings()
                )
                st.session_state["redo_stack"] = []
                _apply_style_to_session_state(drawing_style)
                st.session_state.pop("_prev_scheme", None)
                st.session_state.pop("_last_snap", None)
                st.rerun()

    if not is_sgame:
        with st.sidebar.expander("📐 Layout", expanded=False):
            horizontal = st.checkbox(
                "Horizontal Layout",
                value=False,
                help="Switch between vertical (top-down) and horizontal (left-right) layout.",
                key="gui_horizontal",
            )
            mirror = st.checkbox(
                "Mirror Layout",
                value=False,
                help="Mirror the tree left-to-right by flipping xshift values.",
                key="gui_mirror",
            )

            scale_factor = st.slider(
                "Scale factor",
                0.5,
                2.0,
                1.0,
                0.05,
                help="Scale factor for the entire TikZ diagram.",
                key="gui_scale_factor",
            )

    # Defaults used when aesthetics expander is hidden (strategic-game path)
    color_scheme = "colorblind"
    legend_position = "top-left"
    custom_colors = None
    font_family = "rmfamily"
    font_bold = False
    font_italic = False
    font_size = "normalsize"

    if not is_sgame:
        with st.sidebar.expander("🎨 Aesthetics", expanded=False):
            # Session-state init: default to colorblind
            if "scheme_selector" not in st.session_state:
                st.session_state["scheme_selector"] = "colorblind"

            _num_p = _count_players(game_source) if game_source else 2

            # Step 2: scheme-change → reset pickers to new scheme's defaults
            _prev = st.session_state.get("_prev_scheme")
            _cur = st.session_state["scheme_selector"]
            if _prev != _cur and _cur not in ("default", "custom"):
                for _pnum, _hex in _get_scheme_colors(_cur, _num_p).items():
                    _pk = "cp_chance" if _pnum == 0 else f"cp_p{_pnum}"
                    st.session_state[_pk] = _hex

            # Step 3: colour-change → auto-switch to custom
            if _cur not in ("default", "custom"):
                _defs = _get_scheme_colors(_cur, _num_p)
                for _pnum in range(_num_p + 1):
                    _pk = "cp_chance" if _pnum == 0 else f"cp_p{_pnum}"
                    _val = st.session_state.get(_pk)
                    if (
                        _val is not None
                        and _val.upper() != _defs.get(_pnum, "#000000").upper()
                    ):
                        st.session_state["scheme_selector"] = "custom"
                        break

            # _prev_scheme updated AFTER step 3 so switching back works correctly
            st.session_state["_prev_scheme"] = st.session_state["scheme_selector"]

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
                key="gui_legend_position",
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
                    if all(
                        _picked[k].upper() == _rdefs.get(k, "#000000").upper()
                        for k in _picked
                    ):
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
                key="gui_font_family",
            )
            font_map = {
                "Serif": "rmfamily",
                "Sans-Serif": "sffamily",
                "Monospace": "ttfamily",
            }
            font_family = font_map[font_family_name]

            col1, col2 = st.columns(2)
            with col1:
                font_bold = st.checkbox("Bold", key="gui_font_bold")
            with col2:
                font_italic = st.checkbox("Italic", key="gui_font_italic")

            font_size_name = st.selectbox(
                "Text Size",
                ["Small", "Normal", "Large", "Huge"],
                index=1,
                help="Global text size for the diagram.",
                key="gui_font_size",
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

            num_players = _count_players(game_source) if game_source else 2
            game_levels = (
                _get_game_levels(game_source)
                if game_source
                else list(range(5))
            )

            label_bg_enabled = st.checkbox(
                "Enable Label Background",
                value=False,
                help="Adds a filled background behind label text to improve readability.",
                key="gui_label_bg_enabled",
            )
            if label_bg_enabled:
                label_bg_scope = st.selectbox(
                    "Background applies to",
                    ["All", "By Player", "By Level"],
                    index=0,
                    help="Apply to all labels, or selectively per player or per level.",
                    key="gui_label_bg_scope",
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
                    key="gui_label_bg_style",
                )
                label_bg_style = (
                    "white_bg"
                    if label_bg_style_name.startswith("White")
                    else "player_bg"
                )
                label_bg_opacity = st.slider(
                    "Background Opacity",
                    0.0,
                    1.0,
                    0.8,
                    0.05,
                    key="gui_label_bg_opacity",
                )
            label_bg_color = "white"  # fallback; player colors used automatically

            st.markdown("---")
            st.markdown("##### Action Label Positioning")

            # Vary action label positions
            vary_action_label_positions = st.checkbox(
                "Vary Action Label Positions",
                value=False,
                help="Vary action label positions based on the number of outgoing edges to avoid clashes.",
                key="gui_vary_alp",
            )
            if vary_action_label_positions:
                vary_by = st.selectbox(
                    "Vary by",
                    ["All", "By Player", "By Level"],
                    index=0,
                    help="Apply varying positions to all nodes, or selectively to specific players or levels.",
                    key="gui_vary_alp_by",
                )
                vary_action_label_positions_by = {
                    "All": "all",
                    "By Player": "player",
                    "By Level": "level",
                }[vary_by]
                if vary_by == "By Player":
                    selected_players = st.multiselect(
                        "Apply vary to players",
                        options=list(range(num_players + 1)),
                        default=list(range(num_players + 1)),
                        format_func=lambda x: "Chance" if x == 0 else f"Player {x}",
                        help="Select which players' outgoing edges should have varied label positions.",
                        key="gui_vary_alp_players",
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
                        key="gui_vary_alp_levels",
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
                key="gui_positioning_mode",
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
                    key="gui_alp_global",
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
                key="gui_action_label_dist",
            )

            st.markdown("---")
            st.markdown("##### Edge & Node Styling")
            edge_thickness = st.slider(
                "Edge Thickness", 0.1, 5.0, 1.0, 0.1, key="gui_edge_thickness"
            )
            node_size = st.slider(
                "Node Size",
                0.5,
                5.0,
                1.5,
                0.1,
                help="Size of player nodes in mm.",
                key="gui_node_size",
            )

            st.markdown("---")
            st.markdown("##### Information Sets")
            iset_fill = st.checkbox(
                "Fill Information Sets", value=False, key="gui_iset_fill"
            )
            iset_fill_opacity = st.slider(
                "Fill Opacity",
                0.0,
                1.0,
                0.2,
                0.05,
                disabled=not iset_fill,
                key="gui_iset_fill_opacity",
            )
            iset_boundary = st.selectbox(
                "Boundary Style",
                ["solid", "dotted", "none"],
                index=0,
                key="gui_iset_boundary",
            )
            iset_curved = st.checkbox(
                "Curved Information Sets",
                value=False,
                key="gui_iset_curved",
                help="Draw information sets as curved lines using TikZ 'to[bend left]' paths.",
            )
            bend_mode = st.selectbox(
                "Bend Angle vary by",
                ["Global", "By Player", "By Level"],
                disabled=not iset_curved,
                key="gui_iset_curved_bend_mode",
                help="Set a single global bend angle, or customise per player or per level.",
            )
            iset_curved_bend_by = (
                "player"
                if bend_mode == "By Player"
                else "level"
                if bend_mode == "By Level"
                else "player"
            )

            if bend_mode == "Global" or not iset_curved:
                iset_curved_bend = st.number_input(
                    "Bend Angle",
                    min_value=-90.0,
                    max_value=90.0,
                    value=10.0,
                    step=1.0,
                    disabled=not iset_curved,
                    key="gui_iset_curved_bend",
                    help="Positive values curve upward (bend left), negative values curve downward.",
                )
            elif bend_mode == "By Player":
                iset_curved_bend = {}
                iset_curved_bend[0] = st.number_input(
                    "Chance Bend Angle",
                    -90.0,
                    90.0,
                    0.0,
                    1.0,
                    key="icb_chance",
                    disabled=not iset_curved,
                )
                for i in range(1, num_players + 1):
                    iset_curved_bend[i] = st.number_input(
                        f"Player {i} Bend Angle",
                        -90.0,
                        90.0,
                        0.0,
                        1.0,
                        key=f"icb_p{i}",
                        disabled=not iset_curved,
                    )
            else:  # By Level
                iset_curved_bend = {}
                for lv in game_levels:
                    iset_curved_bend[lv] = st.number_input(
                        f"Level {lv} Bend Angle",
                        -90.0,
                        90.0,
                        0.0,
                        1.0,
                        key=f"icb_lv{lv}",
                        disabled=not iset_curved,
                    )

    # ── Snapshot tracking (undo) ───────────────────────────────
    if not is_sgame and game_source:
        _current_snap = _snapshot_settings()
        _prev_snap = st.session_state.get("_last_snap")
        _MAX_UNDO = 50
        if _prev_snap is not None and _current_snap != _prev_snap:
            _stack = st.session_state.setdefault("undo_stack", [])
            _stack.append(_prev_snap)
            if len(_stack) > _MAX_UNDO:
                _stack.pop(0)
            st.session_state["redo_stack"] = []
        st.session_state["_last_snap"] = _current_snap


    # Main Area: Display
    if not game_source:
        if icon_path.exists():
            c1, c2 = st.columns([0.1, 0.9])
            with c1:
                st.image(str(icon_path), width=80)
            with c2:
                st.title("GTDraw")
            st.markdown(
                "### Part of the [Gambit project](https://www.gambit-project.org/)"
            )
        else:
            st.title("🎨 GTDraw")
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

            if is_sgame:
                # Strategic game: get the LaTeX body (always available, no pdflatex needed)
                tikz_code = tikz(game_source)
                tex_path = tex(game_source, save_to=output_base + ".tex")
                with open(tex_path, "r") as f:
                    tex_data = f.read()

                # Try to render as PNG; fall back gracefully if pdflatex/sgame unavailable
                png_data = None
                pdf_data = None
                sgame_render_error = None
                try:
                    png_path = str(work_dir / f"{base_name}.png")
                    png(game_source, save_to=png_path)
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
                    pdf_path = pdf(game_source, save_to=output_base + ".pdf")
                    with open(pdf_path, "rb") as f:
                        pdf_data = f.read()
                except RuntimeError as e:
                    sgame_render_error = str(e)

                if sgame_render_error:
                    st.warning(
                        "⚠️ Could not compile payoff table to image — pdflatex or the "
                        "`sgame` LaTeX package may not be installed.\n\n"
                        "Install with: `sudo apt-get install texlive-games` (Ubuntu) or "
                        "use a full TeX distribution."
                    )
                    with st.expander("Show pdflatex error details"):
                        st.code(sgame_render_error)
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

            # The style the widgets give. Passed as options so that it, not the
            # drawing's own style block, decides the preview and the downloads.
            current_style = Style(
                scale_factor=scale_factor,
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
                iset_curved=iset_curved,
                iset_curved_bend=iset_curved_bend,
                iset_curved_bend_by=iset_curved_bend_by,
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
            style_options = dataclasses.asdict(current_style)

            svg_path = str(work_dir / f"{base_name}.svg")

            svg_code = svg(
                game_source,
                save_to=svg_path,
                responsive_sizing=True,
                **style_options,
            )

            if not os.path.exists(svg_path):
                st.error("SVG generation failed.")
                return

            with open(svg_path, "r") as f:
                svg_content = f.read()

            # Display the responsive SVG directly
            st.markdown(svg_content, unsafe_allow_html=True)

            # Pre-generate all download formats
            tikz_code = tikz(
                game_source,
                **style_options,
            )

            tex_path = tex(
                game_source,
                save_to=output_base + ".tex",
                **style_options,
            )
            with open(tex_path, "r") as f:
                tex_data = f.read()

            pdf_path = pdf(
                game_source,
                save_to=output_base + ".pdf",
                **style_options,
            )
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()

            png_path = png(
                game_source,
                save_to=output_base + ".png",
                dpi=300,
                **style_options,
            )
            with open(png_path, "rb") as f:
                png_data = f.read()

            # Sidebar: Download Buttons
            with st.sidebar.expander("📥 Downloads", expanded=False):
                # The drawing itself, with a style block for what differs from the base
                with open(game_source, "r", encoding="utf-8") as f:
                    ef_data = _drawing_with_block(f.read(), current_style)

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

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)


if __name__ == "__main__":
    run_app()
