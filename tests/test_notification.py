"""Tests for notification.py hook"""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the module we're testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude import notification


class TestNotificationMain:
    """Test the main notification hook function"""

    @patch("claude.notification.send_notification")
    @patch("claude.notification.play_sound")
    @patch("claude.notification.get_hook_data")
    def test_main_plays_sound_and_sends_notification(
        self, mock_get_hook_data, mock_play_sound, mock_send_notification
    ):
        """Test that main() plays sound and sends notification"""
        mock_get_hook_data.return_value = {}

        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": "/test/project"}):
            with pytest.raises(SystemExit) as exc_info:
                notification.main()

        # Verify sound was played
        mock_play_sound.assert_called_once_with(notification.SOUND_SOSUMI)

        # Verify notification was sent
        mock_send_notification.assert_called_once_with(message="🔔", project="project")

        # Verify permissive exit
        assert exc_info.value.code == 0

    @patch("claude.notification.send_notification")
    @patch("claude.notification.play_sound")
    @patch("claude.notification.get_hook_data")
    def test_main_uses_current_directory_when_no_project_dir(
        self, mock_get_hook_data, mock_play_sound, mock_send_notification
    ):
        """Test that main() falls back to current directory"""
        mock_get_hook_data.return_value = {}

        with patch.dict("os.environ", {}, clear=True):
            with patch("claude.notification.os.getcwd", return_value="/current/dir"):
                with pytest.raises(SystemExit) as exc_info:
                    notification.main()

        # Verify notification used current directory name
        mock_send_notification.assert_called_once_with(message="🔔", project="dir")

        # Verify permissive exit
        assert exc_info.value.code == 0

    @patch("claude.notification.send_notification")
    @patch("claude.notification.play_sound", side_effect=Exception("Sound failed"))
    @patch("claude.notification.get_hook_data")
    def test_main_handles_sound_exception(
        self, mock_get_hook_data, mock_play_sound, mock_send_notification
    ):
        """Test that main() handles exceptions gracefully"""
        mock_get_hook_data.return_value = {}

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                notification.main()

        # Verify error was printed
        error_output = mock_stderr.getvalue()
        assert "Hook Error: Notification" in error_output
        assert "Sound failed" in error_output

        # Verify permissive exit even on error
        assert exc_info.value.code == 0

    @patch(
        "claude.notification.send_notification", side_effect=Exception("Discord failed")
    )
    @patch("claude.notification.play_sound")
    @patch("claude.notification.get_hook_data")
    def test_main_handles_notification_exception(
        self, mock_get_hook_data, mock_play_sound, mock_send_notification
    ):
        """Test that main() handles notification exceptions gracefully"""
        mock_get_hook_data.return_value = {}

        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": "/test/project"}):
            with patch("sys.stderr", new=StringIO()) as mock_stderr:
                with pytest.raises(SystemExit) as exc_info:
                    notification.main()

        # Verify error was printed
        error_output = mock_stderr.getvalue()
        assert "Hook Error: Notification" in error_output
        assert "Discord failed" in error_output

        # Verify permissive exit even on error
        assert exc_info.value.code == 0

    @patch("claude.notification.send_notification")
    @patch("claude.notification.play_sound")
    @patch(
        "claude.notification.get_hook_data", side_effect=Exception("Hook data failed")
    )
    def test_main_handles_get_hook_data_exception(
        self, mock_get_hook_data, mock_play_sound, mock_send_notification
    ):
        """Test that main() handles get_hook_data exceptions gracefully"""
        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                notification.main()

        # Verify error was printed
        error_output = mock_stderr.getvalue()
        assert "Hook Error: Notification" in error_output
        assert "Hook data failed" in error_output

        # Verify permissive exit even on error
        assert exc_info.value.code == 0


class TestNotificationIntegration:
    """Integration tests for notification hook"""

    @patch("claude.notification.send_notification")
    @patch("subprocess.run")
    @patch("claude.notification.get_hook_data")
    def test_full_notification_flow(
        self, mock_get_hook_data, mock_subprocess, mock_send_notification
    ):
        """Test complete notification flow from hook data to sound/notification"""
        mock_get_hook_data.return_value = {"notification_type": "info"}
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": "/test/synodic-hooks"}):
            with pytest.raises(SystemExit) as exc_info:
                notification.main()

        # Verify subprocess was called to play sound
        mock_subprocess.assert_called_once()
        assert "afplay" in str(mock_subprocess.call_args)

        # Verify notification was sent
        mock_send_notification.assert_called_once_with(
            message="🔔", project="synodic-hooks"
        )

        # Verify successful exit
        assert exc_info.value.code == 0
