"""Tests for session_end.py hook"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module we're testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude import session_end


class TestFinalizeSession:
    """Test the finalize_session function"""

    def test_finalize_session_accepts_project_dir(self):
        """Test that finalize_session accepts project directory"""
        # Should not raise any exception
        session_end.finalize_session("/test/project")

    def test_finalize_session_with_real_path(self, tmp_path):
        """Test that finalize_session works with real path"""
        # Should not raise any exception
        session_end.finalize_session(str(tmp_path))

    def test_finalize_session_does_nothing_currently(self):
        """Test that finalize_session is currently a no-op"""
        # This function currently just passes
        # When implementation is added, this test should be updated
        result = session_end.finalize_session("/any/path")
        assert result is None


class TestSessionEndMain:
    """Test the main session_end hook function"""

    @patch("claude.session_end.finalize_session")
    def test_main_calls_finalize_with_project_dir(self, mock_finalize):
        """Test that main() calls finalize_session with project directory"""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": "/test/project"}):
            with pytest.raises(SystemExit) as exc_info:
                session_end.main()

        # Verify finalize_session was called with project dir
        mock_finalize.assert_called_once_with("/test/project")

        # Verify permissive exit
        assert exc_info.value.code == 0

    @patch("claude.session_end.finalize_session")
    def test_main_uses_current_dir_when_no_project_dir(self, mock_finalize):
        """Test that main() falls back to current directory"""
        with patch.dict("os.environ", {}, clear=True):
            with patch("claude.session_end.os.getcwd", return_value="/current/dir"):
                with pytest.raises(SystemExit) as exc_info:
                    session_end.main()

        # Verify finalize_session was called with current dir
        mock_finalize.assert_called_once_with("/current/dir")
        assert exc_info.value.code == 0

    @patch(
        "claude.session_end.finalize_session", side_effect=Exception("Finalize failed")
    )
    def test_main_handles_finalize_exception_silently(self, mock_finalize):
        """Test that main() handles exceptions silently (never blocks session end)"""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": "/test"}):
            with pytest.raises(SystemExit) as exc_info:
                session_end.main()

        # Verify permissive exit even on error (CRITICAL: never block session end)
        assert exc_info.value.code == 0

    @patch("claude.session_end.finalize_session")
    def test_main_handles_environment_exception_silently(self, mock_finalize):
        """Test that main() handles environment errors silently"""

        def raise_exception(*args, **kwargs):
            raise Exception("Environment error")

        with patch("os.environ.get", side_effect=raise_exception):
            with pytest.raises(SystemExit) as exc_info:
                session_end.main()

        # Verify permissive exit even on error
        assert exc_info.value.code == 0

    @patch("claude.session_end.finalize_session")
    def test_main_exits_zero_on_success(self, mock_finalize):
        """Test that main() always exits with code 0"""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": "/test"}):
            with pytest.raises(SystemExit) as exc_info:
                session_end.main()

        assert exc_info.value.code == 0


class TestSessionEndIntegration:
    """Integration tests for session_end hook"""

    def test_full_session_end_flow(self, tmp_path):
        """Test complete session_end flow"""
        project_path = str(tmp_path / "test-project")
        Path(project_path).mkdir(exist_ok=True)

        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": project_path}):
            with pytest.raises(SystemExit) as exc_info:
                session_end.main()

        # Verify successful completion
        assert exc_info.value.code == 0

    def test_session_end_never_fails(self, tmp_path):
        """Test that session_end NEVER blocks session termination"""
        # This is critical behavior - session end must always succeed

        # Test with invalid project dir
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": "/nonexistent/path"}):
            with pytest.raises(SystemExit) as exc_info:
                session_end.main()
            assert exc_info.value.code == 0

        # Test with finalize_session raising
        with patch(
            "claude.session_end.finalize_session",
            side_effect=RuntimeError("Critical error"),
        ):
            with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(tmp_path)}):
                with pytest.raises(SystemExit) as exc_info:
                    session_end.main()
                assert exc_info.value.code == 0
