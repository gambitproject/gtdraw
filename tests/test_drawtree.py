"""
Test suite for draw_tree module.

This module contains comprehensive tests for the game tree drawing functionality,
including unit tests for utility functions, integration tests for file processing,
and validation of TikZ output generation.
"""

import pytest
import shutil
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

import pygambit

# Import the module under test
import draw_tree.core as draw_tree


class TestUtilityFunctions:
    """Test utility functions for mathematical operations and formatting."""

    def test_fformat_default_places(self):
        """Test fformat with default 3 decimal places."""
        assert draw_tree.fformat(3.14159) == "3.142"
        assert draw_tree.fformat(3.0) == "3"
        assert draw_tree.fformat(3.100) == "3.1"

    def test_fformat_custom_places(self):
        """Test fformat with custom decimal places."""
        assert draw_tree.fformat(3.14159, 2) == "3.14"
        assert draw_tree.fformat(3.14159, 0) == "3"
        assert draw_tree.fformat(3.14159, 5) == "3.14159"

    def test_fformat_trailing_zeros(self):
        """Test fformat removes trailing zeros."""
        assert draw_tree.fformat(2.5000) == "2.5"
        assert draw_tree.fformat(2.0000) == "2"

    def test_coord(self):
        """Test coordinate pair formatting."""
        assert draw_tree.coord(1.0, 2.0) == "(1,2)"
        assert draw_tree.coord(3.14, 2.71) == "(3.14,2.71)"
        assert draw_tree.coord(-1.5, 0.0) == "(-1.5,0)"

    def test_twonorm(self):
        """Test Euclidean length calculation."""
        assert draw_tree.twonorm([3, 4]) == 5.0
        assert draw_tree.twonorm([1, 0]) == 1.0
        assert draw_tree.twonorm([0, 0]) == 0.0

    def test_aeq(self):
        """Test almost equal comparison."""
        assert draw_tree.aeq(1e-10, 0)  # Very small number should be considered zero
        assert draw_tree.aeq(1.0, 1.0)
        assert not draw_tree.aeq(1.0, 2.0)
        assert draw_tree.aeq(1.0, 1.0 + 1e-10)  # Numbers within epsilon should be equal

    def test_degrees(self):
        """Test angle calculation in degrees."""
        assert abs(draw_tree.degrees([1, 0]) - 0) < 1e-6
        assert abs(draw_tree.degrees([0, 1]) - 90) < 1e-6
        assert abs(draw_tree.degrees([-1, 0]) - 180) < 1e-6
        assert abs(draw_tree.degrees([0, -1]) - (-90)) < 1e-6

    def test_stretch(self):
        """Test vector stretching to desired length."""
        result = draw_tree.stretch([3, 4], 10)
        assert abs(draw_tree.twonorm(result) - 10) < 1e-6
        assert abs(result[0] - 6) < 1e-6
        assert abs(result[1] - 8) < 1e-6

    def test_det(self):
        """Test determinant calculation."""
        assert draw_tree.det(1, 2, 3, 4) == (1 * 4 - 2 * 3)
        assert draw_tree.det(2, 0, 0, 3) == 6


class TestStringParsing:
    """Test string parsing functions."""

    def test_splitnumtext_basic(self):
        """Test basic number-text splitting."""
        assert draw_tree.splitnumtext("2a") == (2.0, "a")
        assert draw_tree.splitnumtext(".3xyz") == (0.3, "xyz")
        assert draw_tree.splitnumtext("a") == (1, "a")
        assert draw_tree.splitnumtext("22.2xyz") == (22.2, "xyz")

    def test_splitnumtext_edge_cases(self):
        """Test edge cases for number-text splitting."""
        assert draw_tree.splitnumtext("") == (1, "")
        assert draw_tree.splitnumtext("123") == (123.0, "")
        assert draw_tree.splitnumtext(".") == (1, "")


class TestNodeOperations:
    """Test node-related operations."""

    def test_setnodeid(self):
        """Test node ID creation."""
        assert draw_tree.setnodeid(1.0, "test") == "1,test"
        assert draw_tree.setnodeid(0.5, "node") == "0.5,node"

    def test_cleannodeid(self):
        """Test node ID standardization."""
        # Mock the error function to avoid output during tests
        with patch("draw_tree.core.error"):
            assert draw_tree.cleannodeid("1,test") == "1,test"
            assert draw_tree.cleannodeid("0.5,node") == "0.5,node"
            # Test error cases
            draw_tree.cleannodeid("invalid")  # Should handle gracefully
            draw_tree.cleannodeid("x,test")  # Invalid level


