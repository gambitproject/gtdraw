import streamlit as st
import tempfile
from pathlib import Path
import os
import sys
import warnings
import yaml
import hashlib
import inspect

# Suppress warnings in the GUI
warnings.filterwarnings("ignore")


# Add src to path if running from local dev
sys.path.insert(0, str(Path(__file__).parent.parent))

from gtdraw import (
    svg,
    tikz,
    tex,
    pdf,
    png,
    count_players,
    get_game_levels,
    ef_to_efg,
    efg_to_ef,
)
from gtdraw.layout_editor import (
    apply_layout_positions,
    normalise_layout_ef,
    parse_ef_layout,
    positions_changed,
    render_layout_editor,
)


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


def _editor_player_colors(
    color_scheme: str,
    num_players: int,
    custom_colors: dict[int, str] | None = None,
) -> dict[int, str]:
    """Return node colours matching the active publication renderer."""
    if color_scheme == "custom" and custom_colors:
        return {int(player): color for player, color in custom_colors.items()}
    if color_scheme == "default":
        colors = {0: "#FF0000"}
        colors.update({player: "#000000" for player in range(1, num_players + 1)})
        return colors
    return _get_scheme_colors(color_scheme, num_players)


# ── Constants ────────────────────────────────────────────────────────────────

# draw library defaults — used to compute per-game YAML diffs
GTDRAW_DEFAULTS: dict = {
    "scale_factor": 1.0,
    "level_scaling": 1.0,
    "sublevel_scaling": 1.0,
    "width_scaling": 1.0,
    "horizontal": False,
    "mirror": False,
    "shared_terminal_depth": False,
    "color_scheme": "default",
    "edge_thickness": 1.0,
    "action_label_position": 0.5,
    "action_label_position_by": "player",
    "font_family": "rmfamily",
    "font_bold": False,
    "font_italic": False,
    "font_size": "normalsize",
    "custom_colors": None,
    "legend_position": "top-left",
    "action_label_dist": 1.0,
    "iset_fill": False,
    "iset_fill_opacity": 0.2,
    "iset_boundary": "solid",
    "iset_curved": False,
    "iset_curved_bend": 10.0,
    "iset_curved_bend_by": "player",
    "node_size": 1.5,
    "label_bg": False,
    "label_bg_by": "player",
    "label_bg_style": "player_bg",
    "label_bg_color": "white",
    "label_bg_opacity": 0.8,
    "vary_action_label_positions": False,
    "vary_action_label_positions_by": "all",
    "vary_action_label_positions_choices": None,
}

# ── Session-state snapshot helpers ───────────────────────────────────────────


def _snapshot_settings() -> dict:
    """Capture all layout/aesthetics widget session-state values."""
    snap = {}
    for k, v in st.session_state.items():
        if k == "gui_layout_editor":
            continue
        if k.startswith(("gui_", "cp_", "alp_", "lbg_")) or k == "scheme_selector":
            snap[k] = v
    return snap


def _apply_snapshot(snap: dict) -> None:
    """Restore widget session-state from a snapshot."""
    for k, v in snap.items():
        if k == "gui_layout_editor":
            continue
        st.session_state[k] = v


def _settings_stack_entry(snapshot: dict) -> dict:
    return {"kind": "settings", "snapshot": snapshot}


def _layout_stack_entry(layout_key: str, layout_scope: str, ef_text: str) -> dict:
    return {
        "kind": "layout",
        "layout_key": layout_key,
        "layout_scope": layout_scope,
        "ef_text": ef_text,
    }


def _push_stack_entry(stack_name: str, entry: dict, limit: int = 50) -> None:
    stack = st.session_state.setdefault(stack_name, [])
    stack.append(entry)
    if len(stack) > limit:
        del stack[:-limit]


_DRAG_LAYOUT_STATE_PREFIXES = (
    "drag_layout::",
    "drag_layout_undo::",
    "drag_layout_active::",
    "component_drag_layout::",
)
_DRAG_LAYOUT_EPOCH_PREFIX = "drag_layout_epoch::"


def _drag_layout_epoch_key(scope: str | None) -> str:
    return f"{_DRAG_LAYOUT_EPOCH_PREFIX}{scope or '__global__'}"


def _drag_layout_scope_matches(key: str, scope: str | None) -> bool:
    if not scope:
        return True
    return f"::{scope}::" in key or key.endswith(f"::{scope}")


