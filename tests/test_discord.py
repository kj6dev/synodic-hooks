"""Tests for shared/discord.py"""

import json
import sys
import urllib.error
import urllib.request
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch


# Import the module we're testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.discord import get_webhook_url, send_notification


class TestGetWebhookUrl:
    """Test the get_webhook_url function"""

    def test_returns_url_from_environment_variable(self):
        """Test that get_webhook_url returns URL from environment"""
        test_url = "https://discord.com/api/webhooks/123/abc"
        with patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": test_url}):
            result = get_webhook_url()
            assert result == test_url

    def test_returns_url_from_env_file(self, tmp_path):
        """Test that get_webhook_url reads from .env file"""
        # Create a temporary .env file
        env_content = "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/456/def\n"
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Patch Path to return our temp directory
        with patch.dict("os.environ", {}, clear=True):
            with patch("shared.discord.Path") as mock_path:
                mock_path.return_value.parent.parent = tmp_path
                result = get_webhook_url()
                assert result == "https://discord.com/api/webhooks/456/def"

    def test_ignores_comments_in_env_file(self, tmp_path):
        """Test that get_webhook_url ignores comment lines"""
        env_content = """# This is a comment
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/789/ghi
# Another comment
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        with patch.dict("os.environ", {}, clear=True):
            with patch("shared.discord.Path") as mock_path:
                mock_path.return_value.parent.parent = tmp_path
                result = get_webhook_url()
                assert result == "https://discord.com/api/webhooks/789/ghi"

    def test_returns_none_when_no_webhook_configured(self):
        """Test that get_webhook_url returns None when not configured"""
        with patch.dict("os.environ", {}, clear=True):
            with patch("shared.discord.Path") as mock_path:
                mock_path.return_value.parent.parent = Path("/nonexistent")
                result = get_webhook_url()
                assert result is None

    def test_handles_env_file_read_exception(self):
        """Test that get_webhook_url handles file read exceptions gracefully"""
        with patch.dict("os.environ", {}, clear=True):
            # Mock Path to return a non-existent directory
            with patch("builtins.open", side_effect=Exception("Read error")):
                with patch("shared.discord.Path") as mock_path:
                    env_file = MagicMock()
                    env_file.exists.return_value = True
                    mock_path.return_value.parent.parent.__truediv__.return_value = (
                        env_file
                    )
                    # This will cause an exception when trying to read
                    result = get_webhook_url()
                    # Should return None instead of raising
                    assert result is None

    def test_environment_variable_takes_precedence(self, tmp_path):
        """Test that environment variable takes precedence over .env file"""
        env_url = "https://discord.com/api/webhooks/env/url"
        file_url = "https://discord.com/api/webhooks/file/url"

        env_content = f"DISCORD_WEBHOOK_URL={file_url}\n"
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        with patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": env_url}):
            result = get_webhook_url()
            assert result == env_url


class TestSendNotification:
    """Test the send_notification function"""

    @patch("urllib.request.urlopen")
    def test_sends_notification_successfully(self, mock_urlopen):
        """Test that send_notification sends Discord webhook successfully"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        webhook_url = "https://discord.com/api/webhooks/123/abc"
        result = send_notification("🔔", "test-project", webhook_url=webhook_url)

        assert result is True
        assert mock_urlopen.called

    @patch("urllib.request.urlopen")
    def test_builds_correct_payload(self, mock_urlopen):
        """Test that send_notification builds correct Discord payload"""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        webhook_url = "https://discord.com/api/webhooks/123/abc"
        send_notification("🛑", "my-repo", webhook_url=webhook_url)

        # Verify request was made with correct data
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data)

        assert payload["content"] == "🛑 `my-repo`"

    def test_returns_false_when_no_webhook_configured(self):
        """Test that send_notification returns False when no webhook configured"""
        with patch("shared.discord.get_webhook_url", return_value=None):
            result = send_notification("🔔", "test-project")
            assert result is False

    @patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError("url", 404, "Not Found", {}, None),
    )
    def test_handles_http_error(self, mock_urlopen):
        """Test that send_notification handles HTTP errors gracefully"""
        webhook_url = "https://discord.com/api/webhooks/invalid/url"

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            result = send_notification("🔔", "test-project", webhook_url=webhook_url)

        assert result is False
        error_output = mock_stderr.getvalue()
        assert "Discord webhook HTTP error" in error_output

    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network error"))
    def test_handles_url_error(self, mock_urlopen):
        """Test that send_notification handles URL errors gracefully"""
        webhook_url = "https://discord.com/api/webhooks/123/abc"

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            result = send_notification("🔔", "test-project", webhook_url=webhook_url)

        assert result is False
        error_output = mock_stderr.getvalue()
        assert "Discord webhook URL error" in error_output

    @patch("urllib.request.urlopen", side_effect=Exception("Unexpected error"))
    def test_handles_general_exception(self, mock_urlopen):
        """Test that send_notification handles general exceptions gracefully"""
        webhook_url = "https://discord.com/api/webhooks/123/abc"

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            result = send_notification("🔔", "test-project", webhook_url=webhook_url)

        assert result is False
        error_output = mock_stderr.getvalue()
        assert "Discord notification failed" in error_output

    @patch("urllib.request.urlopen")
    def test_uses_correct_headers(self, mock_urlopen):
        """Test that send_notification uses correct HTTP headers"""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        webhook_url = "https://discord.com/api/webhooks/123/abc"
        send_notification("🔔", "test-project", webhook_url=webhook_url)

        # Verify headers
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        assert request.headers["Content-type"] == "application/json"
        assert request.headers["User-agent"] == "Claude-Code-Hooks/1.0"

    @patch(
        "shared.discord.get_webhook_url",
        return_value="https://discord.com/api/webhooks/auto/detected",
    )
    @patch("urllib.request.urlopen")
    def test_auto_detects_webhook_url(self, mock_urlopen, mock_get_webhook):
        """Test that send_notification auto-detects webhook URL"""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        # Call without explicit webhook_url
        result = send_notification("🔔", "test-project")

        assert result is True
        mock_get_webhook.assert_called_once()


class TestDiscordIntegration:
    """Integration tests for Discord module"""

    @patch("urllib.request.urlopen")
    def test_full_notification_flow(self, mock_urlopen):
        """Test complete flow from webhook detection to notification send"""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        webhook_url = "https://discord.com/api/webhooks/123/abc"

        with patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": webhook_url}):
            # Get webhook URL
            url = get_webhook_url()
            assert url == webhook_url

            # Send notification
            result = send_notification("🛑", "synodic-hooks", webhook_url=url)
            assert result is True

    def test_graceful_degradation_without_webhook(self):
        """Test that system works gracefully without webhook configured"""
        with patch.dict("os.environ", {}, clear=True):
            with patch("shared.discord.Path") as mock_path:
                mock_path.return_value.parent.parent = Path("/nonexistent")

                # Get webhook URL (returns None)
                url = get_webhook_url()
                assert url is None

                # Send notification (returns False silently)
                result = send_notification("🔔", "test-project")
                assert result is False
