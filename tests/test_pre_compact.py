"""Tests for pre_compact.py hook"""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module we're testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude import pre_compact


class TestHandlePreCompact:
    """Test the handle_pre_compact function"""

    def test_handle_pre_compact_accepts_empty_dict(self):
        """Test that handle_pre_compact accepts empty dictionary"""
        # Should not raise any exception
        pre_compact.handle_pre_compact({})

    def test_handle_pre_compact_accepts_hook_data(self):
        """Test that handle_pre_compact accepts hook data"""
        hook_data = {
            "context": "Some conversation context",
            "metadata": {"tokens": 50000, "messages": 100},
        }
        # Should not raise any exception
        pre_compact.handle_pre_compact(hook_data)

    def test_handle_pre_compact_does_nothing_currently(self):
        """Test that handle_pre_compact is currently a no-op"""
        # This function currently just passes
        # When implementation is added, this test should be updated
        result = pre_compact.handle_pre_compact({"test": "data"})
        assert result is None


class TestPreCompactMain:
    """Test the main pre_compact hook function"""

    @patch("claude.pre_compact.handle_pre_compact")
    @patch("claude.pre_compact.get_hook_data")
    def test_main_calls_handle_pre_compact(self, mock_get_hook_data, mock_handle):
        """Test that main() calls handle_pre_compact with hook data"""
        test_hook_data = {"context": "test"}
        mock_get_hook_data.return_value = test_hook_data

        with pytest.raises(SystemExit) as exc_info:
            pre_compact.main()

        # Verify handle_pre_compact was called with hook data
        mock_handle.assert_called_once_with(test_hook_data)

        # Verify permissive exit
        assert exc_info.value.code == 0

    @patch("claude.pre_compact.handle_pre_compact")
    @patch("claude.pre_compact.get_hook_data")
    def test_main_exits_zero_on_success(self, mock_get_hook_data, mock_handle):
        """Test that main() exits with code 0 on success"""
        mock_get_hook_data.return_value = {}

        with pytest.raises(SystemExit) as exc_info:
            pre_compact.main()

        assert exc_info.value.code == 0

    @patch(
        "claude.pre_compact.handle_pre_compact", side_effect=Exception("Handler failed")
    )
    @patch("claude.pre_compact.get_hook_data")
    def test_main_handles_handler_exception(self, mock_get_hook_data, mock_handle):
        """Test that main() handles exceptions from handle_pre_compact"""
        mock_get_hook_data.return_value = {}

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                pre_compact.main()

        # Verify error was printed
        error_output = mock_stderr.getvalue()
        assert "Hook Error: PreCompact" in error_output
        assert "Handler failed" in error_output

        # Verify permissive exit even on error
        assert exc_info.value.code == 0

    @patch("claude.pre_compact.handle_pre_compact")
    @patch(
        "claude.pre_compact.get_hook_data", side_effect=Exception("Hook data failed")
    )
    def test_main_handles_get_hook_data_exception(
        self, mock_get_hook_data, mock_handle
    ):
        """Test that main() handles exceptions from get_hook_data"""
        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                pre_compact.main()

        # Verify error was printed
        error_output = mock_stderr.getvalue()
        assert "Hook Error: PreCompact" in error_output
        assert "Hook data failed" in error_output

        # Verify permissive exit even on error
        assert exc_info.value.code == 0

    @patch("claude.pre_compact.handle_pre_compact")
    @patch("claude.pre_compact.get_hook_data")
    def test_main_with_complex_hook_data(self, mock_get_hook_data, mock_handle):
        """Test main() with complex hook data structure"""
        complex_data = {
            "conversation": {
                "messages": [{"role": "user", "content": "test"}],
                "context_tokens": 45000,
            },
            "metadata": {"timestamp": "2024-01-01T00:00:00Z"},
        }
        mock_get_hook_data.return_value = complex_data

        with pytest.raises(SystemExit) as exc_info:
            pre_compact.main()

        # Verify complex data was passed through
        mock_handle.assert_called_once_with(complex_data)
        assert exc_info.value.code == 0


class TestPreCompactIntegration:
    """Integration tests for pre_compact hook"""

    @patch("claude.pre_compact.get_hook_data")
    def test_full_pre_compact_flow(self, mock_get_hook_data):
        """Test complete pre_compact flow"""
        hook_data = {"context": "Large context to be compacted", "tokens": 100000}
        mock_get_hook_data.return_value = hook_data

        with pytest.raises(SystemExit) as exc_info:
            pre_compact.main()

        # Verify successful completion
        assert exc_info.value.code == 0
