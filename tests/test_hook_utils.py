#!/usr/bin/env python3
"""
Tests for hook utility functions

Run with: python3 -m pytest tests/test_hook_utils.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHookDataExtraction:
    """Test suite for hook data extraction functions"""

    def test_get_tool_name(self):
        """Test tool name extraction"""
        from shared.hook_utils import get_tool_name

        hook_data = {"tool_name": "Bash"}
        assert get_tool_name(hook_data) == "Bash"

        hook_data = {"tool_name": "Edit"}
        assert get_tool_name(hook_data) == "Edit"

        # Missing tool_name returns empty string
        assert get_tool_name({}) == ""

    def test_get_tool_input(self):
        """Test tool input extraction"""
        from shared.hook_utils import get_tool_input

        hook_data = {"tool_input": {"command": "git status"}}
        assert get_tool_input(hook_data) == {"command": "git status"}

        hook_data = {"tool_input": {"file_path": "/path/to/file"}}
        assert get_tool_input(hook_data) == {"file_path": "/path/to/file"}

        # Missing tool_input returns empty dict
        assert get_tool_input({}) == {}

    def test_get_bash_command(self):
        """Test bash command extraction"""
        from shared.hook_utils import get_bash_command

        hook_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git status"}
        }
        assert get_bash_command(hook_data) == "git status"

        # Non-Bash tool returns empty string
        hook_data = {
            "tool_name": "Edit",
            "tool_input": {"command": "ignored"}
        }
        assert get_bash_command(hook_data) == ""

        # Missing command returns empty string
        hook_data = {
            "tool_name": "Bash",
            "tool_input": {}
        }
        assert get_bash_command(hook_data) == ""


class TestErrorFormatting:
    """Test suite for error formatting functions"""

    def test_format_hook_error_basic(self):
        """Test basic error formatting"""
        from shared.hook_utils import format_hook_error

        error = ValueError("test error message")
        result = format_hook_error("TestComponent", error, "doing test operation")

        assert "🚨 TestComponent Hook Error: ValueError" in result
        assert "Problem: test error message" in result
        assert "Context: doing test operation" in result
        assert "Stack trace:" in result

    def test_format_hook_error_import_error(self):
        """Test ImportError formatting with fix suggestion"""
        from shared.hook_utils import format_hook_error

        try:
            import nonexistent_module  # noqa: F401
        except (ImportError, ModuleNotFoundError) as e:
            result = format_hook_error("TestComponent", e)
            assert "ModuleNotFoundError" in result or "ImportError" in result
            assert "Fix: Add 'import" in result

    def test_format_hook_error_key_error(self):
        """Test KeyError formatting with fix suggestion"""
        from shared.hook_utils import format_hook_error

        try:
            data = {"key1": "value1"}
            _ = data["missing_key"]
        except KeyError as e:
            result = format_hook_error("TestComponent", e)
            assert "KeyError" in result
            assert "Fix: Missing key" in result

    def test_format_hook_error_file_not_found(self):
        """Test FileNotFoundError formatting with fix suggestion"""
        from shared.hook_utils import format_hook_error

        try:
            with open("/nonexistent/path/file.txt"):
                pass
        except FileNotFoundError as e:
            result = format_hook_error("TestComponent", e)
            assert "FileNotFoundError" in result
            assert "Fix: Check path exists:" in result
            assert "/nonexistent/path/file.txt" in result

    def test_format_hook_error_subprocess_error(self):
        """Test subprocess.CalledProcessError formatting"""
        from shared.hook_utils import format_hook_error

        error = subprocess.CalledProcessError(1, ["git", "nonexistent-command"])
        result = format_hook_error("TestComponent", error)

        assert "CalledProcessError" in result
        assert "Fix: Command failed with exit code 1" in result
        assert "Command:" in result

    def test_format_hook_error_without_context(self):
        """Test error formatting without context"""
        from shared.hook_utils import format_hook_error

        error = RuntimeError("runtime error")
        result = format_hook_error("TestComponent", error)

        assert "🚨 TestComponent Hook Error: RuntimeError" in result
        assert "Problem: runtime error" in result
        assert "Context:" not in result  # Context not included when empty
        assert "Fix: Review stack trace below" in result


class TestMessageEmission:
    """Test suite for message emission functions"""

    def test_emit_warning(self, capsys):
        """Test warning message emission"""
        from shared.hook_utils import emit_warning

        emit_warning("This is a warning")
        captured = capsys.readouterr()
        assert "⚠️  This is a warning" in captured.err

    def test_emit_error(self, capsys):
        """Test error message emission"""
        from shared.hook_utils import emit_error

        emit_error("This is an error")
        captured = capsys.readouterr()
        assert "🚨 This is an error" in captured.err

    def test_emit_success(self, capsys):
        """Test success message emission"""
        from shared.hook_utils import emit_success

        emit_success("This is a success")
        captured = capsys.readouterr()
        assert "✅ This is a success" in captured.err

    def test_emit_info(self, capsys):
        """Test info message emission"""
        from shared.hook_utils import emit_info

        emit_info("This is info")
        captured = capsys.readouterr()
        assert "💡 This is info" in captured.err


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
