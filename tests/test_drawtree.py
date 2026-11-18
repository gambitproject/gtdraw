"""
Test suite for draw module.

This module contains comprehensive tests for the game tree drawing functionality,
including unit tests for utility functions, integration tests for file processing,
and validation of TikZ output generation.
"""

import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module under test
import gtdraw.core as core


class TestUtilityFunctions:
    """Test utility functions for mathematical operations and formatting."""

    def test_fformat_default_places(self):
        """Test fformat with default 3 decimal places."""
        assert core.fformat(3.14159) == "3.142"
        assert core.fformat(3.0) == "3"
        assert core.fformat(3.100) == "3.1"

    def test_fformat_custom_places(self):
        """Test fformat with custom decimal places."""
        assert core.fformat(3.14159, 2) == "3.14"
        assert core.fformat(3.14159, 0) == "3"
        assert core.fformat(3.14159, 5) == "3.14159"

    def test_fformat_trailing_zeros(self):
        """Test fformat removes trailing zeros."""
        assert core.fformat(2.5000) == "2.5"
        assert core.fformat(2.0000) == "2"

    def test_coord(self):
        """Test coordinate pair formatting."""
        assert core.coord(1.0, 2.0) == "(1,2)"
        assert core.coord(3.14, 2.71) == "(3.14,2.71)"
        assert core.coord(-1.5, 0.0) == "(-1.5,0)"

    def test_twonorm(self):
        """Test Euclidean length calculation."""
        assert core.twonorm([3, 4]) == 5.0
        assert core.twonorm([1, 0]) == 1.0
        assert core.twonorm([0, 0]) == 0.0

    def test_aeq(self):
        """Test almost equal comparison."""
        assert core.aeq(1e-10, 0)  # Very small number should be considered zero
        assert core.aeq(1.0, 1.0)
        assert not core.aeq(1.0, 2.0)
        assert core.aeq(1.0, 1.0 + 1e-10)  # Numbers within epsilon should be equal

    def test_degrees(self):
        """Test angle calculation in degrees."""
        assert abs(core.degrees([1, 0]) - 0) < 1e-6
        assert abs(core.degrees([0, 1]) - 90) < 1e-6
        assert abs(core.degrees([-1, 0]) - 180) < 1e-6
        assert abs(core.degrees([0, -1]) - (-90)) < 1e-6

    def test_stretch(self):
        """Test vector stretching to desired length."""
        result = core.stretch([3, 4], 10)
        assert abs(core.twonorm(result) - 10) < 1e-6
        assert abs(result[0] - 6) < 1e-6
        assert abs(result[1] - 8) < 1e-6

    def test_det(self):
        """Test determinant calculation."""
        assert core.det(1, 2, 3, 4) == (1 * 4 - 2 * 3)
        assert core.det(2, 0, 0, 3) == 6


class TestStringParsing:
    """Test string parsing functions."""

    def test_splitnumtext_basic(self):
        """Test basic number-text splitting."""
        assert core.splitnumtext("2a") == (2.0, "a")
        assert core.splitnumtext(".3xyz") == (0.3, "xyz")
        assert core.splitnumtext("a") == (1, "a")
        assert core.splitnumtext("22.2xyz") == (22.2, "xyz")

    def test_splitnumtext_edge_cases(self):
        """Test edge cases for number-text splitting."""
        assert core.splitnumtext("") == (1, "")
        assert core.splitnumtext("123") == (123.0, "")
        assert core.splitnumtext(".") == (1, "")


class TestNodeOperations:
    """Test node-related operations."""

    def test_setnodeid(self):
        """Test node ID creation."""
        assert core.setnodeid(1.0, "test") == "1,test"
        assert core.setnodeid(0.5, "node") == "0.5,node"

    def test_cleannodeid(self):
        """Test node ID standardization."""
        # Mock the error function to avoid output during tests
        with patch("gtdraw.core.error"):
            assert core.cleannodeid("1,test") == "1,test"
            assert core.cleannodeid("0.5,node") == "0.5,node"
            # Test error cases
            core.cleannodeid("invalid")  # Should handle gracefully
            core.cleannodeid("x,test")  # Invalid level


class TestOutputRoutines:
    """Test output and formatting functions."""

    def test_outall(self):
        """Test output stream printing."""
        test_stream = ["line1", "line2", "line3"]
        with patch("builtins.print") as mock_print:
            core.outall(test_stream)
            assert mock_print.call_count == 3

    def test_outs(self):
        """Test single string output."""
        test_stream = []
        core.outs("test", test_stream)
        assert test_stream == ["test"]

    def test_comment(self):
        """Test comment output."""
        with patch("gtdraw.core.outs") as mock_outs:
            core.comment("test comment")
            mock_outs.assert_called_with("%% test comment")


class TestFileOperations:
    """Test file reading and processing."""

    def test_readfile(self):
        """Test file reading with line processing."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("line 1\n")
            f.write("  line 2 with spaces  \n")
            f.write("\n")  # Empty line
            f.write("line 3\n")
            temp_filename = f.name

        try:
            result = core.readfile(temp_filename)
            expected = ["line 1", "line 2 with spaces", "line 3"]
            assert result == expected
        finally:
            os.unlink(temp_filename)

    def test_readfile_nonexistent(self):
        """Test file reading with non-existent file."""
        with pytest.raises(FileNotFoundError):
            core.readfile("nonexistent_file.txt")


class TestCommandLineProcessing:
    """Test command-line argument processing."""

    def test_commandline_scale(self):
        """Test scale argument processing."""
        original_scale = core.scale
        try:
            core.commandline(["core.py", "scale=2.5"])
            assert core.scale == 2.5
        finally:
            core.scale = original_scale

    def test_commandline_grid(self):
        """Test grid argument processing."""
        original_grid = core.grid
        try:
            core.commandline(["core.py", "grid"])
            assert core.grid is True
        finally:
            core.grid = original_grid

    def test_commandline_file(self):
        """Test file argument processing."""
        original_ef_file = getattr(core, "ef_file", None)
        try:
            core.commandline(["core.py", "test_game.ef"])
            assert core.ef_file == "test_game.ef"
        finally:
            if original_ef_file is not None:
                core.ef_file = original_ef_file

    def test_commandline_invalid_scale(self):
        """Test invalid scale argument handling."""
        original_scale = core.scale
        try:
            with patch("gtdraw.core.outs") as mock_outs:
                core.commandline(["core.py", "scale=invalid"])
                # Should output error message
                mock_outs.assert_called()
                # Scale should remain unchanged
                assert core.scale == original_scale
        finally:
            core.scale = original_scale


class TestPlayerHandling:
    """Test player parsing and management."""

    def test_player_basic(self):
        """Test basic player parsing."""
        words = ["player", "1"]
        with patch("gtdraw.core.defout"):
            p, advance = core.player(words)
            assert p == 1
            assert advance == 2

    def test_player_with_name(self):
        """Test player parsing with name."""
        words = ["player", "2", "name", "Alice"]
        with patch("gtdraw.core.defout"):
            p, advance = core.player(words)
            assert p == 2
            assert advance == 4
            assert core.playername[2] == "Alice"

    def test_player_invalid_number(self):
        """Test player parsing with invalid number."""
        words = ["player", "invalid"]
        with patch("gtdraw.core.error") as mock_error:
            p, advance = core.player(words)
            assert p == -1
            mock_error.assert_called()


class TestGeometryFunctions:
    """Test geometric operations for tree layout."""

    def test_isonlineseg_basic(self):
        """Test point-on-line-segment detection."""
        # Point on line segment
        assert core.isonlineseg([0, 0], [1, 1], [2, 2]) is True
        # Point on line segment (slope 2)
        assert core.isonlineseg([0, 0], [1, 2], [2, 4]) is True
        # Point not on line segment
        assert core.isonlineseg([0, 0], [1, 3], [2, 4]) is False
        # Point at endpoint
        assert core.isonlineseg([0, 0], [0, 0], [1, 1]) is True

    def test_makearc_basic(self):
        """Test arc generation."""
        # Test with simple coordinates
        result = core.makearc([0, 0], [1, 0], [2, 0])
        assert isinstance(result, str)
        assert "arc(" in result


class TestGTDrawFunction:
    """Test the new streamlined draw function."""

    def test_draw_basic(self):
        """Test basic draw functionality."""
        # Create a simple .ef file for testing
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\n")
            ef_file.write("level 0 node root player 1\n")
            ef_file.write("level 1 node left from 0,root player 2 payoffs 1 2\n")
            ef_file_path = ef_file.name

        try:
            result = core.tikz(ef_file_path)

            # Verify the result contains expected components
            assert isinstance(result, str)
            assert len(result) > 0
            assert "\\usetikzlibrary{shapes}" in result
            assert "\\usetikzlibrary{arrows.meta}" in result
            assert "\\begin{tikzpicture}" in result
            assert "\\end{tikzpicture}" in result
            # Check for built-in macro definitions
            assert "\\newdimen\\ndiam" in result
            assert "\\ndiam1.5mm" in result
            assert "\\newdimen\\paydown" in result
            assert "\\paydown2.5ex" in result

        finally:
            os.unlink(ef_file_path)

    def test_draw_returns_drawing_with_tikz_and_source(self, tmp_path):
        """draw returns a Drawing: .tikz is the TikZ code and .source the document."""
        ef = tmp_path / "g.ef"
        ef.write_text("player 1\nlevel 0 node root player 1\n")
        d = core.draw(str(ef))
        assert isinstance(d, core.Drawing)
        assert d.tikz == core.tikz(str(ef))
        assert d.source == core.latex_wrapper(d.tikz)

    def test_draw_compiles_only_when_displayed_and_once(self, tmp_path):
        """Making a Drawing compiles nothing; displaying it compiles once and caches."""
        ef = tmp_path / "g.ef"
        ef.write_text("player 1\nlevel 0 node root player 1\n")
        with patch("gtdraw.core._pdf_bytes", return_value=b"%PDF") as mk_pdf, patch(
            "gtdraw.core._pdftocairo", return_value=b"<svg></svg>"
        ) as mk_svg:
            d = core.draw(str(ef))
            assert mk_pdf.call_count == 0 and mk_svg.call_count == 0
            assert d._repr_svg_() == "<svg></svg>"
            assert d._repr_svg_() == "<svg></svg>"
            assert mk_pdf.call_count == 1 and mk_svg.call_count == 1
            assert mk_svg.call_args.args[1] == ["-svg"]

    def test_core_does_not_import_ipython(self):
        """Drawing and draw need no IPython: import and draw in a process without it."""
        code = (
            "import sys\n"
            "sys.modules['IPython'] = None\n"
            "sys.modules['jupyter_tikz'] = None\n"
            "import io, gtdraw\n"
            "d = gtdraw.draw(io.StringIO('player 1\\nlevel 0 node root player 1\\n'))\n"
            "assert '\\\\begin{tikzpicture}' in d.tikz\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr

    def test_draw_with_options(self):
        """Test draw with different options."""
        # Create a simple .ef file for testing
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\n")
            ef_file.write("level 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Test with scale
            result_scaled = core.tikz(ef_file_path, scale_factor=2.0)
            assert "scale=1.6" in result_scaled  # 2 * 0.8

            # Test with grid
            result_grid = core.tikz(ef_file_path, show_grid=True)
            assert "\\draw [help lines, color=green]" in result_grid

            # Test without grid (default)
            result_no_grid = core.tikz(ef_file_path, show_grid=False)
            assert "% \\draw [help lines, color=green]" in result_no_grid

        finally:
            os.unlink(ef_file_path)

    def test_draw_missing_files(self):
        """Test draw with missing files."""
        # Test with missing .ef file
        with pytest.raises(FileNotFoundError):
            core.tikz("nonexistent.ef")

        # Test with valid .ef file (should work with built-in macros)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            result = core.tikz(ef_file_path)
            # Should work with built-in macros
            assert "\\begin{tikzpicture}" in result
        finally:
            os.unlink(ef_file_path)


class TestPngGeneration:
    """Test PNG generation functionality."""

    def test_png_missing_file(self):
        """Test PNG generation with missing .ef file."""
        with pytest.raises(FileNotFoundError):
            core.png("nonexistent.ef")

    @patch("gtdraw.core.subprocess.run")
    def test_png_pdflatex_not_found(self, mock_run):
        """Test PNG generation when pdflatex is not available."""
        # Mock pdflatex not being found
        mock_run.side_effect = FileNotFoundError("pdflatex not found")

        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with pytest.raises(RuntimeError, match="pdflatex not found"):
                core.png(ef_file_path)
        finally:
            os.unlink(ef_file_path)

    def test_png_default_parameters(self):
        """Test PNG generation with default parameters."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Mock both pdflatex and convert being unavailable to test error handling
            with patch("gtdraw.core.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")

                with pytest.raises(RuntimeError):
                    core.png(ef_file_path)
        finally:
            os.unlink(ef_file_path)

    def test_png_custom_dpi(self):
        """Test PNG generation with custom DPI setting."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Test that custom DPI is handled properly
            with patch("gtdraw.core.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")

                with pytest.raises(RuntimeError):
                    core.png(ef_file_path, dpi=600)
        finally:
            os.unlink(ef_file_path)

    def test_png_output_filename(self):
        """Test PNG generation with custom output filename."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with patch("gtdraw.core.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")

                with pytest.raises(RuntimeError):
                    core.png(ef_file_path, save_to="custom_name.png")
        finally:
            os.unlink(ef_file_path)


