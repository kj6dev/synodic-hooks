#!/usr/bin/env python3
"""
Tests for pre_tool_use validation logic

Run with: python3 -m pytest tests/test_pre_tool_use_validation.py
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


class TestValidateGitCommit:
    """Test suite for git commit validation"""

    def test_allow_commit_on_claude_branch(self, test_repo):
        """Test that commits are allowed on claude/* branches"""
        from claude.pre_tool_use import validate_git_commit
        from shared.git import create_branch

        # Create and checkout claude branch
        create_branch("claude/test", repo_path=str(test_repo))

        # Validate commit
        allowed, reason = validate_git_commit("git commit -m 'test'", str(test_repo))

        assert allowed is True
        assert "✅" in reason
        assert "claude/test" in reason

    def test_block_commit_on_develop_branch(self, test_repo):
        """Test that commits are blocked on develop branch"""
        from claude.pre_tool_use import validate_git_commit

        # On develop branch (from fixture)
        allowed, reason = validate_git_commit("git commit -m 'test'", str(test_repo))

        assert allowed is False
        assert "🚨" in reason
        assert "Commits only allowed on claude/*" in reason
        assert "develop" in reason

    def test_block_commit_on_main_branch(self, test_repo):
        """Test that commits are blocked on main branch"""
        from claude.pre_tool_use import validate_git_commit

        # Create and checkout main
        subprocess.run(
            ["git", "checkout", "-b", "main"],
            cwd=test_repo, check=True, capture_output=True
        )

        allowed, reason = validate_git_commit("git commit -m 'test'", str(test_repo))

        assert allowed is False
        assert "🚨" in reason
        assert "main" in reason

    def test_block_commit_on_feature_branch(self, test_repo):
        """Test that commits are blocked on feature branches"""
        from claude.pre_tool_use import validate_git_commit

        # Create feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature/new-thing"],
            cwd=test_repo, check=True, capture_output=True
        )

        allowed, reason = validate_git_commit("git commit -m 'test'", str(test_repo))

        assert allowed is False
        assert "feature/new-thing" in reason

    def test_provide_helpful_error_message(self, test_repo):
        """Test that blocked commits get helpful guidance"""
        from claude.pre_tool_use import validate_git_commit

        allowed, reason = validate_git_commit("git commit -m 'test'", str(test_repo))

        # Should provide guidance
        assert "Create a claude/* branch" in reason
        assert "git checkout -b" in reason
        assert "Or I can create one for you" in reason

    def test_handle_not_in_git_repo(self, tmp_path):
        """Test graceful handling when not in a git repo"""
        from claude.pre_tool_use import validate_git_commit

        # Not a git repo
        allowed, reason = validate_git_commit("git commit -m 'test'", str(tmp_path))

        assert allowed is False
        assert "Not in a git repository" in reason or "detached HEAD" in reason

    def test_graceful_error_handling(self, tmp_path):
        """Test that validation errors return empty branch (no error) which blocks"""
        from claude.pre_tool_use import validate_git_commit

        # Invalid path - get_current_branch returns "" which isn't a claude branch
        allowed, reason = validate_git_commit("git commit -m 'test'", "/nonexistent/path")

        # Empty branch name means not in repo or error - should block
        assert allowed is False
        assert "Not in a git repository" in reason or "detached HEAD" in reason


class TestValidateBashCommand:
    """Test suite for bash command validation"""

    def test_validate_git_commit_command(self, test_repo):
        """Test that git commit commands are validated"""
        from claude.pre_tool_use import validate_bash_command
        from shared.git import create_branch

        # Setup claude branch
        create_branch("claude/test", repo_path=str(test_repo))

        hook_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'test'"},
            "cwd": str(test_repo)
        }

        # Should validate and allow
        allowed = validate_bash_command(hook_data)
        assert allowed is True

    def test_block_git_commit_on_wrong_branch(self, test_repo, capsys):
        """Test that git commits on wrong branches are blocked"""
        from claude.pre_tool_use import validate_bash_command

        hook_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'test'"},
            "cwd": str(test_repo)
        }

        # On develop - should block
        allowed = validate_bash_command(hook_data)
        assert allowed is False

        # Check error was emitted
        captured = capsys.readouterr()
        assert "🚨" in captured.err
        assert "Commits only allowed on claude/*" in captured.err

    def test_allow_non_commit_commands(self, test_repo):
        """Test that non-commit git commands are allowed"""
        from claude.pre_tool_use import validate_bash_command

        commands = [
            "git status",
            "git log",
            "git diff",
            "git branch",
            "git push",
            "git pull",
            "ls -la"
        ]

        for cmd in commands:
            hook_data = {
                "tool_name": "Bash",
                "tool_input": {"command": cmd},
                "cwd": str(test_repo)
            }
            allowed = validate_bash_command(hook_data)
            assert allowed is True, f"Should allow: {cmd}"

    def test_allow_non_bash_tools(self, test_repo):
        """Test that non-Bash tools are always allowed"""
        from claude.pre_tool_use import validate_bash_command

        tools = ["Read", "Write", "Edit", "Grep", "Glob"]

        for tool in tools:
            hook_data = {
                "tool_name": tool,
                "tool_input": {},
                "cwd": str(test_repo)
            }
            allowed = validate_bash_command(hook_data)
            assert allowed is True, f"Should allow tool: {tool}"

    def test_handle_missing_command(self, test_repo):
        """Test graceful handling of missing command in hook data"""
        from claude.pre_tool_use import validate_bash_command

        hook_data = {
            "tool_name": "Bash",
            "tool_input": {},
            "cwd": str(test_repo)
        }

        # Should allow (permissive on errors)
        allowed = validate_bash_command(hook_data)
        assert allowed is True


class TestGitCommitDetectionAdvanced:
    """Additional edge cases for git commit detection"""

    def test_git_with_multiple_flags(self):
        """Test git commit with multiple flags"""
        from claude.pre_tool_use import is_git_commit_command

        assert is_git_commit_command("git -C /path --no-pager commit -m 'test'")
        assert is_git_commit_command("git --git-dir=/path/.git commit")
        assert is_git_commit_command("git --work-tree=/path commit -a")

    def test_git_commit_with_env_vars(self):
        """Test git commit with environment variable syntax"""
        from claude.pre_tool_use import is_git_commit_command

        # Env vars before git command - first token isn't 'git'
        # This is acceptable - env vars should be set separately
        assert not is_git_commit_command("GIT_AUTHOR_NAME='Test' git commit -m 'msg'")

        # But these should work
        assert is_git_commit_command("git commit -m 'msg'")

    def test_git_subcommands_not_commit(self):
        """Test that other git subcommands aren't detected as commit"""
        from claude.pre_tool_use import is_git_commit_command

        non_commits = [
            "git cherry-pick abc123",
            "git rebase -i HEAD~3",
            "git merge feature-branch",
            "git stash",
            "git checkout -b branch",
            "git switch main",
            "git restore file.txt",
        ]

        for cmd in non_commits:
            assert not is_git_commit_command(cmd), f"Should not detect as commit: {cmd}"

    def test_commit_in_string_literals(self):
        """Test that 'commit' in string literals doesn't match"""
        from claude.pre_tool_use import is_git_commit_command

        # These should NOT be detected as git commit
        assert not is_git_commit_command("echo 'git commit -m test'")
        assert not is_git_commit_command("grep 'commit' file.txt")

    def test_semicolon_separated_commands(self):
        """Test semicolon-separated commands"""
        from claude.pre_tool_use import is_git_commit_command

        # First command is what matters (shlex will stop at semicolon)
        assert is_git_commit_command("git commit -m 'test'; git push")
        assert not is_git_commit_command("git status; git commit -m 'test'")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
