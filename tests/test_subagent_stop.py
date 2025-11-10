"""Tests for subagent_stop.py hook"""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module we're testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude import subagent_stop


class TestHandleSubagentCompletion:
    """Test the handle_subagent_completion function"""

    def test_handle_subagent_completion_accepts_empty_dict(self):
        """Test that handle_subagent_completion accepts empty dictionary"""
        # Should not raise any exception
        subagent_stop.handle_subagent_completion({})

    def test_handle_subagent_completion_accepts_hook_data(self):
        """Test that handle_subagent_completion accepts hook data"""
        hook_data = {
            "subagent_id": "subagent-123",
            "subagent_type": "task",
            "execution_time": 5.2,
        }
        # Should not raise any exception
        subagent_stop.handle_subagent_completion(hook_data)

    def test_handle_subagent_completion_does_nothing_currently(self):
        """Test that handle_subagent_completion is currently a no-op"""
        # This function currently just passes
        result = subagent_stop.handle_subagent_completion({"test": "data"})
        assert result is None


class TestSubagentStopMain:
    """Test the main subagent_stop hook function"""

    @patch("claude.subagent_stop.handle_subagent_completion")
    @patch("claude.subagent_stop.get_hook_data")
    def test_main_calls_handler_with_hook_data(self, mock_get_hook_data, mock_handler):
        """Test that main() calls handle_subagent_completion with hook data"""
        test_hook_data = {"subagent_id": "123"}
        mock_get_hook_data.return_value = test_hook_data

        with pytest.raises(SystemExit) as exc_info:
            subagent_stop.main()

        # Verify handler was called with hook data
        mock_handler.assert_called_once_with(test_hook_data)
        assert exc_info.value.code == 0

    @patch("claude.subagent_stop.handle_subagent_completion")
    @patch("claude.subagent_stop.get_hook_data")
    def test_main_exits_zero_on_success(self, mock_get_hook_data, mock_handler):
        """Test that main() exits with code 0 on success"""
        mock_get_hook_data.return_value = {}

        with pytest.raises(SystemExit) as exc_info:
            subagent_stop.main()

        assert exc_info.value.code == 0

    @patch(
        "claude.subagent_stop.handle_subagent_completion",
        side_effect=Exception("Handler failed"),
    )
    @patch("claude.subagent_stop.get_hook_data")
    def test_main_handles_handler_exception(self, mock_get_hook_data, mock_handler):
        """Test that main() handles exceptions from handle_subagent_completion"""
        mock_get_hook_data.return_value = {}

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                subagent_stop.main()

        # Verify error was printed
        error_output = mock_stderr.getvalue()
        assert "Hook Error: SubagentStop" in error_output
        assert "Handler failed" in error_output
        assert exc_info.value.code == 0

    @patch("claude.subagent_stop.handle_subagent_completion")
    @patch(
        "claude.subagent_stop.get_hook_data", side_effect=Exception("Hook data failed")
    )
    def test_main_handles_get_hook_data_exception(
        self, mock_get_hook_data, mock_handler
    ):
        """Test that main() handles exceptions from get_hook_data"""
        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                subagent_stop.main()

        # Verify error was printed
        error_output = mock_stderr.getvalue()
        assert "Hook Error: SubagentStop" in error_output
        assert "Hook data failed" in error_output
        assert exc_info.value.code == 0


class TestSubagentStopIntegration:
    """Integration tests for subagent_stop hook"""

    @patch("claude.subagent_stop.get_hook_data")
    def test_full_subagent_stop_flow(self, mock_get_hook_data):
        """Test complete subagent_stop flow"""
        hook_data = {
            "subagent_id": "agent-001",
            "subagent_type": "explorer",
            "execution_time": 3.5,
            "success": True,
        }
        mock_get_hook_data.return_value = hook_data

        with pytest.raises(SystemExit) as exc_info:
            subagent_stop.main()

        # Verify successful completion
        assert exc_info.value.code == 0

    @patch("claude.subagent_stop.get_hook_data")
    def test_subagent_stop_with_complex_data(self, mock_get_hook_data):
        """Test with complex subagent metadata"""
        complex_data = {
            "subagent_id": "agent-999",
            "metadata": {
                "files_processed": 42,
                "errors": [],
                "warnings": ["minor issue"],
            },
        }
        mock_get_hook_data.return_value = complex_data

        with pytest.raises(SystemExit) as exc_info:
            subagent_stop.main()

        assert exc_info.value.code == 0