class TestSvgGeneration:
    """Test SVG generation functionality."""

    def test_svg_missing_file(self):
        with pytest.raises(FileNotFoundError):
            core.svg("nonexistent.ef")

    @patch("gtdraw.core.subprocess.run")
    def test_svg_pdflatex_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("pdflatex not found")
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with pytest.raises(RuntimeError, match="pdflatex not found"):
                core.svg(ef_file_path)
        finally:
            os.unlink(ef_file_path)

    def test_svg_default_parameters(self):
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with patch("gtdraw.core.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")
                with pytest.raises(RuntimeError):
                    core.svg(ef_file_path)
        finally:
            os.unlink(ef_file_path)

    def test_svg_output_filename(self):
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with patch("gtdraw.core.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")
                with pytest.raises(RuntimeError):
                    core.svg(ef_file_path, save_to="custom_name.svg")
        finally:
            os.unlink(ef_file_path)


class TestTexGeneration:
    """Test LaTeX document generation functionality."""

    def test_tex_missing_file(self):
        """Test LaTeX generation with missing .ef file."""
        with pytest.raises(FileNotFoundError):
            core.tex("nonexistent.ef")

    def test_tex_default_parameters(self):
        """Test LaTeX generation with default parameters."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Generate LaTeX file
            tex_path = core.tex(ef_file_path)

            # Verify the file was created and contains expected content
            assert os.path.exists(tex_path)

            with open(tex_path, "r") as f:
                content = f.read()

            # Check for LaTeX document structure
            assert "\\documentclass[tikz,border=10pt]{standalone}" in content
            assert "\\begin{document}" in content
            assert "\\end{document}" in content
            assert "\\begin{tikzpicture}" in content
            assert "\\end{tikzpicture}" in content

            # Clean up generated file
            os.unlink(tex_path)

        finally:
            os.unlink(ef_file_path)

    def test_tex_custom_filename(self):
        """Test LaTeX generation with custom output filename."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            custom_filename = "custom_output.tex"
            tex_path = core.tex(ef_file_path, save_to=custom_filename)

            # Verify the custom filename was used
            assert tex_path.endswith(custom_filename)
            assert os.path.exists(custom_filename)

            # Clean up
            os.unlink(custom_filename)

        finally:
            os.unlink(ef_file_path)

    def test_tex_with_scale_and_grid(self):
        """Test LaTeX generation with scale and grid options."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            tex_path = core.tex(ef_file_path, scale_factor=2.0, show_grid=True)

            # Verify the file was created
            assert os.path.exists(tex_path)

            with open(tex_path, "r") as f:
                content = f.read()

            # Check for scale and grid options
            assert "scale=1.6" in content  # 2 * 0.8
            assert "\\draw [help lines, color=green]" in content

            # Clean up
            os.unlink(tex_path)

        finally:
            os.unlink(ef_file_path)


class TestCommandlineArguments:
    """Test command line argument parsing for new functionality."""

    def test_commandline_png_flag(self):
        """Test --png flag parsing."""
        result = core.commandline(["core.py", "test.ef", "--png"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert output_mode == "png"
        assert not pdf_requested
        assert png_requested
        assert not svg_requested
        assert not tex_requested
        assert output_file is None
        assert dpi is None

    def test_commandline_png_with_dpi(self):
        """Test --png flag with --dpi option."""
        result = core.commandline(["core.py", "test.ef", "--png", "--dpi=600"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert output_mode == "png"
        assert not pdf_requested
        assert png_requested
        assert not svg_requested
        assert not tex_requested
        assert output_file is None
        assert dpi == 600

    def test_commandline_png_output_file(self):
        """Test PNG output with custom filename."""
        result = core.commandline(["core.py", "test.ef", "--output=custom.png"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert output_mode == "png"
        assert not pdf_requested
        assert png_requested
        assert not svg_requested
        assert not tex_requested
        assert output_file == "custom.png"
        assert dpi is None

    def test_commandline_pdf_output_file(self):
        """Test PDF output with custom filename."""
        result = core.commandline(["core.py", "test.ef", "--output=custom.pdf"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert output_mode == "pdf"
        assert pdf_requested
        assert not png_requested
        assert not svg_requested
        assert not tex_requested
        assert output_file == "custom.pdf"
        assert dpi is None

    def test_commandline_tex_flag(self):
        """Test --tex flag parsing."""
        result = core.commandline(["core.py", "test.ef", "--tex"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert output_mode == "tex"
        assert not pdf_requested
        assert not png_requested
        assert not svg_requested
        assert tex_requested
        assert output_file is None
        assert dpi is None

    def test_commandline_tex_output_file(self):
        """Test LaTeX output with custom filename."""
        result = core.commandline(["core.py", "test.ef", "--output=custom.tex"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert output_mode == "tex"
        assert not pdf_requested
        assert not png_requested
        assert not svg_requested
        assert tex_requested
        assert output_file == "custom.tex"
        assert dpi is None

    def test_commandline_invalid_dpi(self):
        """Test invalid DPI values."""
        # Too low DPI should default to 300
        result = core.commandline(["core.py", "test.ef", "--png", "--dpi=50"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert dpi == 300  # Should default to 300 for out-of-range values

        # Too high DPI should default to 300
        result = core.commandline(["core.py", "test.ef", "--png", "--dpi=5000"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert dpi == 300  # Should default to 300 for out-of-range values

    def test_commandline_invalid_dpi_string(self):
        """Test non-numeric DPI values."""
        result = core.commandline(["core.py", "test.ef", "--png", "--dpi=high"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert dpi == 300  # Should default to 300 for invalid values

    def test_commandline_svg_flag(self):
        """Test --svg flag parsing."""
        result = core.commandline(["core.py", "test.ef", "--svg"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert output_mode == "svg"
        assert not pdf_requested
        assert not png_requested
        assert svg_requested
        assert not tex_requested
        assert output_file is None
        assert dpi is None

    def test_commandline_svg_output_file(self):
        """Test SVG output with custom filename."""
        result = core.commandline(["core.py", "test.ef", "--output=custom.svg"])
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert output_mode == "svg"
        assert not pdf_requested
        assert not png_requested
        assert svg_requested
        assert not tex_requested
        assert output_file == "custom.svg"
        assert dpi is None
        assert action_label_dist == 1.0


def test_commandline_action_label_dist():
    """Test parsing of action label distance flag."""
    result = core.commandline(["gtdraw", "game.ef", "--action-label-dist=2.5"])
    assert result[15] == 2.5


def test_commandline_action_label_position_by_player():
    """Test that --action-label-position-by=player is parsed correctly (default)."""
    result = core.commandline(
        ["gtdraw", "game.ef", "--action-label-position-by=player"]
    )
    (
        *_rest,
        vary_action_label_positions,
        action_label_position_by,
        vary_action_label_positions_by,
        vary_action_label_positions_choices,
    ) = result
    assert action_label_position_by == "player"


def test_commandline_action_label_position_by_level():
    """Test that --action-label-position-by=level is parsed correctly."""
    result = core.commandline(["gtdraw", "game.ef", "--action-label-position-by=level"])
    (
        *_rest,
        vary_action_label_positions,
        action_label_position_by,
        vary_action_label_positions_by,
        vary_action_label_positions_choices,
    ) = result
    assert action_label_position_by == "level"


def test_commandline_vary_action_label_positions_by_player():
    """Test that --vary-action-label-positions-by=player is parsed correctly."""
    result = core.commandline(
        [
            "gtdraw",
            "game.ef",
            "--vary-action-label-positions",
            "--vary-action-label-positions-by=player",
        ]
    )
    (
        *_rest,
        vary_action_label_positions,
        action_label_position_by,
        vary_action_label_positions_by,
        vary_action_label_positions_choices,
    ) = result
    assert vary_action_label_positions is True
    assert vary_action_label_positions_by == "player"


def test_commandline_vary_action_label_positions_by_level():
    """Test that --vary-action-label-positions-by=level is parsed correctly."""
    result = core.commandline(
        [
            "gtdraw",
            "game.ef",
            "--vary-action-label-positions",
            "--vary-action-label-positions-by=level",
        ]
    )
    (
        *_rest,
        vary_action_label_positions,
        action_label_position_by,
        vary_action_label_positions_by,
        vary_action_label_positions_choices,
    ) = result
    assert vary_action_label_positions is True
    assert vary_action_label_positions_by == "level"


def test_commandline_vary_action_label_positions_choices():
    """Test that --vary-action-label-positions-choices parses a comma-separated list."""
    result = core.commandline(
        [
            "gtdraw",
            "game.ef",
            "--vary-action-label-positions",
            "--vary-action-label-positions-by=player",
            "--vary-action-label-positions-choices=0,1",
        ]
    )
    (
        *_rest,
        vary_action_label_positions,
        action_label_position_by,
        vary_action_label_positions_by,
        vary_action_label_positions_choices,
    ) = result
    assert vary_action_label_positions is True
    assert vary_action_label_positions_by == "player"
    assert vary_action_label_positions_choices == [0, 1]


def test_commandline_vary_choices_level():
    """Test --vary-action-label-positions-choices with level-based vary."""
    result = core.commandline(
        [
            "gtdraw",
            "game.ef",
            "--vary-action-label-positions",
            "--vary-action-label-positions-by=level",
            "--vary-action-label-positions-choices=2,3",
        ]
    )
    (
        *_rest,
        vary_action_label_positions,
        action_label_position_by,
        vary_action_label_positions_by,
        vary_action_label_positions_choices,
    ) = result
    assert vary_action_label_positions_by == "level"
    assert vary_action_label_positions_choices == [2, 3]


# ---------------------------------------------------------------------------
# Skip markers for integration tests requiring external tools
# ---------------------------------------------------------------------------

requires_tex_tools = pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("pdftocairo") is None,
    reason="pdflatex and pdftocairo required",
)


# ---------------------------------------------------------------------------
# Helpers for integration tests
# ---------------------------------------------------------------------------

GAMES_DIR = Path(__file__).resolve().parents[1] / "games"


def _simple_ef_content():
    """Minimal valid .ef content for integration tests."""
    return "player 1\nlevel 0 node root player 1\n"




# ---------------------------------------------------------------------------
# PDF generation integration tests
# ---------------------------------------------------------------------------


class TestPdfGenerationIntegration:
    """Integration tests that actually compile LaTeX to PDF."""

    @requires_tex_tools
    def test_pdf_from_ef_file(self, tmp_path):
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(_simple_ef_content())
        pdf_path = core.pdf(str(ef_file), save_to=str(tmp_path / "out.pdf"))
        assert os.path.isfile(pdf_path)
        assert os.path.getsize(pdf_path) > 0
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

    @requires_tex_tools
    def test_pdf_save_to_custom_path(self, tmp_path):
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(_simple_ef_content())
        custom = str(tmp_path / "subdir" / "custom.pdf")
        os.makedirs(os.path.dirname(custom), exist_ok=True)
        pdf_path = core.pdf(str(ef_file), save_to=custom)
        assert pdf_path == str(Path(custom).absolute())
        assert os.path.isfile(pdf_path)


    @requires_tex_tools
    def test_pdf_from_repo_ef_file(self, tmp_path):
        """Test with a real game file from the repository."""
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        pdf_path = core.pdf(str(ef_file), save_to=str(tmp_path / "x1.pdf"))
        assert os.path.isfile(pdf_path)
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"


# ---------------------------------------------------------------------------
# PNG generation integration tests
# ---------------------------------------------------------------------------


class TestPngGenerationIntegration:
    """Integration tests that actually generate PNG images."""

    @requires_tex_tools
    def test_png_from_ef_file(self, tmp_path):
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(_simple_ef_content())
        png_path = core.png(str(ef_file), save_to=str(tmp_path / "out.png"))
        assert os.path.isfile(png_path)
        assert os.path.getsize(png_path) > 0
        with open(png_path, "rb") as f:
            assert f.read(4) == b"\x89PNG"



# ---------------------------------------------------------------------------
# SVG generation integration tests
# ---------------------------------------------------------------------------


class TestSvgGenerationIntegration:
    """Integration tests that actually generate SVG files."""

    @requires_tex_tools
    def test_svg_from_ef_file(self, tmp_path):
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(_simple_ef_content())
        svg_path = core.svg(str(ef_file), save_to=str(tmp_path / "out.svg"))
        assert os.path.isfile(svg_path)
        assert os.path.getsize(svg_path) > 0
        with open(svg_path) as f:
            content = f.read()
        assert "<svg" in content


    @requires_tex_tools
    def test_svg_responsive(self, tmp_path):
        """Verify that responsive_sizing=True modifies the SVG content."""
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(_simple_ef_content())
        svg_path = core.svg(
            str(ef_file),
            save_to=str(tmp_path / "responsive.svg"),
            responsive_sizing=True,
        )
        assert os.path.isfile(svg_path)
        with open(svg_path) as f:
            content = f.read()
        assert "<svg" in content
        # Verify responsive attributes are added
        assert 'width="100%"' in content
        assert 'height="auto"' in content
        assert 'style="max-height: 80vh;"' in content


# ---------------------------------------------------------------------------
# TikZ / tikz option tests
# ---------------------------------------------------------------------------


class TestGenerateTikzOptions:
    """Test tikz with various options (replacing tutorial notebook
    coverage for option variants)."""

    def test_color_scheme_default(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result = core.tikz(str(ef_file), color_scheme="default")
        assert "\\begin{tikzpicture}" in result

    def test_color_scheme_gambit(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result = core.tikz(str(ef_file), color_scheme="gambit")
        assert "\\begin{tikzpicture}" in result

    def test_color_scheme_distinctipy(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result = core.tikz(str(ef_file), color_scheme="distinctipy")
        assert "\\begin{tikzpicture}" in result

    def test_color_scheme_colorblind(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result = core.tikz(str(ef_file), color_scheme="colorblind")
        assert "\\begin{tikzpicture}" in result

    def test_scale_factor_affects_output(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result_default = core.tikz(str(ef_file))
        result_scaled = core.tikz(str(ef_file), scale_factor=2.0)
        assert result_default != result_scaled
        assert "scale=1.6" in result_scaled  # 2.0 * 0.8

    def test_edge_thickness_and_action_label_position(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result = core.tikz(str(ef_file), edge_thickness=2.0, action_label_position=0.8)
        assert "\\treethickn2.0pt" in result
        assert "\\begin{tikzpicture}" in result



# ---------------------------------------------------------------------------
# Sources: paths and buffers; drawings (.ef) and strategic games (.tex)
# ---------------------------------------------------------------------------

# Examples converted from Gambit's game files (once, with the converters gtdraw had then)
_CONVERTED_EF_FILES = sorted(
    GAMES_DIR / f"{name}.ef"
    for name in (
        "alt_russian_fixed",
        "alt_russian_sequential",
        "cross",
        "holdout",
        "kuhn-3-card-v1",
        "kuhn-4-card",
        "tiny_hanabi",
        "trust_game",
    )
)
_SGAME_FILES = sorted(GAMES_DIR.glob("*.tex"))
_ALL_EF_FILES = sorted(GAMES_DIR.glob("*.ef"))
_SGAME_PATH = str(GAMES_DIR / "nau2004_sec3.tex")


def _without_source_line(tikz_code):
    """TikZ text without the comment line that names the source."""
    return "\n".join(
        line
        for line in tikz_code.splitlines()
        if not line.startswith("% Game tree content from")
    )


def test_example_files_are_present():
    """The converted drawings and strategic games are in games/, and no Gambit game files are."""
    assert len(_CONVERTED_EF_FILES) == 8
    assert all(p.is_file() for p in _CONVERTED_EF_FILES)
    assert len(_SGAME_FILES) == 4
    assert not (GAMES_DIR / "efg").exists()
    assert not (GAMES_DIR / "nfg").exists()


@pytest.fixture
def keep_module_state():
    """Undo what rendering leaves in `core.playername`.

    A render's `player 0 name ...` line stays in a module global after the render
    (a known leak, until per-render state lands), so a test that renders many
    examples restores it for the tests that follow.
    """
    saved = list(core.playername)
    yield
    core.playername[:] = saved


@pytest.mark.parametrize("ef_path", _ALL_EF_FILES, ids=[p.name for p in _ALL_EF_FILES])
def test_tikz_smoke(ef_path, keep_module_state):
    """tikz succeeds on every example drawing, and gives a tikzpicture."""
    result = core.tikz(str(ef_path))
    assert "\\begin{tikzpicture}" in result
    assert len(result) > 100  # sanity check: non-trivial output


@pytest.mark.parametrize(
    "ef_path", _CONVERTED_EF_FILES, ids=[p.name for p in _CONVERTED_EF_FILES]
)
@requires_tex_tools
def test_pdf_smoke_converted_examples(ef_path, tmp_path, keep_module_state):
    """pdf compiles each drawing converted from a Gambit game file to a valid PDF."""
    pdf_path = core.pdf(str(ef_path), save_to=str(tmp_path / "smoke.pdf"))
    assert os.path.isfile(pdf_path)
    with open(pdf_path, "rb") as f:
        assert f.read(4) == b"%PDF"


class TestDrawingHelpers:
    """The private helpers that read a .ef drawing for the app."""

    def _write(self, tmp_path, text):
        path = tmp_path / "d.ef"
        path.write_text(text)
        return str(path)

    def test_count_players_ignores_chance(self, tmp_path):
        path = self._write(
            tmp_path, "player 0 name Chance\nplayer 1\nplayer 2\nlevel 0 node root player 0\n"
        )
        assert core._count_players(path) == 2

    def test_count_players_unreadable_file(self, tmp_path):
        assert core._count_players(str(tmp_path / "missing.ef")) == 6

    def test_levels(self, tmp_path):
        path = self._write(
            tmp_path,
            "player 1\nlevel 0 node root player 1\n"
            "level 2 node a from root\nlevel 6 node b from root\nlevel 2 node c from root\n",
        )
        assert core._get_game_levels(path) == [0, 2, 6]
        assert core._count_levels(path) == 6

    def test_levels_unreadable_file(self, tmp_path):
        missing = str(tmp_path / "missing.ef")
        assert core._get_game_levels(missing) == [0]
        assert core._count_levels(missing) == 0


class TestSources:
    """A source is a path or a file-like object; its kind is its extension or `format`."""

    EF_TEXT = "player 1\nlevel 0 node root player 1\nlevel 1 node a from 0,root move L payoffs 1 0\n"

    def test_buffer_gives_same_tikz_as_path(self, tmp_path):
        """A text buffer is a drawing by default and gives the same TikZ as its file."""
        path = tmp_path / "d.ef"
        path.write_text(self.EF_TEXT)
        from_path = core.tikz(str(path))
        from_buffer = core.tikz(io.StringIO(self.EF_TEXT))
        assert _without_source_line(from_path) == _without_source_line(from_buffer)

    def test_pathlike_source(self, tmp_path):
        """A pathlib.Path is a path."""
        path = tmp_path / "d.ef"
        path.write_text(self.EF_TEXT)
        assert core.tikz(path) == core.tikz(str(path))

    def test_file_object_source(self, tmp_path):
        """An open text file is a buffer."""
        path = tmp_path / "d.ef"
        path.write_text(self.EF_TEXT)
        with open(path) as f:
            result = core.tikz(f)
        assert _without_source_line(result) == _without_source_line(core.tikz(str(path)))

    def test_bytes_buffer_is_decoded(self):
        """A binary buffer is read as UTF-8."""
        result = core.tikz(io.BytesIO(self.EF_TEXT.encode("utf-8")))
        assert "\\begin{tikzpicture}" in result

    def test_buffer_source_line_names_buffer(self):
        """For a buffer, the comment line naming the source says so."""
        assert "% Game tree content from <buffer>" in core.tikz(io.StringIO(self.EF_TEXT))

    def test_path_source_line_names_path(self, tmp_path):
        """For a path, the comment line naming the source is the path as given."""
        path = tmp_path / "d.ef"
        path.write_text(self.EF_TEXT)
        assert f"% Game tree content from {path}" in core.tikz(str(path))

    def test_format_overrides_extension(self, tmp_path):
        """format='ef' makes a file with another extension a drawing."""
        path = tmp_path / "d.txt"
        path.write_text(self.EF_TEXT)
        assert "\\begin{tikzpicture}" in core.tikz(str(path), format="ef")

    def test_unknown_extension_without_format_is_an_error(self, tmp_path):
        """An unrecognised extension without format is a ValueError that names the choices."""
        path = tmp_path / "d.txt"
        path.write_text(self.EF_TEXT)
        with pytest.raises(ValueError, match=r"\.ef.*\.tex"):
            core.tikz(str(path))

    def test_efg_extension_is_not_a_drawing(self, tmp_path):
        """A Gambit game file is not read: its extension is not recognised."""
        path = tmp_path / "g.efg"
        path.write_text('EFG 2 R "x" { "1" "2" }\n""\n')
        with pytest.raises(ValueError):
            core.tikz(str(path))

    def test_bad_format_is_an_error(self):
        """format must be 'ef' or 'sgame'."""
        with pytest.raises(ValueError, match="format"):
            core.tikz(io.StringIO(self.EF_TEXT), format="efg")

    def test_missing_file(self, tmp_path):
        """A path that does not exist is a FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            core.tikz(str(tmp_path / "missing.ef"))

    def test_string_is_a_path_not_text(self):
        """A string is never read as the text of a drawing."""
        with pytest.raises((ValueError, FileNotFoundError)):
            core.tikz(self.EF_TEXT)

    def test_removed_layout_options_are_rejected(self):
        """The layout options that belonged to Gambit's layout are no longer accepted."""
        for option in (
            "level_scaling",
            "sublevel_scaling",
            "width_scaling",
            "hide_action_labels",
            "shared_terminal_depth",
        ):
            with pytest.raises(TypeError):
                core.tikz(io.StringIO(self.EF_TEXT), **{option: 1})

    @requires_tex_tools
    def test_default_output_name_is_the_stem(self, tmp_path, monkeypatch):
        """Without save_to the output is named from the path's stem, in the current directory."""
        src = tmp_path / "mygame.ef"
        src.write_text(self.EF_TEXT)
        monkeypatch.chdir(tmp_path)
        out = core.tex(str(src))
        assert Path(out) == (tmp_path / "mygame.tex").resolve()

    @requires_tex_tools
    def test_default_output_name_for_a_buffer(self, tmp_path, monkeypatch):
        """Without save_to a buffer's output is named 'drawing'."""
        monkeypatch.chdir(tmp_path)
        out = core.tex(io.StringIO(self.EF_TEXT))
        assert Path(out) == (tmp_path / "drawing.tex").resolve()

    def test_save_to_adds_extension(self, tmp_path):
        """save_to names the output; the extension is added if missing."""
        out = core.tex(io.StringIO(self.EF_TEXT), save_to=str(tmp_path / "named"))
        assert Path(out) == (tmp_path / "named.tex").resolve()
        assert "\\begin{tikzpicture}" in Path(out).read_text()

    def test_save_to_writes_only_the_output(self, tmp_path):
        """save_to no longer saves an intermediate drawing beside the output."""
        core.tex(io.StringIO(self.EF_TEXT), save_to=str(tmp_path / "named.tex"))
        assert sorted(p.name for p in tmp_path.iterdir()) == ["named.tex"]