class TestOutputRoutines:
    """Test output and formatting functions."""

    def test_outall(self):
        """Test output stream printing."""
        test_stream = ["line1", "line2", "line3"]
        with patch("builtins.print") as mock_print:
            draw_tree.outall(test_stream)
            assert mock_print.call_count == 3

    def test_outs(self):
        """Test single string output."""
        test_stream = []
        draw_tree.outs("test", test_stream)
        assert test_stream == ["test"]

    def test_comment(self):
        """Test comment output."""
        with patch("draw_tree.core.outs") as mock_outs:
            draw_tree.comment("test comment")
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
            result = draw_tree.readfile(temp_filename)
            expected = ["line 1", "line 2 with spaces", "line 3"]
            assert result == expected
        finally:
            os.unlink(temp_filename)

    def test_readfile_nonexistent(self):
        """Test file reading with non-existent file."""
        with pytest.raises(FileNotFoundError):
            draw_tree.readfile("nonexistent_file.txt")


class TestCommandLineProcessing:
    """Test command-line argument processing."""

    def test_commandline_scale(self):
        """Test scale argument processing."""
        original_scale = draw_tree.scale
        try:
            draw_tree.commandline(["draw_tree.py", "scale=2.5"])
            assert draw_tree.scale == 2.5
        finally:
            draw_tree.scale = original_scale

    def test_commandline_grid(self):
        """Test grid argument processing."""
        original_grid = draw_tree.grid
        try:
            draw_tree.commandline(["draw_tree.py", "grid"])
            assert draw_tree.grid is True
        finally:
            draw_tree.grid = original_grid

    def test_commandline_file(self):
        """Test file argument processing."""
        original_ef_file = getattr(draw_tree, "ef_file", None)
        try:
            draw_tree.commandline(["draw_tree.py", "test_game.ef"])
            assert draw_tree.ef_file == "test_game.ef"
        finally:
            if original_ef_file is not None:
                draw_tree.ef_file = original_ef_file

    def test_commandline_invalid_scale(self):
        """Test invalid scale argument handling."""
        original_scale = draw_tree.scale
        try:
            with patch("draw_tree.core.outs") as mock_outs:
                draw_tree.commandline(["draw_tree.py", "scale=invalid"])
                # Should output error message
                mock_outs.assert_called()
                # Scale should remain unchanged
                assert draw_tree.scale == original_scale
        finally:
            draw_tree.scale = original_scale


class TestPlayerHandling:
    """Test player parsing and management."""

    def test_player_basic(self):
        """Test basic player parsing."""
        words = ["player", "1"]
        with patch("draw_tree.core.defout"):
            p, advance = draw_tree.player(words)
            assert p == 1
            assert advance == 2

    def test_player_with_name(self):
        """Test player parsing with name."""
        words = ["player", "2", "name", "Alice"]
        with patch("draw_tree.core.defout"):
            p, advance = draw_tree.player(words)
            assert p == 2
            assert advance == 4
            assert draw_tree.playername[2] == "Alice"

    def test_player_invalid_number(self):
        """Test player parsing with invalid number."""
        words = ["player", "invalid"]
        with patch("draw_tree.core.error") as mock_error:
            p, advance = draw_tree.player(words)
            assert p == -1
            mock_error.assert_called()


class TestGeometryFunctions:
    """Test geometric operations for tree layout."""

    def test_isonlineseg_basic(self):
        """Test point-on-line-segment detection."""
        # Point on line segment
        assert draw_tree.isonlineseg([0, 0], [1, 1], [2, 2]) is True
        # Point on line segment (slope 2)
        assert draw_tree.isonlineseg([0, 0], [1, 2], [2, 4]) is True
        # Point not on line segment
        assert draw_tree.isonlineseg([0, 0], [1, 3], [2, 4]) is False
        # Point at endpoint
        assert draw_tree.isonlineseg([0, 0], [0, 0], [1, 1]) is True

    def test_makearc_basic(self):
        """Test arc generation."""
        # Test with simple coordinates
        result = draw_tree.makearc([0, 0], [1, 0], [2, 0])
        assert isinstance(result, str)
        assert "arc(" in result