def _bump_drag_layout_epoch(scope: str | None) -> None:
    """Force the Streamlit component to remount on the next render."""
    key = _drag_layout_epoch_key(scope)
    st.session_state[key] = int(st.session_state.get(key, 0)) + 1


def _clear_drag_layout_state(scope: str | None = None) -> None:
    """Clear saved drag layouts, undo stacks, and stale component values."""
    for key in list(st.session_state.keys()):
        if key.startswith(_DRAG_LAYOUT_STATE_PREFIXES) and _drag_layout_scope_matches(
            key, scope
        ):
            st.session_state.pop(key, None)
    _bump_drag_layout_epoch(scope)


def _apply_history_entry(entry: dict, reverse_stack_name: str) -> None:
    """Apply one undo/redo history entry and push the current state opposite."""
    keep_layout_editor = bool(st.session_state.get("gui_layout_editor"))
    if isinstance(entry, dict) and entry.get("kind") == "layout":
        layout_key = entry.get("layout_key")
        layout_scope = entry.get("layout_scope")
        ef_text = entry.get("ef_text")
        if layout_key and isinstance(ef_text, str):
            current_text = st.session_state.get(layout_key)
            if isinstance(current_text, str):
                _push_stack_entry(
                    reverse_stack_name,
                    _layout_stack_entry(layout_key, layout_scope, current_text),
                )
            st.session_state[layout_key] = ef_text
            _bump_drag_layout_epoch(layout_scope)
        if keep_layout_editor:
            st.session_state["gui_layout_editor"] = True
        return

    snapshot = entry.get("snapshot") if isinstance(entry, dict) else entry
    if isinstance(snapshot, dict):
        current_snapshot = _snapshot_settings()
        _apply_snapshot(snapshot)
        _push_stack_entry(
            reverse_stack_name,
            _settings_stack_entry(current_snapshot),
        )
        st.session_state["_last_snap"] = _snapshot_settings()
    if keep_layout_editor:
        st.session_state["gui_layout_editor"] = True


# ── YAML helpers ─────────────────────────────────────────────────────────────


def _yaml_path(base_path: "Path") -> "Path":
    return base_path / "gui_settings.yaml"


def _read_yaml(path: "Path") -> dict:
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return {
            "defaults": data.get("defaults") or {},
            "overrides": data.get("overrides") or {},
        }
    except Exception:
        return {"defaults": {}, "overrides": {}}


def _write_game_settings(path: "Path", game_slug: str, settings: dict) -> None:
    """Write (or clear) per-game overrides in gui_settings.yaml."""
    data = _read_yaml(path)
    if settings:
        data["overrides"][game_slug] = settings
    elif game_slug in data["overrides"]:
        del data["overrides"][game_slug]
    try:
        with open(path, "w") as f:
            f.write("# draw GUI master settings\n")
            f.write(
                "# Per-game overrides are written here automatically as you adjust settings.\n"
            )
            f.write(
                "# Edit the defaults section to change settings that apply to all games.\n"
            )
            f.write(
                "# Consult https://www.gambit-project.org/draw/ for available settings.\n\n"
            )
            yaml.dump(
                data, f, default_flow_style=False, sort_keys=False, allow_unicode=True
            )
    except Exception:
        pass


def _effective_settings_for_game(path: "Path", game_slug: str | None) -> dict:
    """Merge draw defaults ← yaml defaults ← yaml overrides for game.

    Override keys are matched if the slug equals the key or starts with
    key + '/', applied shortest-first so more-specific entries win over
    group-level entries (e.g. 'myerson1991' is applied before
    'myerson1991/fig2_1').
    """
    data = _read_yaml(path)
    merged = {**GTDRAW_DEFAULTS}
    merged.update(data["defaults"] or {})
    if game_slug:
        overrides = data["overrides"] or {}
        for key in sorted(overrides, key=len):
            if game_slug == key or game_slug.startswith(key + "/"):
                merged.update(overrides[key])
    return merged


def _settings_diff(current: dict) -> dict:
    """Return only keys that differ from gtdraw library defaults."""
    return {k: v for k, v in current.items() if v != GTDRAW_DEFAULTS.get(k)}


# Font/size display-label ↔ internal-value maps used by YAML loading
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


