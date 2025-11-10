"""
Tests for claude/post_tool_use.py
Tests PostToolUse hook functionality and file processing
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add claude to path
sys.path.insert(0, str(Path(__file__).parent.parent / "claude"))

from post_tool_use import main, process_file


class TestProcessFile:
    """Test process_file function"""

    def test_processes_file_with_registered_formatter(self, tmp_path):
        """Should process file using registered formatter"""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"key": "value"}')

        # JSON formatter is registered
        result = process_file(test_file, tmp_path)

        # Should succeed (JSON formatter exists)
        assert result is True
        # File should be formatted
        formatted = test_file.read_text()
        assert "\n" in formatted  # Pretty-printed

    def test_skips_file_without_formatter(self, tmp_path):
        """Should skip files without registered formatter"""
        test_file = tmp_path / "test.xyz"
        test_file.write_text("unknown file type")

        result = process_file(test_file, tmp_path)

        # Should return True (skip silently)
        assert result is True

    def test_handles_formatter_exception(self, tmp_path):
        """Should handle formatter exceptions gracefully"""
        test_file = tmp_path / "test.json"
        test_file.write_text("{invalid json")

        result = process_file(test_file, tmp_path)

        # Should return False on formatter error
        assert result is False


class TestMain:
    """Test main function"""

    def test_skips_non_edit_tools(self):
        """Should skip non-edit tools"""
        hook_data = {"tool_name": "Read"}

        with patch("post_tool_use.get_hook_data", return_value=hook_data):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_with(0)

    def test_skips_when_no_file_paths(self):
        """Should skip when no file paths provided"""
        hook_data = {"tool_name": "Edit", "tool_input": {}}

        with patch("post_tool_use.get_hook_data", return_value=hook_data):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_with(0)

    def test_processes_edit_tool_with_file_paths(self, tmp_path):
        """Should process files for Edit tool"""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"test": true}')

        hook_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(test_file)},
        }

        with patch("post_tool_use.get_hook_data", return_value=hook_data):
            with patch("post_tool_use.get_project_dir", return_value=tmp_path):
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_exit.assert_called_with(0)

        # File should be formatted
        formatted = test_file.read_text()
        assert "\n" in formatted

    def test_handles_file_not_found(self, tmp_path, capsys):
        """Should handle missing files gracefully"""
        hook_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "nonexistent.py")},
        }

        with patch("post_tool_use.get_hook_data", return_value=hook_data):
            with patch("post_tool_use.get_project_dir", return_value=tmp_path):
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_exit.assert_called_with(0)

        captured = capsys.readouterr()
        assert "File not found" in captured.out

    def test_processes_multiple_files(self, tmp_path, monkeypatch):
        """Should process multiple files"""
        file1 = tmp_path / "test1.json"
        file2 = tmp_path / "test2.json"
        file1.write_text('{"a": 1}')
        file2.write_text('{"b": 2}')

        hook_data = {"tool_name": "MultiEdit", "tool_input": {}}

        # Mock get_file_paths to return multiple files
        monkeypatch.setenv("CLAUDE_FILE_PATHS", f"{file1} {file2}")

        with patch("post_tool_use.get_hook_data", return_value=hook_data):
            with patch("post_tool_use.get_project_dir", return_value=tmp_path):
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_exit.assert_called_with(0)

        # Both files should be formatted
        assert "\n" in file1.read_text()
        assert "\n" in file2.read_text()

    def test_continues_on_formatter_error(self, tmp_path, capsys):
        """Should continue processing even if formatter fails"""
        file1 = tmp_path / "test1.json"
        file2 = tmp_path / "test2.json"
        file1.write_text("{invalid")  # Will fail
        file2.write_text('{"valid": true}')  # Will succeed

        hook_data = {"tool_name": "Edit", "tool_input": {}}
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setenv("CLAUDE_FILE_PATHS", f"{file1} {file2}")

        with patch("post_tool_use.get_hook_data", return_value=hook_data):
            with patch("post_tool_use.get_project_dir", return_value=tmp_path):
                with patch("sys.exit") as mock_exit:
                    main()
                    # Always exits 0 (permissive mode)
                    mock_exit.assert_called_with(0)

        monkeypatch.undo()

        # file2 should still be processed even if file1 failed
        assert "\n" in file2.read_text()

    def test_handles_exception_gracefully(self, capsys):
        """Should handle exceptions in main gracefully"""
        # Cause an exception by making get_hook_data fail
        with patch("post_tool_use.get_hook_data", side_effect=Exception("test error")):
            with patch("sys.exit") as mock_exit:
                main()
                # Should still exit 0 (permissive mode)
                mock_exit.assert_called_with(0)

        captured = capsys.readouterr()
        assert "PostToolUse" in captured.err
        assert "test error" in captured.err

    def test_processes_write_tool(self, tmp_path):
        """Should process Write tool operations"""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"new": "file"}')

        hook_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(test_file)},
        }

        with patch("post_tool_use.get_hook_data", return_value=hook_data):
            with patch("post_tool_use.get_project_dir", return_value=tmp_path):
                with patch("sys.exit") as mock_exit:
                    main()
                    mock_exit.assert_called_with(0)

        # File should be formatted
        formatted = test_file.read_text()
        assert "\n" in formatted

    def test_prints_quality_check_messages(self, tmp_path, capsys):
        """Should print quality check start and complete messages"""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"test": true}')

        hook_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(test_file)},
        }

        with patch("post_tool_use.get_hook_data", return_value=hook_data):
            with patch("post_tool_use.get_project_dir", return_value=tmp_path):
                with patch("sys.exit"):
                    main()

        captured = capsys.readouterr()
        assert "Running quality checks" in captured.out
        assert "Quality checks complete" in captured.out