class TestNoPygambit:
    """gtdraw imports and renders without pygambit."""

    def test_import_and_render_without_pygambit(self):
        """In a fresh process that cannot import pygambit, a drawing renders."""
        code = (
            "import sys\n"
            "sys.modules['pygambit'] = None\n"  # an import of pygambit raises ImportError
            "import io, gtdraw\n"
            "out = gtdraw.tikz(io.StringIO('player 1\\nlevel 0 node root player 1\\n'))\n"
            "assert 'tikzpicture' in out\n"
            "assert 'pygambit' not in sys.modules or sys.modules['pygambit'] is None\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr

    def test_public_names(self):
        """gtdraw exports the drawing functions and nothing from Gambit's formats."""
        import gtdraw

        assert sorted(gtdraw.__all__) == sorted(
            ["draw", "tikz", "tex", "pdf", "png", "svg", "latex_wrapper", "Style"]
        )
        for removed in (
            "ef_to_efg",
            "efg_to_ef",
            "gambit_layout_to_ef",
            "count_players",
            "count_levels",
            "get_game_levels",
            "ef_to_tex",
        ):
            assert not hasattr(gtdraw, removed)

    def test_no_syntax_warnings_in_sources(self):
        """The package's modules compile without a SyntaxWarning (an invalid escape in a docstring)."""
        import warnings

        for path in sorted(Path(core.__file__).parent.glob("*.py")):
            with warnings.catch_warnings():
                warnings.simplefilter("error", SyntaxWarning)
                compile(path.read_text(encoding="utf-8"), str(path), "exec")


class TestSgameRendering:
    """Strategic games: the LaTeX body of an sgame table, as a .tex file or a buffer."""

    def test_tikz_returns_the_body_unchanged(self):
        """tikz on a .tex file returns its text, not TikZ."""
        result = core.tikz(_SGAME_PATH)
        assert result == Path(_SGAME_PATH).read_text()
        assert "\\begin{game}" in result
        assert "\\end{game}" in result

    def test_tikz_does_not_contain_tikzpicture(self):
        """A payoff table is not a tree: no TikZ markup."""
        assert "\\begin{tikzpicture}" not in core.tikz(_SGAME_PATH)

    def test_buffer_with_format_sgame(self):
        """A buffer is a strategic game when format='sgame'."""
        text = Path(_SGAME_PATH).read_text()
        assert core.tikz(io.StringIO(text), format="sgame") == text

    def test_tex_wraps_with_sgame_package(self, tmp_path):
        """tex wraps the body in a document that uses the sgame package."""
        out = core.tex(_SGAME_PATH, save_to=str(tmp_path / "out"))
        assert out.endswith(".tex")
        content = Path(out).read_text()
        assert "\\usepackage{sgame}" in content
        assert "\\begin{game}" in content
        assert core.sgame_wrapper(Path(_SGAME_PATH).read_text()) == content

    def test_draw_returns_drawing_of_latex_body(self):
        """draw() on a strategic game returns a Drawing whose .tikz is the LaTeX body."""
        result = core.draw(_SGAME_PATH)
        assert isinstance(result, core.Drawing)
        assert "\\begin{game}" in result.tikz
        assert result.source == core.sgame_wrapper(result.tikz)

    @pytest.mark.parametrize("path", _SGAME_FILES, ids=[p.name for p in _SGAME_FILES])
    def test_sgame_tikz_smoke(self, path):
        """tikz succeeds on every example strategic game."""
        assert "\\begin{game}" in core.tikz(str(path))

    @pytest.mark.parametrize("path", _SGAME_FILES, ids=[p.name for p in _SGAME_FILES])
    @requires_tex_tools
    def test_sgame_pdf_smoke(self, path, tmp_path):
        """pdf compiles each strategic game to a valid PDF."""
        pdf_path = core.pdf(str(path), save_to=str(tmp_path / "out.pdf"))
        assert os.path.isfile(pdf_path)
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

    @requires_tex_tools
    def test_pdf_from_buffer(self, tmp_path):
        """pdf of a strategic game given as a buffer."""
        text = Path(_SGAME_PATH).read_text()
        pdf_path = core.pdf(io.StringIO(text), save_to=str(tmp_path / "t"), format="sgame")
        assert pdf_path.endswith("t.pdf")
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"


class TestFontStyling:
    """Test font styling in TikZ output."""

    def test_tikz_font_styles(self):
        """Test that font styles are correctly injected into TikZ output."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = f.name

        try:
            # Test sans-serif bold italic
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".ef"
            ) as f2:
                f2.write("player 1\n")
                f2.write("level 0 node root player 1\n")
                f2.write(
                    "level 1 node child from 0,root player 2 move Move payoffs 1 2\n"
                )
                ef2_path = f2.name

            result = core.tikz(
                ef2_path, font_family="sffamily", font_bold=True, font_italic=True
            )
            assert (
                "every node/.append style={font=\\sffamily\\bfseries\\itshape, execute at begin node=\\boldmath}"
                in result
            )

            # Action labels should also be present
            assert "Move" in result

            # Test font size
            result_size = core.tikz(ef2_path, font_size="large")
            assert "every node/.append style={font=\\rmfamily\\large}" in result_size

            os.unlink(ef2_path)
        finally:
            os.unlink(ef_file_path)


class TestCustomColors:
    """Test custom color scheme functionality."""

    def test_count_players(self):
        """Test player counting utility."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1 name Alice\n")
            f.write("player 2 name Bob\n")
            f.write("level 0 node root player 1\n")
            ef_file_path = f.name

        try:
            assert core._count_players(ef_file_path) == 2
            # Chance player name should be capitalized
            assert core.playername[0] == "Chance"
        finally:
            os.unlink(ef_file_path)

    def test_custom_color_definitions(self):
        """Test custom color LaTeX definitions."""
        custom_colors = {0: "#759138", 1: "#FF0000", 2: "#0000FF"}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = f.name

        try:
            result = core.tikz(
                ef_file_path, color_scheme="custom", custom_colors=custom_colors
            )
            assert "\\definecolor{customchancecolor}{HTML}{759138}" in result
            assert "\\definecolor{customp1color}{HTML}{FF0000}" in result
            assert "\\definecolor{customp2color}{HTML}{0000FF}" in result
        finally:
            os.unlink(ef_file_path)

    def test_iset_edge_thickness(self):
        """Test that edge thickness applies to info sets."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1\n")
            f.write("level 0 node n1 player 1\n")
            f.write("level 0 node n2 player 1\n")
            f.write("iset 0,n1 0,n2 player 1\n")
            ef_file_path = f.name

        try:
            result = core.tikz(ef_file_path, edge_thickness=2.5)
            # The iset draw command should contain the line width/thickn
            assert "line width=\\treethickn" in result
            assert "\\treethickn2.5pt" in result
        finally:
            os.unlink(ef_file_path)


def test_commandline_font_options():
    """Test font-related argument parsing."""
    # Test font family
    result = core.commandline(["core.py", "test.ef", "--font=sans-serif"])
    assert result[7] == "sffamily"

    result = core.commandline(["core.py", "test.ef", "--font=monospace"])
    assert result[7] == "ttfamily"

    # Test bold/italic flags
    result = core.commandline(["core.py", "test.ef", "--bold", "--italic"])
    assert result[8] is True  # bold
    assert result[9] is True  # italic

    # Test font size
    result = core.commandline(["core.py", "test.ef", "--font-size=large"])
    assert result[10] == "large"


def test_commandline_horizontal_flag():
    """Test --horizontal flag parsing."""
    result = core.commandline(["core.py", "test.ef", "--horizontal"])
    assert result[12] is True


def test_commandline_color_scheme():
    """Test parsing of the --color-scheme option."""
    result = core.commandline(["core.py", "test.ef", "--color-scheme=distinctipy"])
    assert result[28] == "distinctipy"


def test_commandline_edge_and_label_options():
    """Test parsing of edge thickness and action label position options."""
    result = core.commandline(
        [
            "core.py",
            "test.ef",
            "--edge-thickness=2.0",
            "--action-label-position=0.7",
        ]
    )
    assert result[29] == 2.0
    assert result[30] == 0.7


class TestHorizontalLayout:
    """Test horizontal layout specific features."""

    def test_horizontal_tikz_output(self):
        """Test that horizontal layout injects correct TikZ rotation."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = f.name

        try:
            result = core.tikz(ef_file_path, horizontal=True)

            # Check for picture rotation
            assert "rotate=90" in result

            # Labels should NOT be rotated back anymore
            assert "rotate=-90" not in result

            # Action labels should NOT have redundant rotatebox anymore
            # (Adding a child to check action labels)
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".ef"
            ) as f2:
                f2.write("player 1\n")
                f2.write("level 0 node root player 1\n")
                f2.write(
                    "level 1 node child from 0,root player 2 move Move payoffs 1 2\n"
                )
                ef2_path = f2.name

            result2 = core.tikz(ef2_path, horizontal=True)
            # Should NOT contain \rotatebox{-90} in Move label
            assert "\\rotatebox{-90}" not in result2
            # But Move label should be present
            assert "Move" in result2

            os.unlink(ef2_path)
        finally:
            os.unlink(ef_file_path)

    def test_horizontal_legend_position(self):
        """Test that legend is repositioned in horizontal mode."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1\n")
            f.write("level 0 node n1 player 1\n")
            ef_file_path = f.name

        try:
            # Vertical legend (default)
            res_v = core.tikz(ef_file_path, color_scheme="gambit")
            # Horizontal legend
            res_h = core.tikz(ef_file_path, color_scheme="gambit", horizontal=True)

            assert "Player color legend" in res_v
            assert "Player color legend" in res_h
            assert res_v != res_h

            # In horizontal mode, it should use a positive x_offset (right side in original coords)
            # which becomes top side in final rotated coords.
            # Look for shift={(X,Y)} and rotate=-90
            import re

            shift_h = re.search(
                r"\\begin{scope}\[scale=1,shift={\(([\d.-]+),([\d.-]+)\)}, rotate=-90\]",
                res_h,
            )
            shift_v = re.search(
                r"\\begin{scope}\[scale=1,shift={\(([\d.-]+),([\d.-]+)\)}\]", res_v
            )

            assert shift_h and shift_v
            # X coordinate in horizontal mode should be larger (max_x based)
            assert float(shift_h.group(1)) > float(shift_v.group(1))

        finally:
            os.unlink(ef_file_path)

    def test_legend_position_vertical(self):
        """Test that legend_position shifts scope correctly in vertical mode."""
        import re

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1 2\n")
            f.write("level 0 node n1 player 1\n")
            f.write("level 1 node n2 player 2 parent n1\n")
            f.write("level 1 node n3 player 2 parent n1\n")
            ef_file_path = f.name

        try:

            def get_scope_xy(tikz):
                m = re.search(
                    r"\\begin{scope}\[scale=1,shift={\(([\d.-]+),([\d.-]+)\)}\]",
                    tikz,
                )
                assert m, f"No scope shift found in: {tikz}"
                return float(m.group(1)), float(m.group(2))

            res_tl = core.tikz(
                ef_file_path, color_scheme="gambit", legend_position="top-left"
            )
            res_tr = core.tikz(
                ef_file_path, color_scheme="gambit", legend_position="top-right"
            )
            res_bl = core.tikz(
                ef_file_path, color_scheme="gambit", legend_position="bottom-left"
            )
            res_br = core.tikz(
                ef_file_path, color_scheme="gambit", legend_position="bottom-right"
            )

            x_tl, y_tl = get_scope_xy(res_tl)
            x_tr, y_tr = get_scope_xy(res_tr)
            x_bl, y_bl = get_scope_xy(res_bl)
            x_br, y_br = get_scope_xy(res_br)

            # Left corners should have smaller x than right corners
            assert x_tl < x_tr
            assert x_bl < x_br

            # Top corners should have y = max_y (= 0 for root)
            assert y_tl == 0.0
            assert y_tr == 0.0

            # Bottom corners should have y < 0 (deeper level)
            assert y_bl < 0.0
            assert y_br < 0.0

            # Same side should have matching x
            assert x_tl == x_bl
            assert x_tr == x_br

            # Same vertical level should have matching y
            assert y_tl == y_tr
            assert y_bl == y_br

        finally:
            os.unlink(ef_file_path)

    def test_legend_position_horizontal(self):
        """Test that legend_position shifts scope correctly in horizontal mode."""
        import re

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1 2\n")
            f.write("level 0 node n1 player 1\n")
            f.write("level 1 node n2 player 2 parent n1\n")
            f.write("level 1 node n3 player 2 parent n1\n")
            ef_file_path = f.name

        try:

            def get_scope_xy(tikz):
                m = re.search(
                    r"\\begin{scope}\[scale=1,shift={\(([\d.-]+),([\d.-]+)\)}, rotate=-90\]",
                    tikz,
                )
                assert m, f"No horizontal scope shift found in: {tikz}"
                return float(m.group(1)), float(m.group(2))

            res_tl = core.tikz(
                ef_file_path,
                color_scheme="gambit",
                horizontal=True,
                legend_position="top-left",
            )
            res_tr = core.tikz(
                ef_file_path,
                color_scheme="gambit",
                horizontal=True,
                legend_position="top-right",
            )
            res_bl = core.tikz(
                ef_file_path,
                color_scheme="gambit",
                horizontal=True,
                legend_position="bottom-left",
            )
            res_br = core.tikz(
                ef_file_path,
                color_scheme="gambit",
                horizontal=True,
                legend_position="bottom-right",
            )

            x_tl, y_tl = get_scope_xy(res_tl)
            x_tr, y_tr = get_scope_xy(res_tr)
            x_bl, y_bl = get_scope_xy(res_bl)
            x_br, y_br = get_scope_xy(res_br)

            # Top corners (top in final view) should have larger x (max_x based)
            assert x_tl > x_bl
            assert x_tr > x_br

            # Left corners (left in final view) should have larger y (max_y + 0.5)
            assert y_tl > y_tr
            assert y_bl > y_br

        finally:
            os.unlink(ef_file_path)

    def test_legend_position_commandline(self):
        """Test that --legend-position is correctly parsed by commandline()."""
        result_default = core.commandline(["core.py", "test.ef"])
        assert result_default[14] == "top-left"

        result_tr = core.commandline(
            ["core.py", "test.ef", "--legend-position=top-right"]
        )
        assert result_tr[14] == "top-right"

        result_bl = core.commandline(
            ["core.py", "test.ef", "--legend-position=bottom-left"]
        )
        assert result_bl[14] == "bottom-left"

        result_br = core.commandline(
            ["core.py", "test.ef", "--legend-position=bottom-right"]
        )
        assert result_br[14] == "bottom-right"

        # Invalid value should leave default unchanged
        result_invalid = core.commandline(
            ["core.py", "test.ef", "--legend-position=invalid"]
        )
        assert result_invalid[14] == "top-left"

    def test_horizontal_payoff_position(self):
        """Test that payoffs are comma-separated and positioned using 'right' in horizontal mode."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1\n")
            f.write("level 0 node n1 player 1 payoffs 1 2\n")
            ef_file_path = f.name

        try:
            result = core.tikz(ef_file_path, horizontal=True)
            # Payoffs should be combined into a single comma-separated node
            assert "1, 2" in result
            # Vertical mode would emit separate values without commas; comma means combined
            assert "1, 2" in result and "2, " not in result
            # Should be positioned with 'right=0.5\paydown'
            assert "right=0.5\\paydown" in result
            assert "below=0.5\\paydown" not in result

            # Test with label background enabled (terminal payoffs should still lack a background and be comma-separated)
            result_bg = core.tikz(ef_file_path, horizontal=True, label_bg=True)
            assert "1, 2" in result_bg
            assert "right=0.5\\paydown" in result_bg
            assert "right=2.5\\paydown" not in result_bg
            assert "below=0.5\\paydown" not in result_bg
            assert "below=2.5\\paydown" not in result_bg
        finally:
            os.unlink(ef_file_path)

    def test_action_labels_centered_with_label_bg(self):
        """Test that action labels are centered on edges when label backgrounds are on."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1\n")
            f.write("level 0 node root player 1\n")
            f.write(
                "level 1 node child from 0,root player 1 move MyAction payoffs 1 2\n"
            )
            ef_file_path = f.name

        try:
            # 1. Backgrounds off: should have positional offsets/sides (e.g. above/below/left/right/yshift/xshift)
            res_no_bg = core.tikz(ef_file_path, label_bg=False)
            assert "MyAction" in res_no_bg
            assert "xshift=" in res_no_bg or "yshift=" in res_no_bg

            # 2. Backgrounds on: should NOT have positional offsets/sides and should be centered on edge
            res_bg = core.tikz(ef_file_path, label_bg=True)
            assert "MyAction" in res_bg
            # Because it is centered, there are no side or shift options in the action label node
            action_lines = [
                line
                for line in res_bg.split("\n")
                if "MyAction" in line and not line.strip().startswith("%")
            ]
            assert len(action_lines) == 1
            action_line = action_lines[0]
            assert "xshift" not in action_line
            assert "yshift" not in action_line
            assert "above" not in action_line
            assert "below" not in action_line
            assert "left" not in action_line
            assert "right" not in action_line
            # It should have fill options
            assert "fill=" in action_line
        finally:
            os.unlink(ef_file_path)


def test_chance_node_probability_with_long_label():
    """Chance node probabilities must not be dropped when action label contains a number."""
    ef_content = (
        "player 1\n"
        "level 0 node n1 chance\n"
        "level 1 node n2 player 1 parent n1 move Chamber~1~(\\frac{1}{6})\n"
        "level 1 node n3 player 1 parent n1 move Chamber~2~(\\frac{1}{6})\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
        f.write(ef_content)
        path = f.name
    try:
        result = core.tikz(path)
        assert "\\frac{1}{6}" in result, (
            "Probability fraction must appear in TikZ output"
        )
    finally:
        os.unlink(path)


def test_commandline_custom_colors():
    """Test custom color argument parsing."""
    result = core.commandline(
        ["core.py", "test.ef", '--custom-colors="0:#FF0000,1:#0000FF"']
    )
    custom_colors = result[11]
    assert custom_colors == {0: "#FF0000", 1: "#0000FF"}


def test_action_label_dist():
    """Test that action_label_dist correctly scales the TikZ macro definitions."""
    ef_file_path = "games/example.ef"
    if not os.path.exists(ef_file_path):
        # Fallback for CI or different working directory
        ef_file_path = os.path.join(
            os.path.dirname(__file__), "..", "games", "example.ef"
        )
        if not os.path.exists(ef_file_path):
            return  # Skip if file not found

    try:
        # Default dist=1.0 -> 0.5mm
        res1 = core.tikz(ef_file_path, action_label_dist=1.0)
        if not ("xshift=0.5mm" in res1 or "xshift=-0.5mm" in res1):
            print(f"DEBUG: res1=\n{res1}")
        assert "xshift=0.5mm" in res1 or "xshift=-0.5mm" in res1

        # Custom dist=2.0 -> 1.0mm
        res2 = core.tikz(ef_file_path, action_label_dist=2.0)
        assert "xshift=1mm" in res2 or "xshift=-1mm" in res2

        # Horizontal dist=2.0 -> yshift 1mm
        res3 = core.tikz(ef_file_path, action_label_dist=2.0, horizontal=True)
        assert "yshift=1mm" in res3 or "yshift=-1mm" in res3
    except Exception as e:
        raise e


def test_commandline_iset_options():
    """Test parsing of information set styling flags."""
    # Test all flags together
    result = core.commandline(
        [
            "core.py",
            "test.ef",
            "--iset-fill",
            "--iset-fill-opacity=0.5",
            "--iset-boundary=dotted",
            "--node-size=2.0",
        ]
    )
    assert result[16] is True  # iset_fill
    assert result[17] == 0.5  # iset_fill_opacity
    assert result[18] == "dotted"  # iset_boundary
    # iset_curved, iset_curved_bend, iset_curved_bend_by at indices 19-21
    assert result[19] is False  # iset_curved default
    assert result[20] == 10.0  # iset_curved_bend default
    assert result[21] == "player"  # iset_curved_bend_by default
    assert result[22] == 2.0  # node_size

    # Test individual flags
    result_fill = core.commandline(["core.py", "test.ef", "--iset-fill"])
    assert result_fill[16] is True
    assert result_fill[17] == 0.2  # Default
    assert result_fill[18] == "solid"

    result_dotted = core.commandline(["core.py", "test.ef", "--iset-dotted"])
    assert result_dotted[18] == "dotted"

    result_none = core.commandline(["core.py", "test.ef", "--iset-boundary=none"])
    assert result_none[18] == "none"

    # Test curved flags
    result_curved = core.commandline(
        [
            "core.py",
            "test.ef",
            "--iset-curved",
            "--iset-curved-bend=15.0",
            "--iset-curved-bend-by=level",
        ]
    )
    assert result_curved[19] is True  # iset_curved
    assert result_curved[20] == 15.0  # iset_curved_bend
    assert result_curved[21] == "level"  # iset_curved_bend_by


class TestIsetStylingIntegration:
    """Test information set styling in generated TikZ."""

    def test_iset_styling_in_tikz(self, tmp_path):
        """Verify that iset styling options correctly affect TikZ output."""
        ef_file = tmp_path / "iset_test.ef"
        ef_file.write_text(
            "player 1\n"
            "player 2\n"
            "level 0 node 1 player 1\n"
            "level 1 node 1 from 0,1 player 2 move L\n"
            "level 1 node 2 from 0,1 player 2 move R\n"
            "iset 1,1 1,2 player 2\n"
        )
        ef_file_path = str(ef_file)

        # 1. Default (no fill, not dotted)
        res_default = core.tikz(ef_file_path, color_scheme="gambit")
        # Check for iset draw command (not the node definition)
        iset_draw_lines = [
            line
            for line in res_default.split("\n")
            if "\\draw [" in line and "playertwocolor" in line
        ]
        assert len(iset_draw_lines) > 0
        assert "fill=playertwocolor" not in iset_draw_lines[0]
        assert "dotted" not in iset_draw_lines[0]
        assert "draw=none" not in iset_draw_lines[0]

        # 2. Filled
        res_fill = core.tikz(
            ef_file_path, color_scheme="gambit", iset_fill=True, iset_fill_opacity=0.4
        )
        iset_draw_fill = [
            line
            for line in res_fill.split("\n")
            if "\\draw [" in line and "playertwocolor" in line
        ]
        assert "fill=playertwocolor" in iset_draw_fill[0]
        assert "fill opacity=0.4" in iset_draw_fill[0]

        # 3. Dotted
        res_dotted = core.tikz(
            ef_file_path, color_scheme="gambit", iset_boundary="dotted"
        )
        iset_draw_dotted = [
            line
            for line in res_dotted.split("\n")
            if "\\draw [" in line and "playertwocolor" in line
        ]
        assert "dotted" in iset_draw_dotted[0]

        # 4. None (invisible)
        res_none = core.tikz(ef_file_path, color_scheme="gambit", iset_boundary="none")
        iset_draw_none = [
            line
            for line in res_none.split("\n")
            if "\\draw [" in line and "playertwocolor" in line
        ]
        assert "draw=none" in iset_draw_none[0]

    def test_iset_curved_tikz(self, tmp_path):
        """Verify that curved iset mode produces explicit Bezier control point paths."""
        ef_file = tmp_path / "iset_curved_test.ef"
        ef_file.write_text(
            "player 1\n"
            "player 2\n"
            "level 0 node 1 player 1\n"
            "level 1 node 1 xshift -2 from 0,1 player 2 move L\n"
            "level 1 node 2 xshift 2 from 0,1 player 2 move R\n"
            "iset 1,1 1,2 player 2\n"
        )
        ef_file_path = str(ef_file)

        # 1. Default mode: arc-based (contains '-- cycle')
        res_default = core.tikz(ef_file_path, color_scheme="gambit")
        iset_lines_default = [
            line for line in res_default.split("\n") if "playertwocolor" in line and "\\draw [" in line
        ]
        assert len(iset_lines_default) > 0
        assert "-- cycle" in res_default
        assert "to[bend left=" not in res_default

        # 2. Curved mode: open path with double-stroke ribbon, no '-- cycle'
        res_curved = core.tikz(
            ef_file_path, color_scheme="gambit", iset_curved=True, iset_curved_bend=10.0
        )
        iset_lines_curved = [
            line for line in res_curved.split("\n") if "playertwocolor" in line and "\\draw [" in line
        ]
        assert len(iset_lines_curved) > 0
        iset_line = iset_lines_curved[0]
        # Explicit Bezier control points used to avoid TikZ dimension overflow
        assert ".. controls" in iset_line
        assert "-- cycle" not in iset_line
        # Open path: for N nodes, open path has N-1 Bezier segments
        import re
        ctrl_count = len(re.findall(r'\.\. controls', iset_line))
        assert ctrl_count == 1, f"Open path for 2 nodes must have exactly 1 Bezier segment, got {ctrl_count}"
        # Double-stroke ribbon style
        assert "double distance=" in iset_line
        assert "line cap=round" in iset_line
        # No arc-mode fill= in curved mode
        assert "fill=" not in iset_line

        # 3. Negative bend angle — curve goes to the opposite side; still uses Bezier
        res_neg = core.tikz(
            ef_file_path, color_scheme="gambit", iset_curved=True, iset_curved_bend=-15.0
        )
        iset_lines_neg = [
            line for line in res_neg.split("\n") if "playertwocolor" in line and "\\draw [" in line
        ]
        assert ".. controls" in iset_lines_neg[0]
        # Positive and negative bends should produce different control points
        res_pos = core.tikz(
            ef_file_path, color_scheme="gambit", iset_curved=True, iset_curved_bend=15.0
        )
        iset_lines_pos = [
            line for line in res_pos.split("\n") if "playertwocolor" in line and "\\draw [" in line
        ]
        assert iset_lines_neg[0] != iset_lines_pos[0], "Positive and negative bends must differ"

        # 4. Double-stroke ribbon width is fixed at 6mm (2 × isetradius × 10)
        res_default = core.tikz(
            ef_file_path, color_scheme="gambit", iset_curved=True, iset_curved_bend=10.0
        )
        iset_line_default = [
            line for line in res_default.split("\n") if "playertwocolor" in line and "\\draw [" in line
        ][0]
        assert "double distance=6mm" in iset_line_default, "Ribbon width must be fixed at 6mm"

        # 5. Per-player dict bend: player 2 gets a different bend from player 1
        res_per_player = core.tikz(
            ef_file_path,
            color_scheme="gambit",
            iset_curved=True,
            iset_curved_bend={1: 5.0, 2: 25.0},
            iset_curved_bend_by="player",
        )
        res_default_bend = core.tikz(
            ef_file_path,
            color_scheme="gambit",
            iset_curved=True,
            iset_curved_bend=10.0,
        )
        iset_lines_pp = [
            line for line in res_per_player.split("\n") if "playertwocolor" in line and "\\draw [" in line
        ]
        iset_lines_db = [
            line for line in res_default_bend.split("\n") if "playertwocolor" in line and "\\draw [" in line
        ]
        assert iset_lines_pp[0] != iset_lines_db[0], "Per-player dict bend must differ from uniform bend"

        # 6. Bezier control points change with bend angle — different angles → different paths
        res_b10 = core.tikz(ef_file_path, color_scheme="gambit", iset_curved=True, iset_curved_bend=10.0)
        res_b20 = core.tikz(ef_file_path, color_scheme="gambit", iset_curved=True, iset_curved_bend=20.0)
        assert res_b10 != res_b20, "Different bend angles must produce different TikZ output"


def test_node_size_macro():
    """Test that node_size correctly scales the TikZ macro definitions."""
    ef_file_path = "games/example.ef"
    if not os.path.exists(ef_file_path):
        ef_file_path = os.path.join(
            os.path.dirname(__file__), "..", "games", "example.ef"
        )
        if not os.path.exists(ef_file_path):
            return

    # Default size=1.5mm
    res1 = core.tikz(ef_file_path, node_size=1.5)
    assert "\\ndiam1.5mm" in res1
    assert "\\sqwidth1.6mm" in res1

    # Custom size=2.0mm
    res2 = core.tikz(ef_file_path, node_size=2.0)
    assert "\\ndiam2.0mm" in res2
    assert "\\sqwidth2.1mm" in res2


def test_payoff_font_family():
    r"""Test that payoffs pick up the sans-serif font family via \mathsf."""
    ef_file_path = "games/example.ef"
    if not os.path.exists(ef_file_path):
        ef_file_path = os.path.join(
            os.path.dirname(__file__), "..", "games", "example.ef"
        )
        if not os.path.exists(ef_file_path):
            return

    # Serif (default)
    res_serif = core.tikz(ef_file_path, font_family="rmfamily")
    assert "$\\mathsf{" not in res_serif

    # Sans-serif
    res_sans = core.tikz(ef_file_path, font_family="sffamily")
    assert "$\\mathsf{" in res_sans




class TestLabelBackground:
    """Tests for the label_bg / label_bg_color / label_bg_opacity feature."""

    @pytest.fixture
    def simple_ef(self, tmp_path):
        ef = tmp_path / "simple.ef"
        ef.write_text(
            "player 1\nplayer 2\n"
            "level 0 node root player 1\n"
            "level 2 node 1 from 0,root move L payoffs 1 0\n"
            "level 2 node 2 from 0,root move R payoffs 0 1\n"
        )
        return str(ef)

    def test_label_bg_disabled_by_default(self, simple_ef):
        result = core.tikz(simple_ef)
        assert "fill opacity=" not in result

    def test_label_bg_enables_fill(self, simple_ef):
        # Default colour scheme: player 1 is black; background uses player colour
        result = core.tikz(simple_ef, label_bg=True)
        assert "fill=black" in result
        assert "fill opacity=" in result
        assert "text opacity=1" in result
        assert "text=white" in result

    def test_label_bg_custom_named_color(self, simple_ef):
        # label_bg_color is a fallback; player colors still take precedence for labelled nodes
        result = core.tikz(simple_ef, label_bg=True, label_bg_color="yellow")
        assert "fill opacity=" in result  # fill is present (player colour used)
        assert "text=white" in result  # text is always white when label_bg active

    def test_label_bg_custom_hex_color(self, simple_ef):
        # Hex fallback colour is still defined in preamble even though player colours take precedence
        result = core.tikz(simple_ef, label_bg=True, label_bg_color="#ffcc00")
        assert "\\definecolor{gtdrawdropbg}{HTML}{FFCC00}" in result
        assert "fill opacity=" in result

    def test_label_bg_hex_without_hash(self, simple_ef):
        result = core.tikz(simple_ef, label_bg=True, label_bg_color="ffcc00")
        assert "\\definecolor{gtdrawdropbg}{HTML}{FFCC00}" in result

    def test_label_bg_opacity_clamped_high(self, simple_ef):
        # opacity > 1 should be clamped to 1.0
        result = core.tikz(simple_ef, label_bg=True, label_bg_opacity=5.0)
        assert "fill opacity=1" in result

    def test_label_bg_opacity_clamped_low(self, simple_ef):
        # opacity < 0 should be clamped to 0.0
        result = core.tikz(simple_ef, label_bg=True, label_bg_opacity=-1.0)
        assert "fill opacity=0" in result

    def test_cli_label_bg_flag(self):
        from gtdraw.core import commandline

        result = commandline(
            [
                "gtdraw",
                "game.ef",
                "--label-bg",
                "--label-bg-color=#aabbcc",
                "--label-bg-opacity=0.5",
            ]
        )
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert label_bg is True
        assert label_bg_color == "#aabbcc"
        assert label_bg_opacity == pytest.approx(0.5)

    def test_label_bg_declares_layer(self, simple_ef):
        from gtdraw.core import tikz

        code = tikz(str(simple_ef), label_bg=True)
        assert "\\pgfdeclarelayer{labels}" in code
        assert "\\pgfsetlayers{main,labels}" in code

    def test_label_bg_no_layer_when_disabled(self, simple_ef):
        from gtdraw.core import tikz

        code = tikz(str(simple_ef), label_bg=False)
        assert "\\pgfdeclarelayer" not in code
        assert "\\pgfsetlayers" not in code

    def test_label_bg_labels_in_foreground(self, simple_ef):
        from gtdraw.core import tikz

        code = tikz(str(simple_ef), label_bg=True)
        assert "\\begin{pgfonlayer}{labels}" in code
        assert "\\end{pgfonlayer}" in code

    def test_label_bg_per_player_dict_enabled(self, simple_ef):
        # Player 1 enabled, player 2 not — fill should appear (player 1 label exists)
        from gtdraw.core import tikz

        code = tikz(str(simple_ef), label_bg={1: True, 2: False}, label_bg_by="player")
        assert "fill opacity=" in code

    def test_label_bg_per_player_dict_all_disabled(self, simple_ef):
        # All players disabled — no fill
        from gtdraw.core import tikz

        code = tikz(str(simple_ef), label_bg={1: False, 2: False}, label_bg_by="player")
        assert "fill opacity=" not in code

    def test_label_bg_per_level_dict(self, simple_ef):
        # Enable for level 0 only
        from gtdraw.core import tikz

        code = tikz(str(simple_ef), label_bg={0: True}, label_bg_by="level")
        assert "fill opacity=" in code

    def test_label_bg_white_bg_style(self, simple_ef):
        # white_bg: fill=white and text= set to player color (not text=white)
        from gtdraw.core import tikz

        code = tikz(str(simple_ef), label_bg=True, label_bg_style="white_bg")
        assert "fill=white" in code
        assert "fill opacity=" in code
        assert "text=white" not in code

    def test_label_bg_player_bg_style_unchanged(self, simple_ef):
        # player_bg: current behaviour — fill=player_color, text=white
        from gtdraw.core import tikz

        code = tikz(str(simple_ef), label_bg=True, label_bg_style="player_bg")
        assert "fill opacity=" in code
        assert "text=white" in code

    def test_label_bg_dict_declares_layer(self, simple_ef):
        # Even with a dict, the labels layer is declared if any value is True
        from gtdraw.core import tikz

        code = tikz(str(simple_ef), label_bg={1: True}, label_bg_by="player")
        assert "\\pgfdeclarelayer{labels}" in code

    def test_label_bg_dict_no_layer_all_false(self, simple_ef):
        # Dict with all False — no layer declared
        from gtdraw.core import tikz

        code = tikz(str(simple_ef), label_bg={1: False, 2: False}, label_bg_by="player")
        assert "\\pgfdeclarelayer" not in code

    def test_cli_label_bg_per_player_indices(self):
        from gtdraw.core import commandline

        result = commandline(
            ["gtdraw", "game.ef", "--label-bg=1,2", "--label-bg-by=player"]
        )
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert label_bg == {1: True, 2: True}
        assert label_bg_by == "player"

    def test_cli_label_bg_style(self):
        from gtdraw.core import commandline

        result = commandline(
            ["gtdraw", "game.ef", "--label-bg", "--label-bg-style=white_bg"]
        )
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
            mirror,
            legend_position,
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            iset_curved,
            iset_curved_bend,
            iset_curved_bend_by,
            node_size,
            label_bg,
            label_bg_color,
            label_bg_opacity,
            label_bg_by,
            label_bg_style,
            color_scheme,
            edge_thickness,
            action_label_position,
            vary_action_label_positions,
            action_label_position_by,
            vary_action_label_positions_by,
            vary_action_label_positions_choices,
        ) = result
        assert label_bg is True
        assert label_bg_style == "white_bg"


class TestVaryActionLabelPositions:
    """Tests for the vary_action_label_positions feature."""

    def test_commandline_vary_action_label_positions_flag(self):
        """Test parsing of the --vary-action-label-positions option."""
        from gtdraw.core import commandline

        result = commandline(["core.py", "test.ef", "--vary-action-label-positions"])
        assert result[31] is True

    def test_vary_action_label_positions_layout(self, tmp_path):
        """Test that vary_action_label_positions=True staggers action labels for nodes with multiple children."""
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(
            "player 1\n"
            "level 0 node root player 1\n"
            "level 1 node 1 from 0,root move Left payoffs 1 0\n"
            "level 1 node 2 from 0,root move Right payoffs 0 1\n"
        )
        result_default = core.tikz(str(ef_file), vary_action_label_positions=False)
        result_varied = core.tikz(str(ef_file), vary_action_label_positions=True)
        assert result_default != result_varied


class TestPlayerActionLabelPositions:
    """Tests for the player-by-player action label positions feature."""

    def test_commandline_player_action_label_positions(self):
        """Test parsing of dictionary-based --action-label-position settings."""
        from gtdraw.core import commandline

        # Dictionary format
        result = commandline(
            ["core.py", "test.ef", "--action-label-position=0:0.3,1:0.65"]
        )
        assert isinstance(result[30], dict)
        assert result[30][0] == 0.3
        assert result[30][1] == 0.65

        # Invalid format falls back
        result_invalid = commandline(
            ["core.py", "test.ef", "--action-label-position=invalid"]
        )
        assert result_invalid[30] == 0.5

    def test_player_action_label_positions_layout(self, tmp_path):
        """Test that different player nodes apply different action label positions."""
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(
            "player 1 name Alice\n"
            "player 2 name Bob\n"
            "level 0 node root player 1\n"
            "level 1 node child1 from 0,root player 2 move L1 payoffs 1 0\n"
            "level 2 node child2 from 1,child1 player 1 move L2 payoffs 0 1\n"
        )

        positions = {1: 0.3, 2: 0.7}
        result = core.tikz(str(ef_file), action_label_position=positions)

        result_global_0_3 = core.tikz(str(ef_file), action_label_position=0.3)
        result_global_0_7 = core.tikz(str(ef_file), action_label_position=0.7)

        assert result != result_global_0_3
        assert result != result_global_0_7


class TestLevelActionLabelPositions:
    """Tests for level-based action label positions."""

    def test_commandline_level_position_by(self):
        """Test that --action-label-position-by=level is parsed correctly."""
        from gtdraw.core import commandline

        result = commandline(
            [
                "core.py",
                "test.ef",
                "--action-label-position=0:0.3,1:0.7",
                "--action-label-position-by=level",
            ]
        )
        # action_label_position_by is at index 32
        assert result[32] == "level"
        assert isinstance(result[30], dict)

    def test_level_action_label_positions_layout(self, tmp_path):
        """Test that level-keyed positions produce different output than player-keyed ones."""
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(
            "player 1 name Alice\n"
            "player 2 name Bob\n"
            "level 0 node root player 1\n"
            "level 1 node child1 from 0,root player 2 move L1 payoffs 1 0\n"
            "level 2 node child2 from 1,child1 player 1 move L2 payoffs 0 1\n"
        )

        positions = {0: 0.3, 1: 0.7}
        result_by_level = core.tikz(
            str(ef_file),
            action_label_position=positions,
            action_label_position_by="level",
        )
        result_by_player = core.tikz(
            str(ef_file),
            action_label_position=positions,
            action_label_position_by="player",
        )
        # The two modes address different keys so output must differ
        assert result_by_level != result_by_player


class TestSelectiveVaryActionLabelPositions:
    """Tests for selective vary action label positions by player or level."""

    def test_vary_by_player_selective(self, tmp_path):
        """Test vary_action_label_positions_by='player' with selective choices."""
        ef_file = tmp_path / "game.ef"
        # Player 2 is at the root with two children; player 1 has no multi-child nodes.
        # vary restricted to player 1 → no vary applied → output differs from full vary.
        ef_file.write_text(
            "player 1 name Alice\n"
            "player 2 name Bob\n"
            "level 0 node root player 2\n"
            "level 1 node child1 from 0,root player 1 move L1 payoffs 1 0\n"
            "level 1 node child2 from 0,root player 1 move R1 payoffs 0 1\n"
        )

        result_all = core.tikz(
            str(ef_file),
            vary_action_label_positions=True,
            vary_action_label_positions_by="all",
        )
        result_player1_only = core.tikz(
            str(ef_file),
            vary_action_label_positions=True,
            vary_action_label_positions_by="player",
            vary_action_label_positions_choices=[1],
        )
        # Player 1 has no multi-child nodes in this game, so restricting to
        # player 1 only suppresses the vary that would apply at the player 2 root.
        assert result_all != result_player1_only

    def test_vary_by_level_selective(self, tmp_path):
        """Test vary_action_label_positions_by='level' with selective choices."""
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(
            "player 1 name Alice\n"
            "level 0 node root player 1\n"
            "level 1 node child1 from 0,root player 1 move L1 payoffs 1 0\n"
            "level 1 node child2 from 0,root player 1 move R1 payoffs 0 1\n"
        )

        result_all = core.tikz(
            str(ef_file),
            vary_action_label_positions=True,
            vary_action_label_positions_by="all",
        )
        result_level0_only = core.tikz(
            str(ef_file),
            vary_action_label_positions=True,
            vary_action_label_positions_by="level",
            vary_action_label_positions_choices=[0],
        )
        result_no_match = core.tikz(
            str(ef_file),
            vary_action_label_positions=True,
            vary_action_label_positions_by="level",
            vary_action_label_positions_choices=[99],
        )
        # Varying only level 0 should match full vary (only one level anyway)
        assert result_all == result_level0_only
        # No matching level → no vary applied → differs from varied output
        assert result_all != result_no_match


class TestEF1Format:
    """Tests for EF 1 globally unique node identifier support."""

    def _get_ef_path(self, name):
        path = f"games/{name}"
        if not os.path.exists(path):
            path = os.path.join(os.path.dirname(__file__), "..", "games", name)
        return path

    def test_detect_ef_version_v1(self):
        """Files where 'from' references contain no commas are detected as EF 1."""
        lines = [
            "level 0 node r player 1",
            "level 2 node p from r move L",
            "level 2 node q from r move R payoffs 1 0",
        ]
        assert core._detect_ef_version(lines) == 1

    def test_detect_ef_version_v0(self):
        """Files where 'from' references use 'level,name' format (comma) are detected as EF 0."""
        lines = [
            "level 0 node 1 player 1",
            "level 2 node 1 from 0,1 move L",
            "level 2 node 2 from 0,1 move R payoffs 1 0",
        ]
        assert core._detect_ef_version(lines) == 0

    def test_detect_ef_version_example_v0(self):
        """games/example.ef is detected as EF 0 (repeated per-level node numbers)."""
        path = self._get_ef_path("example.ef")
        if not os.path.exists(path):
            pytest.skip("example.ef not found")
        lines = [
            l.strip()
            for l in open(path).read().splitlines()
            if l.strip() and not l.strip().startswith("%")
        ]
        assert core._detect_ef_version(lines) == 0

    def test_detect_ef_version_example_v1(self):
        """games/example_v1.ef is detected as EF 1."""
        path = self._get_ef_path("example_v1.ef")
        if not os.path.exists(path):
            pytest.skip("example_v1.ef not found")
        lines = [
            l.strip()
            for l in open(path).read().splitlines()
            if l.strip() and not l.strip().startswith("%")
        ]
        assert core._detect_ef_version(lines) == 1

    def test_render_v1_example(self, tmp_path):
        """EF 1 example file renders without errors."""
        path = self._get_ef_path("example_v1.ef")
        if not os.path.exists(path):
            pytest.skip("example_v1.ef not found")
        result = core.tikz(path)
        assert result is not None
        assert "tikzpicture" in result

    def test_render_v1_kuhn(self, tmp_path):
        """EF 1 Kuhn poker file renders without errors."""
        path = self._get_ef_path("kuhn_v1.ef")
        if not os.path.exists(path):
            pytest.skip("kuhn_v1.ef not found")
        result = core.tikz(path)
        assert result is not None
        assert "tikzpicture" in result

    def test_render_v1_iset_present(self):
        """EF 1 file with iset produces TikZ output containing iset drawing code."""
        path = self._get_ef_path("example_v1.ef")
        if not os.path.exists(path):
            pytest.skip("example_v1.ef not found")
        result = core.tikz(path)
        # An iset is drawn as an ellipse in TikZ
        assert "ellipse" in result or "draw" in result

    def test_v0_files_still_render(self):
        """Existing EF 0 files still render correctly (backward compatibility)."""
        path = self._get_ef_path("example.ef")
        if not os.path.exists(path):
            pytest.skip("example.ef not found")
        result = core.tikz(path)
        assert result is not None
        assert "tikzpicture" in result

    def test_v1_and_v0_same_output(self):
        """EF 1 and EF 0 versions of the same game produce equivalent TikZ output."""
        v0_path = self._get_ef_path("example.ef")
        v1_path = self._get_ef_path("example_v1.ef")
        if not os.path.exists(v0_path) or not os.path.exists(v1_path):
            pytest.skip("example.ef or example_v1.ef not found")
        result_v0 = core.tikz(v0_path)
        result_v1 = core.tikz(v1_path)

        # Strip comment lines (filename comment and source-echo %% lines) before comparing:
        # these differ between v0 and v1 due to different source text, but the rendering is identical.
        def strip_comments(s):
            return "\n".join(l for l in s.splitlines() if not l.startswith("%"))

        assert strip_comments(result_v0) == strip_comments(result_v1)


if __name__ == "__main__":
    pytest.main([__file__])


# ---------------------------------------------------------------------------
# Image conversion: pdftocairo only
# ---------------------------------------------------------------------------


class TestPdftocairo:
    """PNG and SVG come from pdflatex and pdftocairo, and from nothing else."""

    @staticmethod
    def _fake_run(calls):
        def run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "pdflatex":
                out = Path(cmd[cmd.index("-output-directory") + 1]) / "output.pdf"
                out.write_bytes(b"%PDF-fake")
            else:  # pdftocairo: the last argument is the output name
                target = Path(cmd[-1])
                if "-png" in cmd:
                    target = target.with_name(target.name + ".png")
                target.write_bytes(b"IMAGE")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        return run

    def test_png_uses_pdftocairo_with_dpi(self, tmp_path):
        calls = []
        with patch("gtdraw.core.subprocess.run", self._fake_run(calls)):
            out = core.png(
                io.StringIO("player 1\nlevel 0 node root player 1\n"),
                save_to=str(tmp_path / "o"),
                dpi=123,
            )
        assert Path(out).read_bytes() == b"IMAGE"
        assert [c[0] for c in calls] == ["pdflatex", "pdftocairo"]
        assert calls[1][1:6] == ["-png", "-r", "123", "-singlefile", calls[1][5]]

    def test_svg_uses_pdftocairo(self, tmp_path):
        calls = []
        with patch("gtdraw.core.subprocess.run", self._fake_run(calls)):
            out = core.svg(
                io.StringIO("player 1\nlevel 0 node root player 1\n"),
                save_to=str(tmp_path / "o"),
            )
        assert Path(out).read_bytes() == b"IMAGE"
        assert [c[0] for c in calls] == ["pdflatex", "pdftocairo"]
        assert calls[1][1] == "-svg"

    @pytest.mark.parametrize("func", ["png", "svg"])
    def test_missing_pdftocairo_names_tool_and_package(self, func, tmp_path):
        def run(cmd, **kwargs):
            if cmd[0] == "pdflatex":
                out = Path(cmd[cmd.index("-output-directory") + 1]) / "output.pdf"
                out.write_bytes(b"%PDF-fake")
                return subprocess.CompletedProcess(cmd, 0, "", "")
            raise FileNotFoundError(cmd[0])

        with patch("gtdraw.core.subprocess.run", run):
            with pytest.raises(RuntimeError, match="pdftocairo not found") as e:
                getattr(core, func)(
                    io.StringIO("player 1\nlevel 0 node root player 1\n"),
                    save_to=str(tmp_path / "o"),
                )
        assert "poppler" in str(e.value)

    def test_missing_pdflatex_names_tool_and_package(self, tmp_path):
        with patch("gtdraw.core.subprocess.run", side_effect=FileNotFoundError("x")):
            with pytest.raises(RuntimeError, match="pdflatex not found") as e:
                core.pdf(io.StringIO("player 1\nlevel 0 node root player 1\n"))
        assert "texlive" in str(e.value)

    @requires_tex_tools
    @pytest.mark.parametrize("func", ["png", "svg"])
    def test_images_with_only_the_tex_tools_on_path(self, func, tmp_path):
        """The image is made with a PATH holding pdflatex, pdftocairo and pdflatex's directory.

        pdflatex may need its own directory, which on Linux is /usr/bin and also holds other
        converters, so this test checks only that the image is made. That pdflatex and
        pdftocairo are the only tools called is checked by the mocked tests above.
        """
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        for tool in ("pdflatex", "pdftocairo"):
            (bin_dir / tool).symlink_to(shutil.which(tool))
        env = {"PATH": str(bin_dir) + os.pathsep + os.path.dirname(shutil.which("pdflatex"))}
        code = (
            "import sys, gtdraw\n"
            f"out = gtdraw.{func}(sys.argv[1], save_to=sys.argv[2])\n"
            "print(out)\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code, str(GAMES_DIR / "example.ef"), str(tmp_path / "ex")],
            env={**os.environ, **env},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert os.path.getsize(result.stdout.strip()) > 0
