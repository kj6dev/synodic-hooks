#!/usr/bin/env python3
"""
Tests for session management modules

Run with: python3 -m pytest tests/test_session_management.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def test_repo():
    """Create a temporary git repository for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path, check=True, capture_output=True
        )

        # Create initial commit
        test_file = repo_path / "README.md"
        test_file.write_text("# Test Repo\n")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path, check=True, capture_output=True
        )

        # Get current branch name
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path, capture_output=True, text=True
        )
        current_branch = result.stdout.strip()

        # Ensure we have a develop branch
        if current_branch != "develop":
            subprocess.run(
                ["git", "branch", "develop"],
                cwd=repo_path, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "checkout", "develop"],
                cwd=repo_path, check=True, capture_output=True
            )

        yield repo_path


class TestBranchManagement:
    """Test suite for branch management module"""

    def test_should_auto_create_branch_at_repo_root(self, test_repo):
        """Test that auto-branch is enabled at repo root"""
        from claude.session.branch_management import should_auto_create_branch

        # Should create at repo root
        assert should_auto_create_branch(str(test_repo))

    def test_should_not_auto_create_at_home(self):
        """Test that auto-branch is disabled at home directories"""
        from claude.session.branch_management import should_auto_create_branch

        # Should NOT create at home
        assert not should_auto_create_branch(str(Path.home()))
        assert not should_auto_create_branch(str(Path.home() / "Developer"))
        assert not should_auto_create_branch(str(Path.home() / "Downloads"))

    def test_should_not_auto_create_if_already_on_claude_branch(self, test_repo):
        """Test that auto-branch is disabled if already on claude/* branch"""
        from claude.session.branch_management import should_auto_create_branch
        from shared.git import create_branch

        # Create and checkout a claude branch
        create_branch("claude/test", repo_path=str(test_repo))

        # Should NOT create another one
        assert not should_auto_create_branch(str(test_repo))

    def test_cleanup_empty_branches(self, test_repo):
        """Test that empty claude branches are cleaned up"""
        from claude.session.branch_management import cleanup_empty_branches
        from shared.git import create_branch, get_claude_branches

        # Create empty claude branches
        create_branch("claude/empty1", repo_path=str(test_repo))
        subprocess.run(["git", "checkout", "develop"], cwd=test_repo, check=True, capture_output=True)
        create_branch("claude/empty2", repo_path=str(test_repo))
        subprocess.run(["git", "checkout", "develop"], cwd=test_repo, check=True, capture_output=True)

        # Verify they exist
        branches = get_claude_branches(str(test_repo))
        assert "claude/empty1" in branches
        assert "claude/empty2" in branches

        # Cleanup
        cleanup_empty_branches(str(test_repo))

        # Verify they're gone
        branches = get_claude_branches(str(test_repo))
        assert "claude/empty1" not in branches
        assert "claude/empty2" not in branches

    def test_create_session_branch(self, test_repo):
        """Test session branch creation"""
        from claude.session.branch_management import create_session_branch
        from shared.git import get_current_branch

        # Create session branch
        create_session_branch(str(test_repo))

        # Verify we're on a claude/* branch
        current = get_current_branch(str(test_repo))
        assert current.startswith("claude/")
        assert len(current) == len("claude/20250108143022")  # Check format


class TestChangeHandler:
    """Test suite for uncommitted changes handler"""

    def test_handle_no_uncommitted_changes(self, test_repo):
        """Test handling when there are no uncommitted changes"""
        from claude.session.change_handler import handle_uncommitted_changes
        from shared.git import get_git_status

        # No uncommitted changes
        status_before = get_git_status(str(test_repo))

        # Handle (should be no-op)
        handle_uncommitted_changes(str(test_repo))

        # Status unchanged
        status_after = get_git_status(str(test_repo))
        assert status_before == status_after

    def test_handle_uncommitted_on_non_claude_branch(self, test_repo):
        """Test that uncommitted changes on non-claude branches are left alone"""
        from claude.session.change_handler import handle_uncommitted_changes
        from shared.git import has_uncommitted_changes

        # Create uncommitted change on develop
        test_file = test_repo / "uncommitted.txt"
        test_file.write_text("test")

        # Should have uncommitted changes
        assert has_uncommitted_changes(str(test_repo))

        # Handle (should leave as-is)
        handle_uncommitted_changes(str(test_repo))

        # Still uncommitted
        assert has_uncommitted_changes(str(test_repo))

    def test_handle_uncommitted_on_claude_branch(self, test_repo):
        """Test that uncommitted changes on claude/* branches are auto-committed"""
        from claude.session.change_handler import handle_uncommitted_changes
        from shared.git import create_branch, has_uncommitted_changes

        # Switch to claude branch
        create_branch("claude/test", repo_path=str(test_repo))

        # Create uncommitted change
        test_file = test_repo / "uncommitted.txt"
        test_file.write_text("test")
        assert has_uncommitted_changes(str(test_repo))

        # Handle (should auto-commit)
        handle_uncommitted_changes(str(test_repo))

        # No longer uncommitted
        assert not has_uncommitted_changes(str(test_repo))

        # Verify commit message
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            cwd=test_repo, capture_output=True, text=True
        )
        assert "⚠️ AUTOCOMMIT" in result.stdout


class TestReporter:
    """Test suite for session context reporter"""

    def test_report_session_context(self, test_repo, capsys):
        """Test session context reporting"""
        from claude.session.reporter import report_session_context

        # Report context
        report_session_context(str(test_repo))

        # Check output
        captured = capsys.readouterr()
        assert "Session Started" in captured.err
        assert "develop" in captured.err

    def test_report_with_uncommitted_changes(self, test_repo, capsys):
        """Test reporting shows uncommitted file count"""
        from claude.session.reporter import report_session_context

        # Create uncommitted changes
        test_file = test_repo / "uncommitted.txt"
        test_file.write_text("test")

        # Report
        report_session_context(str(test_repo))

        # Should show uncommitted count
        captured = capsys.readouterr()
        assert "uncommitted" in captured.err


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
