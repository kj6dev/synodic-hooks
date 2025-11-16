"""Tests for user_prompt_submit.py hook"""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module we're testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude import user_prompt_submit


class TestProcessPrompt:
    """Test the process_prompt function"""

    def test_process_prompt_accepts_empty_dict(self):
        """Test that process_prompt accepts empty dictionary"""
        # Should not raise any exception
        user_prompt_submit.process_prompt({})

    def test_process_prompt_accepts_hook_data_with_user_message(self):
        """Test that process_prompt accepts hook data with user_message"""
        hook_data = {"user_message": "Hello, Claude!"}
        # Should not raise any exception
        user_prompt_submit.process_prompt(hook_data)

    def test_process_prompt_accepts_hook_data_without_user_message(self):
        """Test that process_prompt handles missing user_message"""
        hook_data = {"other_field": "value"}
        # Should not raise any exception
        user_prompt_submit.process_prompt(hook_data)

    def test_process_prompt_does_nothing_currently(self):
        """Test that process_prompt is currently a no-op"""
        # This function currently just passes
        result = user_prompt_submit.process_prompt({"user_message": "test"})
        assert result is None


class TestUserPromptSubmitMain:
    """Test the main user_prompt_submit hook function"""

    @patch("claude.user_prompt_submit.process_prompt")
    @patch("claude.user_prompt_submit.get_hook_data")
    def test_main_calls_processor_with_hook_data(
        self, mock_get_hook_data, mock_processor
    ):
        """Test that main() calls process_prompt with hook data"""
        test_hook_data = {"user_message": "Test prompt"}
        mock_get_hook_data.return_value = test_hook_data

        with pytest.raises(SystemExit) as exc_info:
            user_prompt_submit.main()

        # Verify processor was called with hook data
        mock_processor.assert_called_once_with(test_hook_data)
        assert exc_info.value.code == 0

    @patch("claude.user_prompt_submit.process_prompt")
    @patch("claude.user_prompt_submit.get_hook_data")
    def test_main_exits_zero_on_success(self, mock_get_hook_data, mock_processor):
        """Test that main() exits with code 0 on success"""
        mock_get_hook_data.return_value = {}

        with pytest.raises(SystemExit) as exc_info:
            user_prompt_submit.main()

        assert exc_info.value.code == 0

    @patch(
        "claude.user_prompt_submit.process_prompt",
        side_effect=Exception("Processor failed"),
    )
    @patch("claude.user_prompt_submit.get_hook_data")
    def test_main_handles_processor_exception(self, mock_get_hook_data, mock_processor):
        """Test that main() handles exceptions from process_prompt"""
        mock_get_hook_data.return_value = {}

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                user_prompt_submit.main()

        # Verify error was printed
        error_output = mock_stderr.getvalue()
        assert "Hook Error: UserPromptSubmit" in error_output
        assert "Processor failed" in error_output
        assert exc_info.value.code == 0

    @patch("claude.user_prompt_submit.process_prompt")
    @patch(
        "claude.user_prompt_submit.get_hook_data",
        side_effect=Exception("Hook data failed"),
    )
    def test_main_handles_get_hook_data_exception(
        self, mock_get_hook_data, mock_processor
    ):
        """Test that main() handles exceptions from get_hook_data"""
        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                user_prompt_submit.main()

        # Verify error was printed
        error_output = mock_stderr.getvalue()
        assert "Hook Error: UserPromptSubmit" in error_output
        assert "Hook data failed" in error_output
        assert exc_info.value.code == 0


class TestUserPromptSubmitIntegration:
    """Integration tests for user_prompt_submit hook"""

    @patch("claude.user_prompt_submit.get_hook_data")
    def test_full_user_prompt_submit_flow(self, mock_get_hook_data):
        """Test complete user_prompt_submit flow"""
        hook_data = {
            "user_message": "Please analyze this code",
            "timestamp": "2024-01-01",
        }
        mock_get_hook_data.return_value = hook_data

        with pytest.raises(SystemExit) as exc_info:
            user_prompt_submit.main()

        # Verify successful completion
        assert exc_info.value.code == 0

    @patch("claude.user_prompt_submit.get_hook_data")
    def test_user_prompt_submit_with_empty_message(self, mock_get_hook_data):
        """Test with empty user message"""
        hook_data = {"user_message": ""}
        mock_get_hook_data.return_value = hook_data

        with pytest.raises(SystemExit) as exc_info:
            user_prompt_submit.main()

        assert exc_info.value.code == 0

    @patch("claude.user_prompt_submit.get_hook_data")
    def test_user_prompt_submit_with_long_message(self, mock_get_hook_data):
        """Test with very long user message"""
        long_message = "Please help me with this task. " * 100
        hook_data = {"user_message": long_message}
        mock_get_hook_data.return_value = hook_data

        with pytest.raises(SystemExit) as exc_info:
            user_prompt_submit.main()

        assert exc_info.value.code == 0