def _apply_yaml_to_session_state(settings: dict) -> None:
    """Map draw param names from YAML onto GUI widget session-state keys."""
    simple = {
        "scale_factor": "gui_scale_factor",
        "level_scaling": "gui_level_scaling",
        "sublevel_scaling": "gui_sublevel_scaling",
        "width_scaling": "gui_width_scaling",
        "horizontal": "gui_horizontal",
        "mirror": "gui_mirror",
        "shared_terminal_depth": "gui_shared_terminal_depth",
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
    icon = "🎨"

    st.set_page_config(page_title="GTDraw", layout="wide", page_icon=icon)

    # Sidebar: Title and Input
    st.sidebar.title("🎨 GTDraw")
    st.sidebar.markdown(
        "##### Part of the [Gambit project](https://www.gambit-project.org/)."
    )
    st.sidebar.markdown("📖 **[Documentation](https://www.gambit-project.org/draw/)**")
    st.sidebar.markdown(
        "Welcome to GTDraw! Load a game in EF, EFG, or NFG format, then download your publication-ready image."
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

        def format_option(i):
            cat, name, _ = options[i]
            if cat == "None":
                return "None"
            return f"[{cat}] {name}"

        default_idx = 0

        help_text = "**Catalog**: Games from Gambit's catalog."

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

        uploaded_file = st.file_uploader(
            "Or upload your own .ef, .efg, or .nfg file", type=["ef", "efg", "nfg"]
        )

    base_filename = "game_tree"
    game_slug = None  # key for per-game YAML settings
    if uploaded_file:
        base_filename = Path(uploaded_file.name).stem
        game_slug = base_filename
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
            game_slug = base_filename
        else:
            base_filename = (
                getattr(game_source, "title", "catalog_game")
                .replace(" ", "_")
                .replace("/", "_")
            )
            if not base_filename:
                base_filename = "catalog_game"
            # For catalog games, use the catalog slug (e.g. "watson2013/fig1") as key
            if example_selection[0] == "Catalog":
                game_slug = example_selection[2]
            else:
                game_slug = base_filename

    # Apply per-game settings from YAML when game changes
    _yaml = _yaml_path(base_path)
    _prev_slug = st.session_state.get("_current_game_slug", "__unset__")
    if _prev_slug != game_slug:
        st.session_state["_current_game_slug"] = game_slug
        if game_slug and _yaml.exists():
            _loaded = _effective_settings_for_game(_yaml, game_slug)
            _apply_yaml_to_session_state(_loaded)
            # Pre-populate _last_saved_params with the loaded diff so the
            # save-on-change block doesn't immediately overwrite the just-loaded settings
            st.session_state["_last_saved_params"] = _settings_diff(_loaded)
        else:
            st.session_state.pop("_last_saved_params", None)
        # Reset snapshot so undo tracking starts fresh for the new game
        st.session_state.pop("_last_snap", None)

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
    vary_action_label_positions = False
    vary_action_label_positions_by = "all"
    vary_action_label_positions_choices = None
    action_label_position_by = "player"
    layout_editor_enabled = False

    # ── Undo / Redo / Reset buttons ─────────────────────────────────────────
    if not is_nfg:
        _col_undo, _col_redo, _col_reset = st.sidebar.columns(3)
        with _col_undo:
            if st.button(
                "↩ Undo",
                disabled=not st.session_state.get("undo_stack"),
                use_container_width=True,
                help="Undo last settings or layout change",
            ):
                _apply_history_entry(
                    st.session_state["undo_stack"].pop(),
                    "redo_stack",
                )
                st.rerun()
        with _col_redo:
            if st.button(
                "↪ Redo",
                disabled=not st.session_state.get("redo_stack"),
                use_container_width=True,
                help="Redo last undone settings or layout change",
            ):
                _apply_history_entry(
                    st.session_state["redo_stack"].pop(),
                    "undo_stack",
                )
                st.rerun()
        with _col_reset:
            if st.button(
                "↺ Reset",
                use_container_width=True,
                help="Restore defaults from gui_settings.yaml",
                disabled=not game_slug,
            ):
                _push_stack_entry(
                    "undo_stack",
                    _settings_stack_entry(_snapshot_settings()),
                )
                st.session_state["redo_stack"] = []
                _write_game_settings(_yaml, game_slug, {})
                _loaded = _effective_settings_for_game(_yaml, game_slug)
                _apply_yaml_to_session_state(_loaded)
                st.session_state["gui_layout_editor"] = False
                _clear_drag_layout_state(game_slug)
                st.session_state.pop("_prev_scheme", None)
                st.session_state.pop("_last_snap", None)
                st.rerun()

        layout_editor_enabled = st.sidebar.checkbox(
            "Layout editor",
            value=False,
            key="gui_layout_editor",
            help="Drag nodes and use the adjusted layout for previews and downloads.",
        )

    if not is_nfg:
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

            if is_efg:
                shared_terminal_depth = st.checkbox(
                    "Shared Terminal Node Depth", False, key="gui_shared_terminal_depth"
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

            if is_efg:
                level_scaling = st.slider(
                    "Level Spacing", 0.0, 5.0, 1.0, 0.05, key="gui_level_scaling"
                )
                sublevel_scaling = st.slider(
                    "Sublevel Spacing", 0.0, 5.0, 1.0, 0.05, key="gui_sublevel_scaling"
                )
                width_scaling = st.slider(
                    "Width Spacing", 0.0, 5.0, 1.0, 0.05, key="gui_width_scaling"
                )

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

            num_players = count_players(game_source) if game_source else 2
            game_levels = (
                get_game_levels(
                    game_source,
                    level_scaling=level_scaling,
                    sublevel_scaling=sublevel_scaling,
                )
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

    # ── Snapshot tracking (undo) and YAML save ───────────────────────────────
    if not is_nfg and game_source:
        _current_snap = _snapshot_settings()
        _prev_snap = st.session_state.get("_last_snap")
        if _prev_snap is not None and _current_snap != _prev_snap:
            _push_stack_entry(
                "undo_stack",
                _settings_stack_entry(_prev_snap),
            )
            st.session_state["redo_stack"] = []
        st.session_state["_last_snap"] = _current_snap

        if game_slug and _yaml.exists():
            _current_params = {
                "scale_factor": scale_factor,
                "level_scaling": level_scaling,
                "sublevel_scaling": sublevel_scaling,
                "width_scaling": width_scaling,
                "horizontal": horizontal,
                "mirror": mirror,
                "shared_terminal_depth": shared_terminal_depth,
                "color_scheme": color_scheme,
                "custom_colors": custom_colors,
                "edge_thickness": edge_thickness,
                "action_label_position": action_label_position,
                "action_label_position_by": action_label_position_by,
                "font_family": font_family,
                "font_bold": font_bold,
                "font_italic": font_italic,
                "font_size": font_size,
                "legend_position": legend_position,
                "action_label_dist": action_label_dist,
                "iset_fill": iset_fill,
                "iset_fill_opacity": iset_fill_opacity,
                "iset_boundary": iset_boundary,
                "iset_curved": iset_curved,
                "iset_curved_bend": iset_curved_bend,
                "iset_curved_bend_by": iset_curved_bend_by,
                "node_size": node_size,
                "label_bg": label_bg,
                "label_bg_by": label_bg_by,
                "label_bg_style": label_bg_style,
                "label_bg_opacity": label_bg_opacity,
                "vary_action_label_positions": vary_action_label_positions,
                "vary_action_label_positions_by": vary_action_label_positions_by,
                "vary_action_label_positions_choices": vary_action_label_positions_choices,
            }
            _diff = _settings_diff(_current_params)
            if _diff != st.session_state.get("_last_saved_params"):
                _write_game_settings(_yaml, game_slug, _diff)
                st.session_state["_last_saved_params"] = _diff

    # Main Area: Display
    if not game_source:
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
            render_game_source = game_source
            active_ef_source = None

            if is_nfg:
                # NFG: get the LaTeX body (always available, no pdflatex needed)
                tikz_code = tikz(game=game_source)
                tex_path = tex(game=game_source, save_to=output_base + ".tex")
                with open(tex_path, "r") as f:
                    tex_data = f.read()

                # Try to render as PNG; fall back gracefully if pdflatex/sgame unavailable
                png_data = None
                pdf_data = None
                nfg_render_error = None
                try:
                    png_path = str(work_dir / f"{base_name}.png")
                    png(game=game_source, save_to=png_path)
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
                    pdf_path = pdf(game=game_source, save_to=output_base + ".pdf")
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

            if layout_editor_enabled:
                try:
                    st.markdown("#### Editor layout")
                    base_ef_path = work_dir / f"{base_name}_layout_base.ef"
                    if is_efg:
                        efg_to_ef(
                            game_source,
                            save_to=str(base_ef_path),
                            level_scaling=level_scaling,
                            sublevel_scaling=sublevel_scaling,
                            width_scaling=width_scaling,
                            shared_terminal_depth=shared_terminal_depth,
                        )
                        base_ef_text = base_ef_path.read_text(encoding="utf-8")
                    else:
                        base_ef_text = Path(game_source).read_text(encoding="utf-8")

                    source_hash = hashlib.sha1(
                        base_ef_text.encode("utf-8")
                    ).hexdigest()[:12]
                    layout_scope = game_slug or base_filename
                    layout_key = (
                        f"drag_layout::{layout_scope}::{source_hash}::"
                        f"{level_scaling}:{sublevel_scaling}:{width_scaling}:"
                        f"{shared_terminal_depth}"
                    )
                    st.session_state[f"drag_layout_active::{layout_scope}"] = layout_key

                    if layout_key not in st.session_state:
                        st.session_state[layout_key] = normalise_layout_ef(
                            base_ef_text
                        )

                    current_ef_text = st.session_state[layout_key]
                    editable_layout = parse_ef_layout(current_ef_text)
                    editor_colors = _editor_player_colors(
                        color_scheme,
                        count_players(render_game_source),
                        custom_colors,
                    )
                    layout_epoch = st.session_state.get(
                        _drag_layout_epoch_key(layout_scope), 0
                    )
                    editor_kwargs = {
                        "key": f"component_{layout_key}::{layout_epoch}",
                    }
                    if "player_colors" in inspect.signature(
                        render_layout_editor
                    ).parameters:
                        editor_kwargs["player_colors"] = editor_colors
                    drag_result = render_layout_editor(
                        editable_layout,
                        **editor_kwargs,
                    )
                    if (
                        isinstance(drag_result, dict)
                        and isinstance(drag_result.get("positions"), dict)
                        and positions_changed(
                            editable_layout, drag_result["positions"]
                        )
                    ):
                        _push_stack_entry(
                            "undo_stack",
                            _layout_stack_entry(
                                layout_key,
                                layout_scope,
                                current_ef_text,
                            ),
                        )
                        st.session_state["redo_stack"] = []
                        st.session_state[layout_key] = apply_layout_positions(
                            current_ef_text,
                            drag_result["positions"],
                        )
                        st.rerun()

                    active_ef_path = work_dir / f"{base_name}_dragged.ef"
                    active_ef_path.write_text(
                        st.session_state[layout_key],
                        encoding="utf-8",
                    )
                    active_ef_source = str(active_ef_path)
                    render_game_source = active_ef_source
                except Exception as layout_err:
                    st.warning(f"Layout editor unavailable: {layout_err}")

            svg_path = str(work_dir / f"{base_name}.svg")

            svg_code = svg(
                game=render_game_source,
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

            if not os.path.exists(svg_path):
                st.error("SVG generation failed.")
                return

            with open(svg_path, "r") as f:
                svg_content = f.read()

            # Display the responsive SVG directly
            if layout_editor_enabled:
                st.markdown("---")
                st.markdown("#### Displayed layout")
            st.markdown(svg_content, unsafe_allow_html=True)

            # Pre-generate all download formats
            tikz_code = tikz(
                game=render_game_source,
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

            tex_path = tex(
                game=render_game_source,
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
            with open(tex_path, "r") as f:
                tex_data = f.read()

            pdf_path = pdf(
                game=render_game_source,
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
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()

            png_path = png(
                game=render_game_source,
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
            with open(png_path, "rb") as f:
                png_data = f.read()

            # Sidebar: Download Buttons
            with st.sidebar.expander("📥 Downloads", expanded=False):
                # Pre-generate EF and EFG data for download
                ef_data = None
                efg_data = None
                try:
                    if active_ef_source:
                        with open(active_ef_source, "r") as f:
                            ef_data = f.read()
                        efg_download_path = ef_to_efg(
                            active_ef_source,
                            save_to=output_base + ".efg",
                        )
                        with open(efg_download_path, "r") as f:
                            efg_data = f.read()
                    elif is_efg:
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
