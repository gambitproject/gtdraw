"""
Test suite for draw_tree module.

This module contains comprehensive tests for the game tree drawing functionality,
including unit tests for utility functions, integration tests for file processing,
and validation of TikZ output generation.
"""

import pytest
import tempfile
import os
from unittest.mock import patch

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
        import math
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
        with patch('draw_tree.core.error'):
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
        with patch('builtins.print') as mock_print:
            draw_tree.outall(test_stream)
            assert mock_print.call_count == 3

    def test_outs(self):
        """Test single string output."""
        test_stream = []
        draw_tree.outs("test", test_stream)
        assert test_stream == ["test"]

    def test_comment(self):
        """Test comment output."""
        with patch('draw_tree.core.outs') as mock_outs:
            draw_tree.comment("test comment")
            mock_outs.assert_called_with("%% test comment")


class TestFileOperations:
    """Test file reading and processing."""

    def test_readfile(self):
        """Test file reading with line processing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
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
        original_ef_file = getattr(draw_tree, 'ef_file', None)
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
            with patch('draw_tree.core.outs') as mock_outs:
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
        with patch('draw_tree.core.defout'):
            p, advance = draw_tree.player(words)
            assert p == 1
            assert advance == 2

    def test_player_with_name(self):
        """Test player parsing with name."""
        words = ["player", "2", "name", "Alice"]
        with patch('draw_tree.core.defout'):
            p, advance = draw_tree.player(words)
            assert p == 2
            assert advance == 4
            assert draw_tree.playername[2] == "Alice"

    def test_player_invalid_number(self):
        """Test player parsing with invalid number."""
        words = ["player", "invalid"]
        with patch('draw_tree.core.error') as mock_error:
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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
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
            assert "\\newcommand\\chancecolor" in result
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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
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
            em = DummyEM(loaded={'jupyter_tikz'})
            ip = DummyIP(em)
            with patch('draw_tree.core.get_ipython', return_value=ip):
                res = draw_tree.draw_tree(ef_file_path)
                # Should call run_cell_magic and return its value
                assert res == "MAGIC-RESULT"

            # Case 2: extension not loaded -> run_line_magic should be called
            em2 = DummyEM(loaded=set())
            ip2 = DummyIP(em2)
            with patch('draw_tree.core.get_ipython', return_value=ip2):
                res2 = draw_tree.draw_tree(ef_file_path)
                assert res2 == "MAGIC-RESULT"
                # run_line_magic should have been called to load the extension
                assert ('load_ext', 'jupyter_tikz') in ip2._loaded_magics

        finally:
            os.unlink(ef_file_path)

    def test_draw_tree_with_options(self):
        """Test draw_tree with different options."""
        # Create a simple .ef file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            result = draw_tree.generate_tikz(ef_file_path)
            # Should work with built-in macros
            assert "\\begin{tikzpicture}" in result
            assert "\\newcommand\\chancecolor" in result
        finally:
            os.unlink(ef_file_path)


class TestPngGeneration:
    """Test PNG generation functionality."""

    def test_generate_png_missing_file(self):
        """Test PNG generation with missing .ef file."""
        with pytest.raises(FileNotFoundError):
            draw_tree.generate_png("nonexistent.ef")

    @patch('draw_tree.core.subprocess.run')
    def test_generate_png_pdflatex_not_found(self, mock_run):
        """Test PNG generation when pdflatex is not available."""
        # Mock pdflatex not being found
        mock_run.side_effect = FileNotFoundError("pdflatex not found")
        
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Mock both pdflatex and convert being unavailable to test error handling
            with patch('draw_tree.core.subprocess.run') as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")
                
                with pytest.raises(RuntimeError):
                    draw_tree.generate_png(ef_file_path)
        finally:
            os.unlink(ef_file_path)

    def test_generate_png_custom_dpi(self):
        """Test PNG generation with custom DPI setting."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Test that custom DPI is handled properly
            with patch('draw_tree.core.subprocess.run') as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")
                
                with pytest.raises(RuntimeError):
                    draw_tree.generate_png(ef_file_path, dpi=600)
        finally:
            os.unlink(ef_file_path)

    def test_generate_png_output_filename(self):
        """Test PNG generation with custom output filename."""
        # Create a temporary .ef file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with patch('draw_tree.core.subprocess.run') as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")
                
                with pytest.raises(RuntimeError):
                    draw_tree.generate_png(ef_file_path, save_to="custom_name.png")
        finally:
            os.unlink(ef_file_path)