class TestDrawTreeFunction:
    """Test the new streamlined draw_tree function."""

    def test_draw_tree_basic(self):
        """Test basic draw_tree functionality."""
        # Create a simple .ef file for testing
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\n")
            ef_file.write("level 0 node root player 1\n")
            ef_file.write("level 1 node left from 0,root player 2 payoffs 1 2\n")
            ef_file_path = ef_file.name

        try:
            result = draw_tree.generate_tikz(ef_file_path)

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

    def test_draw_tree_calls_ipython_magic_when_available(self):
        """When IPython is available, draw_tree should load the jupyter_tikz
        extension if needed and call the tikz cell magic with the generated code.
        """
        # Create a simple .ef file for testing
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\n")
            ef_file.write("level 0 node root player 1\n")
            ef_file_path = ef_file.name

        class DummyEM:
            def __init__(self, loaded=None):
                self.loaded = loaded or set()

        class DummyIP:
            def __init__(self, em):
                self.extension_manager = em
                self._loaded_magics = []
                self._run_cell_magic_calls = []

            def run_line_magic(self, name, arg):
                # record that load_ext was called
                self._loaded_magics.append((name, arg))

            def run_cell_magic(self, magic_name, args, code):
                # record call and return a sentinel
                self._run_cell_magic_calls.append((magic_name, args, code))
                return "MAGIC-RESULT"

        try:
            # Case 1: extension already loaded
            em = DummyEM(loaded={"jupyter_tikz"})
            ip = DummyIP(em)
            with patch("draw_tree.core.get_ipython", return_value=ip):
                res = draw_tree.draw_tree(ef_file_path)
                # Should call run_cell_magic and return its value
                assert res == "MAGIC-RESULT"

            # Case 2: extension not loaded -> run_line_magic should be called
            em2 = DummyEM(loaded=set())
            ip2 = DummyIP(em2)
            with patch("draw_tree.core.get_ipython", return_value=ip2):
                res2 = draw_tree.draw_tree(ef_file_path)
                assert res2 == "MAGIC-RESULT"
                # run_line_magic should have been called to load the extension
                assert ("load_ext", "jupyter_tikz") in ip2._loaded_magics

        finally:
            os.unlink(ef_file_path)

    def test_draw_tree_with_options(self):
        """Test draw_tree with different options."""
        # Create a simple .ef file for testing
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\n")
            ef_file.write("level 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Test with scale
            result_scaled = draw_tree.generate_tikz(ef_file_path, scale_factor=2.0)
            assert "scale=1.6" in result_scaled  # 2 * 0.8

            # Test with grid
            result_grid = draw_tree.generate_tikz(ef_file_path, show_grid=True)
            assert "\\draw [help lines, color=green]" in result_grid

            # Test without grid (default)
            result_no_grid = draw_tree.generate_tikz(ef_file_path, show_grid=False)
            assert "% \\draw [help lines, color=green]" in result_no_grid

        finally:
            os.unlink(ef_file_path)

    def test_draw_tree_missing_files(self):
        """Test draw_tree with missing files."""
        # Test with missing .ef file
        with pytest.raises(FileNotFoundError):
            draw_tree.generate_tikz("nonexistent.ef")

        # Test with valid .ef file (should work with built-in macros)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            result = draw_tree.generate_tikz(ef_file_path)
            # Should work with built-in macros
            assert "\\begin{tikzpicture}" in result
        finally:
            os.unlink(ef_file_path)


class TestPngGeneration:
    """Test PNG generation functionality."""

    def test_generate_png_missing_file(self):
        """Test PNG generation with missing .ef file."""
        with pytest.raises(FileNotFoundError):
            draw_tree.generate_png("nonexistent.ef")

    @patch("draw_tree.core.subprocess.run")
    def test_generate_png_pdflatex_not_found(self, mock_run):
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
                draw_tree.generate_png(ef_file_path)
        finally:
            os.unlink(ef_file_path)

    def test_generate_png_default_parameters(self):
        """Test PNG generation with default parameters."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Mock both pdflatex and convert being unavailable to test error handling
            with patch("draw_tree.core.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")

                with pytest.raises(RuntimeError):
                    draw_tree.generate_png(ef_file_path)
        finally:
            os.unlink(ef_file_path)

    def test_generate_png_custom_dpi(self):
        """Test PNG generation with custom DPI setting."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Test that custom DPI is handled properly
            with patch("draw_tree.core.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")

                with pytest.raises(RuntimeError):
                    draw_tree.generate_png(ef_file_path, dpi=600)
        finally:
            os.unlink(ef_file_path)

    def test_generate_png_output_filename(self):
        """Test PNG generation with custom output filename."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with patch("draw_tree.core.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")

                with pytest.raises(RuntimeError):
                    draw_tree.generate_png(ef_file_path, save_to="custom_name.png")
        finally:
            os.unlink(ef_file_path)


class TestSvgGeneration:
    """Test SVG generation functionality."""

    def test_generate_svg_missing_file(self):
        with pytest.raises(FileNotFoundError):
            draw_tree.generate_svg("nonexistent.ef")

    @patch("draw_tree.core.subprocess.run")
    def test_generate_svg_pdflatex_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("pdflatex not found")
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with pytest.raises(RuntimeError, match="pdflatex not found"):
                draw_tree.generate_svg(ef_file_path)
        finally:
            os.unlink(ef_file_path)

    def test_generate_svg_default_parameters(self):
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with patch("draw_tree.core.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")
                with pytest.raises(RuntimeError):
                    draw_tree.generate_svg(ef_file_path)
        finally:
            os.unlink(ef_file_path)

    def test_generate_svg_output_filename(self):
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with patch("draw_tree.core.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")
                with pytest.raises(RuntimeError):
                    draw_tree.generate_svg(ef_file_path, save_to="custom_name.svg")
        finally:
            os.unlink(ef_file_path)


class TestTexGeneration:
    """Test LaTeX document generation functionality."""

    def test_generate_tex_missing_file(self):
        """Test LaTeX generation with missing .ef file."""
        with pytest.raises(FileNotFoundError):
            draw_tree.generate_tex("nonexistent.ef")

    def test_generate_tex_default_parameters(self):
        """Test LaTeX generation with default parameters."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Generate LaTeX file
            tex_path = draw_tree.generate_tex(ef_file_path)

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

    def test_generate_tex_custom_filename(self):
        """Test LaTeX generation with custom output filename."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            custom_filename = "custom_output.tex"
            tex_path = draw_tree.generate_tex(ef_file_path, save_to=custom_filename)

            # Verify the custom filename was used
            assert tex_path.endswith(custom_filename)
            assert os.path.exists(custom_filename)

            # Clean up
            os.unlink(custom_filename)

        finally:
            os.unlink(ef_file_path)

    def test_generate_tex_with_scale_and_grid(self):
        """Test LaTeX generation with scale and grid options."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ef"
        ) as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            tex_path = draw_tree.generate_tex(
                ef_file_path, scale_factor=2.0, show_grid=True
            )

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
        result = draw_tree.commandline(["draw_tree.py", "test.ef", "--png"])
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
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
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
        result = draw_tree.commandline(
            ["draw_tree.py", "test.ef", "--png", "--dpi=600"]
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
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
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
        result = draw_tree.commandline(
            ["draw_tree.py", "test.ef", "--output=custom.png"]
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
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
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
        result = draw_tree.commandline(
            ["draw_tree.py", "test.ef", "--output=custom.pdf"]
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
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
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
        result = draw_tree.commandline(["draw_tree.py", "test.ef", "--tex"])
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
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
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
        result = draw_tree.commandline(
            ["draw_tree.py", "test.ef", "--output=custom.tex"]
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
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
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
        result = draw_tree.commandline(["draw_tree.py", "test.ef", "--png", "--dpi=50"])
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
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
        ) = result
        assert dpi == 300  # Should default to 300 for out-of-range values

        # Too high DPI should default to 300
        result = draw_tree.commandline(
            ["draw_tree.py", "test.ef", "--png", "--dpi=5000"]
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
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
        ) = result
        assert dpi == 300  # Should default to 300 for out-of-range values

    def test_commandline_invalid_dpi_string(self):
        """Test non-numeric DPI values."""
        result = draw_tree.commandline(
            ["draw_tree.py", "test.ef", "--png", "--dpi=high"]
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
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
        ) = result
        assert dpi == 300  # Should default to 300 for invalid values

    def test_commandline_svg_flag(self):
        """Test --svg flag parsing."""
        result = draw_tree.commandline(["draw_tree.py", "test.ef", "--svg"])
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
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
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
        result = draw_tree.commandline(
            ["draw_tree.py", "test.ef", "--output=custom.svg"]
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
            action_label_dist,
            iset_fill,
            iset_fill_opacity,
            iset_boundary,
            node_size,
            color_scheme,
            edge_thickness,
            action_label_position,
            level_scaling,
            sublevel_scaling,
            width_scaling,
            shared_terminal_depth,
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
    result = draw_tree.commandline(["draw_tree", "game.ef", "--action-label-dist=2.5"])
    assert result[13] == 2.5


# ---------------------------------------------------------------------------
# Skip markers for integration tests requiring external tools
# ---------------------------------------------------------------------------

requires_pdflatex = pytest.mark.skipif(
    shutil.which("pdflatex") is None,
    reason="pdflatex not available",
)

requires_pdf_to_png = pytest.mark.skipif(
    shutil.which("pdflatex") is None
    or (
        shutil.which("convert") is None
        and shutil.which("gs") is None
        and shutil.which("pdftoppm") is None
    ),
    reason="pdflatex and a PDF-to-PNG converter (convert/gs/pdftoppm) required",
)

requires_pdf2svg = pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("pdf2svg") is None,
    reason="pdflatex and pdf2svg required",
)


# ---------------------------------------------------------------------------
# Helpers for integration tests
# ---------------------------------------------------------------------------

GAMES_DIR = Path(__file__).resolve().parents[1] / "games"


def _simple_ef_content():
    """Minimal valid .ef content for integration tests."""
    return "player 1\nlevel 0 node root player 1\n"


def _make_pygambit_game():
    """Create a small pygambit game for end-to-end tests."""
    g = pygambit.Game.new_tree(players=["Alice", "Bob"], title="integration_test")
    g.append_move(g.root, g.players[0], ["Left", "Right"])
    g.append_move(g.root.children[0], g.players[1], ["Up", "Down"])
    g.set_outcome(g.root.children[0].children[0], g.add_outcome([1, 0]))
    g.set_outcome(g.root.children[0].children[1], g.add_outcome([0, 1]))
    g.set_outcome(g.root.children[1], g.add_outcome([2, 2]))
    return g


# ---------------------------------------------------------------------------
# PDF generation integration tests
# ---------------------------------------------------------------------------


class TestPdfGenerationIntegration:
    """Integration tests that actually compile LaTeX to PDF."""

    @requires_pdflatex
    def test_generate_pdf_from_ef_file(self, tmp_path):
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(_simple_ef_content())
        pdf_path = draw_tree.generate_pdf(
            str(ef_file), save_to=str(tmp_path / "out.pdf")
        )
        assert os.path.isfile(pdf_path)
        assert os.path.getsize(pdf_path) > 0
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

    @requires_pdflatex
    def test_generate_pdf_save_to_custom_path(self, tmp_path):
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(_simple_ef_content())
        custom = str(tmp_path / "subdir" / "custom.pdf")
        os.makedirs(os.path.dirname(custom), exist_ok=True)
        pdf_path = draw_tree.generate_pdf(str(ef_file), save_to=custom)
        assert pdf_path == str(Path(custom).absolute())
        assert os.path.isfile(pdf_path)

    @requires_pdflatex
    def test_generate_pdf_from_pygambit_game(self, tmp_path):
        """End-to-end: pygambit Game → .ef → .tex → .pdf"""
        g = _make_pygambit_game()
        pdf_path = draw_tree.generate_pdf(g, save_to=str(tmp_path / "pygambit.pdf"))
        assert os.path.isfile(pdf_path)
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

    @requires_pdflatex
    def test_generate_pdf_from_repo_ef_file(self, tmp_path):
        """Test with a real game file from the repository."""
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        pdf_path = draw_tree.generate_pdf(
            str(ef_file), save_to=str(tmp_path / "x1.pdf")
        )
        assert os.path.isfile(pdf_path)
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"


# ---------------------------------------------------------------------------
# PNG generation integration tests
# ---------------------------------------------------------------------------


class TestPngGenerationIntegration:
    """Integration tests that actually generate PNG images."""

    @requires_pdf_to_png
    def test_generate_png_from_ef_file(self, tmp_path):
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(_simple_ef_content())
        png_path = draw_tree.generate_png(
            str(ef_file), save_to=str(tmp_path / "out.png")
        )
        assert os.path.isfile(png_path)
        assert os.path.getsize(png_path) > 0
        with open(png_path, "rb") as f:
            assert f.read(4) == b"\x89PNG"

    @requires_pdf_to_png
    def test_generate_png_from_pygambit_game(self, tmp_path):
        """End-to-end: pygambit Game → .ef → .tex → .pdf → .png"""
        g = _make_pygambit_game()
        png_path = draw_tree.generate_png(g, save_to=str(tmp_path / "pygambit.png"))
        assert os.path.isfile(png_path)
        with open(png_path, "rb") as f:
            assert f.read(4) == b"\x89PNG"


# ---------------------------------------------------------------------------
# SVG generation integration tests
# ---------------------------------------------------------------------------


class TestSvgGenerationIntegration:
    """Integration tests that actually generate SVG files."""

    @requires_pdf2svg
    def test_generate_svg_from_ef_file(self, tmp_path):
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(_simple_ef_content())
        svg_path = draw_tree.generate_svg(
            str(ef_file), save_to=str(tmp_path / "out.svg")
        )
        assert os.path.isfile(svg_path)
        assert os.path.getsize(svg_path) > 0
        with open(svg_path) as f:
            content = f.read()
        assert "<svg" in content

    @requires_pdf2svg
    def test_generate_svg_from_pygambit_game(self, tmp_path):
        """End-to-end: pygambit Game → .ef → .tex → .pdf → .svg"""
        g = _make_pygambit_game()
        svg_path = draw_tree.generate_svg(g, save_to=str(tmp_path / "pygambit.svg"))
        assert os.path.isfile(svg_path)
        with open(svg_path) as f:
            content = f.read()
        assert "<svg" in content

    @requires_pdf2svg
    def test_generate_svg_responsive(self, tmp_path):
        """Verify that responsive_sizing=True modifies the SVG content."""
        ef_file = tmp_path / "game.ef"
        ef_file.write_text(_simple_ef_content())
        svg_path = draw_tree.generate_svg(
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
# TikZ / generate_tikz option tests
# ---------------------------------------------------------------------------


class TestGenerateTikzOptions:
    """Test generate_tikz with various options (replacing tutorial notebook
    coverage for option variants)."""

    def test_color_scheme_default(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result = draw_tree.generate_tikz(str(ef_file), color_scheme="default")
        assert "\\begin{tikzpicture}" in result

    def test_color_scheme_gambit(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result = draw_tree.generate_tikz(str(ef_file), color_scheme="gambit")
        assert "\\begin{tikzpicture}" in result

    def test_color_scheme_distinctipy(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result = draw_tree.generate_tikz(str(ef_file), color_scheme="distinctipy")
        assert "\\begin{tikzpicture}" in result

    def test_color_scheme_colorblind(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result = draw_tree.generate_tikz(str(ef_file), color_scheme="colorblind")
        assert "\\begin{tikzpicture}" in result

    def test_scale_factor_affects_output(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result_default = draw_tree.generate_tikz(str(ef_file))
        result_scaled = draw_tree.generate_tikz(str(ef_file), scale_factor=2.0)
        assert result_default != result_scaled
        assert "scale=1.6" in result_scaled  # 2.0 * 0.8

    def test_edge_thickness_and_action_label_position(self):
        ef_file = GAMES_DIR / "x1.ef"
        if not ef_file.exists():
            pytest.skip("Repository game file not found")
        result = draw_tree.generate_tikz(
            str(ef_file), edge_thickness=2.0, action_label_position=0.8
        )
        assert "\\treethickn2.0pt" in result
        assert "\\begin{tikzpicture}" in result

    def test_pygambit_game_with_layout_options(self, tmp_path):
        """Test pygambit-specific options: level_scaling, sublevel_scaling,
        width_scaling, shared_terminal_depth, hide_action_labels."""
        g = _make_pygambit_game()
        result = draw_tree.generate_tikz(
            g,
            save_to=str(tmp_path / "opts.ef"),
            level_scaling=2,
            sublevel_scaling=2,
            width_scaling=2,
            shared_terminal_depth=True,
            hide_action_labels=True,
        )
        assert "\\begin{tikzpicture}" in result
        # hide_action_labels means no "move" keyword in the intermediate .ef
        ef_content = (tmp_path / "opts.ef").read_text()
        assert "move" not in ef_content


# ---------------------------------------------------------------------------
# Smoke test: generate_tikz over all repo .efg files via pygambit
# ---------------------------------------------------------------------------


def _find_efg_files():
    """Return list of .efg paths under games/efg/."""
    efg_dir = GAMES_DIR / "efg"
    if not efg_dir.exists():
        return []
    return sorted(efg_dir.glob("*.efg"))


_EFG_FILES = _find_efg_files()


@pytest.mark.parametrize("efg_path", _EFG_FILES, ids=[p.name for p in _EFG_FILES])
def test_pygambit_generate_tikz_smoke(efg_path, tmp_path):
    """Smoke test: read each .efg with pygambit and generate TikZ without
    crashing. This replaces the tutorial notebooks' role as a crash-check
    for the pygambit → draw_tree pipeline."""
    g = pygambit.read_efg(str(efg_path))
    result = draw_tree.generate_tikz(g, save_to=str(tmp_path / "smoke.ef"))
    assert isinstance(result, str)
    assert "\\begin{tikzpicture}" in result
    assert len(result) > 100  # sanity check: non-trivial output


@pytest.mark.parametrize("efg_path", _EFG_FILES, ids=[p.name for p in _EFG_FILES])
@requires_pdflatex
def test_pygambit_generate_pdf_smoke(efg_path, tmp_path):
    """Smoke test: read each .efg with pygambit and generate PDF.
    Verifies the full pipeline doesn't crash and produces a valid PDF."""
    g = pygambit.read_efg(str(efg_path))
    pdf_path = draw_tree.generate_pdf(g, save_to=str(tmp_path / "smoke.pdf"))
    assert os.path.isfile(pdf_path)
    with open(pdf_path, "rb") as f:
        assert f.read(4) == b"%PDF"


class TestFontStyling:
    """Test font styling in TikZ output."""

    def test_generate_tikz_font_styles(self):
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

            result = draw_tree.generate_tikz(
                ef2_path, font_family="sffamily", font_bold=True, font_italic=True
            )
            assert (
                "every node/.append style={font=\\sffamily\\bfseries\\itshape, execute at begin node=\\boldmath}"
                in result
            )

            # Action labels should also be present
            assert "Move" in result

            # Test font size
            result_size = draw_tree.generate_tikz(ef2_path, font_size="large")
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
            assert draw_tree.count_players(ef_file_path) == 2
            # Chance player name should be capitalized
            assert draw_tree.playername[0] == "Chance"
        finally:
            os.unlink(ef_file_path)

    def test_custom_color_definitions(self):
        """Test custom color LaTeX definitions."""
        custom_colors = {0: "#759138", 1: "#FF0000", 2: "#0000FF"}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = f.name

        try:
            result = draw_tree.generate_tikz(
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
            result = draw_tree.generate_tikz(ef_file_path, edge_thickness=2.5)
            # The iset draw command should contain the line width/thickn
            assert "line width=\\treethickn" in result
            assert "\\treethickn2.5pt" in result
        finally:
            os.unlink(ef_file_path)


def test_commandline_font_options():
    """Test font-related argument parsing."""
    # Test font family
    result = draw_tree.commandline(["draw_tree.py", "test.ef", "--font=sans-serif"])
    assert result[7] == "sffamily"

    result = draw_tree.commandline(["draw_tree.py", "test.ef", "--font=monospace"])
    assert result[7] == "ttfamily"

    # Test bold/italic flags
    result = draw_tree.commandline(["draw_tree.py", "test.ef", "--bold", "--italic"])
    assert result[8] is True  # bold
    assert result[9] is True  # italic

    # Test font size
    result = draw_tree.commandline(["draw_tree.py", "test.ef", "--font-size=large"])
    assert result[10] == "large"


def test_commandline_horizontal_flag():
    """Test --horizontal flag parsing."""
    result = draw_tree.commandline(["draw_tree.py", "test.ef", "--horizontal"])
    assert result[12] is True


def test_commandline_color_scheme():
    """Test parsing of the --color-scheme option."""
    result = draw_tree.commandline(
        ["draw_tree.py", "test.ef", "--color-scheme=distinctipy"]
    )
    assert result[18] == "distinctipy"


def test_commandline_edge_and_label_options():
    """Test parsing of edge thickness and action label position options."""
    result = draw_tree.commandline(
        [
            "draw_tree.py",
            "test.ef",
            "--edge-thickness=2.0",
            "--action-label-position=0.7",
        ]
    )
    assert result[19] == 2.0
    assert result[20] == 0.7


def test_commandline_efg_scaling_options():
    """Test parsing of scaling and layout options specific to EFG files."""
    result = draw_tree.commandline(
        [
            "draw_tree.py",
            "test.ef",
            "--level-scaling=1.5",
            "--sublevel-scaling=0.8",
            "--width-scaling=1.2",
            "--shared-terminal-depth",
        ]
    )
    assert result[21] == 1.5
    assert result[22] == 0.8
    assert result[23] == 1.2
    assert result[24] is True


class TestHorizontalLayout:
    """Test horizontal layout specific features."""

    def test_horizontal_tikz_output(self):
        """Test that horizontal layout injects correct TikZ rotation."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = f.name

        try:
            result = draw_tree.generate_tikz(ef_file_path, horizontal=True)

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

            result2 = draw_tree.generate_tikz(ef2_path, horizontal=True)
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
            res_v = draw_tree.generate_tikz(ef_file_path, color_scheme="gambit")
            # Horizontal legend
            res_h = draw_tree.generate_tikz(
                ef_file_path, color_scheme="gambit", horizontal=True
            )

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

    def test_horizontal_payoff_position(self):
        """Test that payoffs are positioned to the right in horizontal mode."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ef") as f:
            f.write("player 1\n")
            f.write("level 0 node n1 player 1 payoffs 1 2\n")
            ef_file_path = f.name

        try:
            result = draw_tree.generate_tikz(ef_file_path, horizontal=True)
            # Payoffs should use node[xshift=0.6cm,...] (centered) instead of node[right,...]
            assert "node[xshift=0.6cm,yshift=" in result
            assert "node[right,yshift=" not in result
        finally:
            os.unlink(ef_file_path)


def test_commandline_custom_colors():
    """Test custom color argument parsing."""
    result = draw_tree.commandline(
        ["draw_tree.py", "test.ef", '--custom-colors="0:#FF0000,1:#0000FF"']
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
        res1 = draw_tree.generate_tikz(ef_file_path, action_label_dist=1.0)
        if not ("xshift=0.5mm" in res1 or "xshift=-0.5mm" in res1):
            print(f"DEBUG: res1=\n{res1}")
        assert "xshift=0.5mm" in res1 or "xshift=-0.5mm" in res1

        # Custom dist=2.0 -> 1.0mm
        res2 = draw_tree.generate_tikz(ef_file_path, action_label_dist=2.0)
        assert "xshift=1mm" in res2 or "xshift=-1mm" in res2

        # Horizontal dist=2.0 -> yshift 1mm
        res3 = draw_tree.generate_tikz(
            ef_file_path, action_label_dist=2.0, horizontal=True
        )
        assert "yshift=1mm" in res3 or "yshift=-1mm" in res3
    except Exception as e:
        raise e


def test_commandline_iset_options():
    """Test parsing of information set styling flags."""
    # Test all flags together
    result = draw_tree.commandline(
        [
            "draw_tree.py",
            "test.ef",
            "--iset-fill",
            "--iset-fill-opacity=0.5",
            "--iset-boundary=dotted",
            "--node-size=2.0",
        ]
    )
    assert result[14] is True  # iset_fill
    assert result[15] == 0.5  # iset_fill_opacity
    assert result[16] == "dotted"  # iset_boundary
    assert result[17] == 2.0  # node_size

    # Test individual flags
    result_fill = draw_tree.commandline(["draw_tree.py", "test.ef", "--iset-fill"])
    assert result_fill[14] is True
    assert result_fill[15] == 0.2  # Default
    assert result_fill[16] == "solid"

    result_dotted = draw_tree.commandline(["draw_tree.py", "test.ef", "--iset-dotted"])
    assert result_dotted[16] == "dotted"

    result_none = draw_tree.commandline(
        ["draw_tree.py", "test.ef", "--iset-boundary=none"]
    )
    assert result_none[16] == "none"


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
        res_default = draw_tree.generate_tikz(ef_file_path, color_scheme="gambit")
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
        res_fill = draw_tree.generate_tikz(
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
        res_dotted = draw_tree.generate_tikz(
            ef_file_path, color_scheme="gambit", iset_boundary="dotted"
        )
        iset_draw_dotted = [
            line
            for line in res_dotted.split("\n")
            if "\\draw [" in line and "playertwocolor" in line
        ]
        assert "dotted" in iset_draw_dotted[0]

        # 4. None (invisible)
        res_none = draw_tree.generate_tikz(
            ef_file_path, color_scheme="gambit", iset_boundary="none"
        )
        iset_draw_none = [
            line
            for line in res_none.split("\n")
            if "\\draw [" in line and "playertwocolor" in line
        ]
        assert "draw=none" in iset_draw_none[0]


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
    res1 = draw_tree.generate_tikz(ef_file_path, node_size=1.5)
    assert "\\ndiam1.5mm" in res1
    assert "\\sqwidth1.6mm" in res1

    # Custom size=2.0mm
    res2 = draw_tree.generate_tikz(ef_file_path, node_size=2.0)
    assert "\\ndiam2.0mm" in res2
    assert "\\sqwidth2.1mm" in res2


def test_payoff_font_family():
    """Test that payoffs pick up the sans-serif font family via \mathsf."""
    ef_file_path = "games/example.ef"
    if not os.path.exists(ef_file_path):
        ef_file_path = os.path.join(
            os.path.dirname(__file__), "..", "games", "example.ef"
        )
        if not os.path.exists(ef_file_path):
            return

    # Serif (default)
    res_serif = draw_tree.generate_tikz(ef_file_path, font_family="rmfamily")
    assert "$\\mathsf{" not in res_serif

    # Sans-serif
    res_sans = draw_tree.generate_tikz(ef_file_path, font_family="sffamily")
    assert "$\\mathsf{" in res_sans


if __name__ == "__main__":
    pytest.main([__file__])
