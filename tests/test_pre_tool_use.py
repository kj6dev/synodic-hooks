#!/usr/bin/env python3
"""
Tests for pre_tool_use hook

Run with: python3 -m pytest tests/test_pre_tool_use.py
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude.pre_tool_use import is_git_commit_command


class TestGitCommitDetection:
    """Test suite for git commit command detection"""

    def test_basic_git_commit(self):
        """Test basic git commit detection"""
        assert is_git_commit_command("git commit -m 'message'")
        assert is_git_commit_command('git commit -m "message"')
        assert is_git_commit_command("git commit")

    def test_git_commit_variants(self):
        """Test various git commit command formats"""
        assert is_git_commit_command("git commit --amend")
        assert is_git_commit_command("git commit -a -m 'message'")
        assert is_git_commit_command("git commit --allow-empty -m 'empty'")
        assert is_git_commit_command("git -C /path/to/repo commit")
        assert is_git_commit_command("git --no-pager commit")

    def test_not_git_commit(self):
        """Test commands that should NOT be detected as git commit"""
        assert not is_git_commit_command("git log --oneline")
        assert not is_git_commit_command("git show commit-abc123")
        assert not is_git_commit_command("git log --grep=commit")
        assert not is_git_commit_command("ls -la")
        assert not is_git_commit_command("echo 'git commit'")  # In quotes

    def test_piped_commands(self):
        """Test piped commands"""
        # Should not match commit in pipeline
        assert not is_git_commit_command("git log | grep commit")
        assert not is_git_commit_command("git branch | head -n 1")

    def test_compound_commands(self):
        """Test compound commands with &&"""
        # First command is git commit
        assert is_git_commit_command("git commit -m 'msg' && git push")

        # First command is not git commit
        assert not is_git_commit_command("git add . && git status")

    def test_edge_cases(self):
        """Test edge cases"""
        assert not is_git_commit_command("")  # Empty string
        assert not is_git_commit_command("git")  # Just 'git'
        assert not is_git_commit_command("commit")  # No 'git'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