class TestSvgGeneration:
    """Test SVG generation functionality."""

    def test_generate_svg_missing_file(self):
        """Test SVG generation with missing .ef file."""
        with pytest.raises(FileNotFoundError):
            draw_tree.generate_svg("nonexistent.ef")

    @patch('draw_tree.core.generate_pdf')
    @patch('draw_tree.core.subprocess.run')
    def test_generate_svg_pdf2svg_not_found(self, mock_run, mock_generate_pdf):
        """Test SVG generation when pdf2svg is not available."""
        mock_generate_pdf.return_value = "/tmp/temp_output.pdf"
        mock_run.side_effect = FileNotFoundError("pdf2svg not found")

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            with pytest.raises(RuntimeError, match="pdf2svg not found"):
                draw_tree.generate_svg(ef_file_path)
        finally:
            os.unlink(ef_file_path)

    @patch('draw_tree.core.generate_pdf')
    @patch('draw_tree.core.subprocess.run')
    def test_generate_svg_output_filename(self, mock_run, mock_generate_pdf):
        """Test SVG generation with custom output filename."""
        mock_generate_pdf.return_value = "/tmp/temp_output.pdf"

        def fake_pdf2svg(command, capture_output, text, check):
            output_path = command[2]
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("<svg></svg>")
            return None

        mock_run.side_effect = fake_pdf2svg

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            custom_filename = "custom_output.svg"
            svg_path = draw_tree.generate_svg(ef_file_path, save_to=custom_filename)

            assert svg_path.endswith(custom_filename)
            assert os.path.exists(custom_filename)
            mock_generate_pdf.assert_called_once()
            mock_run.assert_called_once()

            os.unlink(custom_filename)
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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            # Generate LaTeX file
            tex_path = draw_tree.generate_tex(ef_file_path)
            
            # Verify the file was created and contains expected content
            assert os.path.exists(tex_path)
            
            with open(tex_path, 'r') as f:
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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ef') as ef_file:
            ef_file.write("player 1\nlevel 0 node root player 1\n")
            ef_file_path = ef_file.name

        try:
            tex_path = draw_tree.generate_tex(ef_file_path, scale_factor=2.0, show_grid=True)
            
            # Verify the file was created
            assert os.path.exists(tex_path)
            
            with open(tex_path, 'r') as f:
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
        result = draw_tree.commandline(['draw_tree.py', 'test.ef', '--png'])
        output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi = result
        assert output_mode == "png"
        assert not pdf_requested
        assert png_requested
        assert not tex_requested
        assert output_file is None
        assert dpi is None

    def test_commandline_png_with_dpi(self):
        """Test --png flag with --dpi option."""
        result = draw_tree.commandline(['draw_tree.py', 'test.ef', '--png', '--dpi=600'])
        output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi = result
        assert output_mode == "png"
        assert not pdf_requested
        assert png_requested
        assert not tex_requested
        assert output_file is None
        assert dpi == 600

    def test_commandline_png_output_file(self):
        """Test PNG output with custom filename."""
        result = draw_tree.commandline(['draw_tree.py', 'test.ef', '--output=custom.png'])
        output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi = result
        assert output_mode == "png"
        assert not pdf_requested
        assert png_requested
        assert not tex_requested
        assert output_file == "custom.png"
        assert dpi is None

    def test_commandline_pdf_output_file(self):
        """Test PDF output with custom filename."""
        result = draw_tree.commandline(['draw_tree.py', 'test.ef', '--output=custom.pdf'])
        output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi = result
        assert output_mode == "pdf"
        assert pdf_requested
        assert not png_requested
        assert not tex_requested
        assert output_file == "custom.pdf"
        assert dpi is None

    def test_commandline_tex_flag(self):
        """Test --tex flag parsing."""
        result = draw_tree.commandline(['draw_tree.py', 'test.ef', '--tex'])
        output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi = result
        assert output_mode == "tex"
        assert not pdf_requested
        assert not png_requested
        assert tex_requested
        assert output_file is None
        assert dpi is None

    def test_commandline_tex_output_file(self):
        """Test LaTeX output with custom filename."""
        result = draw_tree.commandline(['draw_tree.py', 'test.ef', '--output=custom.tex'])
        output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi = result
        assert output_mode == "tex"
        assert not pdf_requested
        assert not png_requested
        assert tex_requested
        assert output_file == "custom.tex"
        assert dpi is None

    def test_commandline_invalid_dpi(self):
        """Test invalid DPI values."""
        # Too low DPI should default to 300
        result = draw_tree.commandline(['draw_tree.py', 'test.ef', '--png', '--dpi=50'])
        output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi = result
        assert dpi == 300  # Should default to 300 for out-of-range values

        # Too high DPI should default to 300
        result = draw_tree.commandline(['draw_tree.py', 'test.ef', '--png', '--dpi=5000'])
        output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi = result
        assert dpi == 300  # Should default to 300 for out-of-range values

    def test_commandline_invalid_dpi_string(self):
        """Test non-numeric DPI values."""
        result = draw_tree.commandline(['draw_tree.py', 'test.ef', '--png', '--dpi=high'])
        output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi = result
        assert dpi == 300  # Should default to 300 for invalid values


def test_efg_dl_ef_conversion_examples():
    """Integration test: convert the repository's example .efg files and
    require exact equality with their corresponding canonical .ef outputs.

    This combined test iterates over known example pairs so it's easy to
    extend with additional examples in the future.
    """
    examples = [
        ('games/efg/one_card_poker.efg', 'games/one_card_poker.ef'),
        ('games/efg/2smp.efg', 'games/2smp.ef'),
        ('games/efg/2s2x2x2.efg', 'games/2s2x2x2.ef'),
        ('games/efg/cent2.efg', 'games/cent2.ef'),
    ]

    for efg_path, expected_ef_path in examples:
        out = draw_tree.efg_dl_ef(efg_path)
        # Converter must return a path and write the file
        assert isinstance(out, str), "efg_dl_ef must return a file path string"
        assert os.path.exists(out), f"efg_dl_ef did not create output file: {out}"

        with open(out, 'r', encoding='utf-8') as f:
            generated = f.read().strip().splitlines()
        with open(expected_ef_path, 'r', encoding='utf-8') as f:
            expected = f.read().strip().splitlines()

        gen_norm = [line.strip() for line in generated if line.strip()]
        expected_lines = [ln.strip() for ln in expected if ln.strip()]
        assert gen_norm == expected_lines, (
            f"Generated .ef does not match expected for {efg_path}.\nGenerated:\n" + "\n".join(gen_norm)
            + "\n\nExpected:\n" + "\n".join(expected_lines)
        )


if __name__ == "__main__":
    pytest.main([__file__])