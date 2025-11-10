"""Tests for session_start.py hook"""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module we're testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude import session_start


class TestSessionStartMain:
    """Test the main session_start hook function"""

    @patch("claude.session_start.report_session_context")
    @patch("claude.session_start.create_session_branch")
    @patch("claude.session_start.should_auto_create_branch", return_value=True)
    @patch("claude.session_start.handle_uncommitted_changes")
    @patch("claude.session_start.cleanup_empty_branches")
    @patch("claude.session_start.is_git_repo_root", return_value=True)
    @patch("claude.session_start.get_hook_data")
    def test_main_full_workflow_in_git_repo(
        self,
        mock_get_hook_data,
        mock_is_git,
        mock_cleanup,
        mock_handle_uncommitted,
        mock_should_auto_create,
        mock_create_branch,
        mock_report,
    ):
        """Test main() executes full workflow in git repository"""
        mock_get_hook_data.return_value = {"cwd": "/test/project"}

        with pytest.raises(SystemExit) as exc_info:
            session_start.main()

        # Verify workflow steps executed in order
        mock_cleanup.assert_called_once_with("/test/project")
        mock_handle_uncommitted.assert_called_once_with("/test/project")
        mock_should_auto_create.assert_called_once_with("/test/project")
        mock_create_branch.assert_called_once_with("/test/project")
        mock_report.assert_called_once_with("/test/project")

        # Verify permissive exit
        assert exc_info.value.code == 0

    @patch("claude.session_start.is_git_repo_root", return_value=False)
    @patch("claude.session_start.get_hook_data")
    def test_main_exits_early_when_not_git_repo(self, mock_get_hook_data, mock_is_git):
        """Test main() exits early when not in git repository"""
        mock_get_hook_data.return_value = {"cwd": "/not/a/repo"}

        with pytest.raises(SystemExit) as exc_info:
            session_start.main()

        # Verify early exit
        assert exc_info.value.code == 0

    @patch("claude.session_start.report_session_context")
    @patch("claude.session_start.should_auto_create_branch", return_value=False)
    @patch("claude.session_start.handle_uncommitted_changes")
    @patch("claude.session_start.cleanup_empty_branches")
    @patch("claude.session_start.is_git_repo_root", return_value=True)
    @patch("claude.session_start.get_hook_data")
    def test_main_skips_branch_creation_when_not_appropriate(
        self,
        mock_get_hook_data,
        mock_is_git,
        mock_cleanup,
        mock_handle_uncommitted,
        mock_should_auto_create,
        mock_report,
    ):
        """Test main() skips branch creation when should_auto_create returns False"""
        mock_get_hook_data.return_value = {"cwd": "/test/project"}

        with pytest.raises(SystemExit) as exc_info:
            session_start.main()

        # Verify branch creation was NOT called
        # (create_session_branch should not be in mocked functions)
        mock_should_auto_create.assert_called_once()
        assert exc_info.value.code == 0

    @patch("claude.session_start.is_git_repo_root", return_value=True)
    @patch("claude.session_start.get_hook_data")
    def test_main_uses_current_dir_when_no_cwd_in_hook_data(
        self, mock_get_hook_data, mock_is_git
    ):
        """Test main() falls back to current directory"""
        mock_get_hook_data.return_value = {}

        with patch("claude.session_start.os.getcwd", return_value="/current/dir"):
            with pytest.raises(SystemExit) as exc_info:
                session_start.main()

        # Verify is_git_repo_root was called with current dir
        mock_is_git.assert_called_once_with("/current/dir")
        assert exc_info.value.code == 0

    @patch(
        "claude.session_start.is_git_repo_root",
        side_effect=Exception("Git check failed"),
    )
    @patch("claude.session_start.get_hook_data")
    def test_main_handles_exception_gracefully(self, mock_get_hook_data, mock_is_git):
        """Test main() handles exceptions and never blocks session start"""
        mock_get_hook_data.return_value = {"cwd": "/test"}

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                session_start.main()

        # Verify error was printed
        error_output = mock_stderr.getvalue()
        assert "SessionStart Hook Error" in error_output
        assert "Git check failed" in error_output

        # Verify permissive exit even on error
        assert exc_info.value.code == 0

    @patch(
        "claude.session_start.cleanup_empty_branches",
        side_effect=Exception("Cleanup failed"),
    )
    @patch("claude.session_start.is_git_repo_root", return_value=True)
    @patch("claude.session_start.get_hook_data")
    def test_main_handles_cleanup_exception(
        self, mock_get_hook_data, mock_is_git, mock_cleanup
    ):
        """Test main() handles cleanup exceptions gracefully"""
        mock_get_hook_data.return_value = {"cwd": "/test"}

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                session_start.main()

        error_output = mock_stderr.getvalue()
        assert "SessionStart Hook Error" in error_output

        # Verify permissive exit
        assert exc_info.value.code == 0


class TestSessionStartIntegration:
    """Integration tests for session_start hook"""

    @patch("claude.session_start.report_session_context")
    @patch("claude.session_start.create_session_branch")
    @patch("claude.session_start.handle_uncommitted_changes")
    @patch("claude.session_start.cleanup_empty_branches")
    @patch("claude.session_start.is_git_repo_root", return_value=True)
    @patch("claude.session_start.should_auto_create_branch", return_value=True)
    @patch("claude.session_start.get_hook_data")
    def test_full_session_start_flow(
        self,
        mock_get_hook_data,
        mock_should_auto_create,
        mock_is_git,
        mock_cleanup,
        mock_handle_uncommitted,
        mock_create_branch,
        mock_report,
    ):
        """Test complete session_start flow"""
        mock_get_hook_data.return_value = {"cwd": "/test/project"}

        with pytest.raises(SystemExit) as exc_info:
            session_start.main()

        # Verify all workflow steps were executed
        assert mock_cleanup.called
        assert mock_handle_uncommitted.called
        assert mock_create_branch.called
        assert mock_report.called

        # Verify successful completion
        assert exc_info.value.code == 0

    def test_session_start_never_blocks(self):
        """Test that session_start NEVER blocks session initialization"""
        # This is critical behavior - session start must always succeed

        # Test with exception in get_hook_data
        with patch(
            "claude.session_start.get_hook_data",
            side_effect=Exception("Hook data error"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                session_start.main()
            assert exc_info.value.code == 0

        # Test with exception in is_git_repo_root
        with patch("claude.session_start.get_hook_data", return_value={}):
            with patch(
                "claude.session_start.is_git_repo_root",
                side_effect=RuntimeError("Git error"),
            ):
                with pytest.raises(SystemExit) as exc_info:
                    session_start.main()
                assert exc_info.value.code == 0
