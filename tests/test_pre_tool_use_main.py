#!/usr/bin/env python3
"""
Tests for pre_tool_use main() entry point

Run with: python3 -m pytest tests/test_pre_tool_use_main.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

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

        # Get current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path, capture_output=True, text=True
        )
        current_branch = result.stdout.strip()

        # Create develop branch if needed
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


class TestPreToolUseMain:
    """Test suite for main() entry point"""

    def test_main_allows_non_bash_tools(self):
        """Test that non-Bash tools pass through"""
        from claude.pre_tool_use import main

        hook_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/path/to/file"},
        }

        with patch('claude.pre_tool_use.get_hook_data', return_value=hook_data):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_main_allows_non_commit_bash(self, test_repo):
        """Test that non-commit Bash commands pass through"""
        from claude.pre_tool_use import main

        hook_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
            "cwd": str(test_repo)
        }

        with patch('claude.pre_tool_use.get_hook_data', return_value=hook_data):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_main_blocks_commit_on_wrong_branch(self, test_repo, capsys):
        """Test that commits on non-claude branches are blocked"""
        from claude.pre_tool_use import main
        from shared.git import create_branch

        # On develop branch
        hook_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'test'"},
            "cwd": str(test_repo)
        }

        with patch('claude.pre_tool_use.get_hook_data', return_value=hook_data):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2  # Blocked

            captured = capsys.readouterr()
            assert "🚨" in captured.err
            assert "Commits only allowed on claude/*" in captured.err

    def test_main_allows_commit_on_claude_branch(self, test_repo, capsys):
        """Test that commits on claude/* branches are allowed"""
        from claude.pre_tool_use import main
        from shared.git import create_branch

        # Create and checkout claude branch
        create_branch("claude/test", repo_path=str(test_repo))

        hook_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'test'"},
            "cwd": str(test_repo)
        }

        with patch('claude.pre_tool_use.get_hook_data', return_value=hook_data):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0  # Allowed

            captured = capsys.readouterr()
            assert "✅" in captured.err

    def test_main_graceful_error_handling(self, capsys):
        """Test that main() handles errors gracefully"""
        from claude.pre_tool_use import main

        # Invalid hook data
        hook_data = {}

        with patch('claude.pre_tool_use.get_hook_data', return_value=hook_data):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0  # Permissive on errors


class TestPreToolUseErrorPaths:
    """Test suite for error handling paths"""

    def test_validate_git_commit_empty_branch(self):
        """Test validation when branch detection fails"""
        from claude.pre_tool_use import validate_git_commit

        # Non-git directory
        allowed, reason = validate_git_commit("git commit -m 'test'", "/nonexistent/path")

        assert allowed is False
        assert "Not in a git repository" in reason or "detached HEAD" in reason

    def test_validate_bash_command_missing_cwd(self):
        """Test validation when cwd is missing"""
        from claude.pre_tool_use import validate_bash_command

        hook_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'test'"},
            # No cwd - should default to "."
        }

        # Should not crash, will check current directory
        result = validate_bash_command(hook_data)
        # Result depends on if current dir is a git repo
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
