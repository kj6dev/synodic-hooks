#!/usr/bin/env python3
"""
Tests for git_utils module

Run with: python3 -m pytest tests/test_git_utils.py
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def test_repo():
    """Create a temporary git repository for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        test_file = repo_path / "README.md"
        test_file.write_text("# Test Repo\n")
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Get current branch name (may be main, master, or develop depending on git config)
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        current_branch = result.stdout.strip()

        # Only create develop branch if we're not already on it
        if current_branch != "develop":
            subprocess.run(
                ["git", "branch", "develop"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "develop"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

        yield repo_path


class TestGitUtils:
    """Test suite for git utility functions"""

    def test_is_git_repo_root(self, test_repo):
        """Test git repo detection"""
        from shared.git import is_git_repo_root

        assert is_git_repo_root(str(test_repo))
        assert not is_git_repo_root(str(test_repo / "nonexistent"))

    def test_get_current_branch(self, test_repo):
        """Test current branch detection"""
        from shared.git import get_current_branch

        branch = get_current_branch(str(test_repo))
        assert branch == "develop"

    def test_create_unique_claude_branch(self, test_repo):
        """Test unique branch name generation"""
        from shared.git import create_unique_claude_branch

        # First branch should not have suffix
        branch1 = create_unique_claude_branch(str(test_repo))
        assert branch1.startswith("claude/")
        assert len(branch1) == len("claude/20250108143022")

        # Create the branch
        subprocess.run(
            ["git", "branch", branch1], cwd=test_repo, check=True, capture_output=True
        )

        # Second branch same second should have 'a' suffix
        branch2 = create_unique_claude_branch(str(test_repo))
        if branch2 == branch1:
            # Different second, try forcing collision
            subprocess.run(
                ["git", "branch", branch2],
                cwd=test_repo,
                check=True,
                capture_output=True,
            )
            branch2 = create_unique_claude_branch(str(test_repo))

        # Should have suffix or different timestamp
        assert branch2 != branch1

    def test_is_claude_branch(self, test_repo):
        """Test claude branch detection"""
        from shared.git import is_claude_branch

        assert not is_claude_branch("develop", str(test_repo))
        assert not is_claude_branch("main", str(test_repo))
        assert is_claude_branch("claude/20250108143022", str(test_repo))
        assert is_claude_branch("claude/20250108143022a", str(test_repo))
        assert is_claude_branch("claude/feature", str(test_repo))

    def test_is_empty_claude_branch(self, test_repo):
        """Test empty branch detection"""
        from shared.git import create_branch, is_empty_claude_branch

        # Create a claude branch with no commits
        branch_name = "claude/20250108143022"
        create_branch(branch_name, "develop", str(test_repo))

        # Should be empty (no unique commits)
        assert is_empty_claude_branch(branch_name, str(test_repo))

        # Add a commit
        subprocess.run(
            ["git", "checkout", branch_name],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )
        test_file = test_repo / "test.txt"
        test_file.write_text("test")
        subprocess.run(
            ["git", "add", "."], cwd=test_repo, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "test"],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )

        # Should not be empty now
        assert not is_empty_claude_branch(branch_name, str(test_repo))

    def test_has_uncommitted_changes(self, test_repo):
        """Test uncommitted changes detection"""
        from shared.git import has_uncommitted_changes

        # Clean repo
        assert not has_uncommitted_changes(str(test_repo))

        # Create uncommitted file
        test_file = test_repo / "uncommitted.txt"
        test_file.write_text("uncommitted")

        # Should detect changes
        assert has_uncommitted_changes(str(test_repo))

    def test_get_claude_branches(self, test_repo):
        """Test listing claude branches"""
        from shared.git import create_branch, get_claude_branches

        # No claude branches initially
        branches = get_claude_branches(str(test_repo))
        assert len(branches) == 0

        # Create some claude branches
        create_branch("claude/20250108143022", "develop", str(test_repo))
        create_branch("claude/20250108143023", "develop", str(test_repo))
        create_branch("regular-branch", "develop", str(test_repo))

        # Should only list claude branches
        branches = get_claude_branches(str(test_repo))
        assert len(branches) == 2
        assert all(b.startswith("claude/") for b in branches)

    def test_is_merged_claude_branch(self, test_repo):
        """Test merged branch detection"""
        from shared.git import is_merged_claude_branch

        # Create a claude branch with a commit
        branch_name = "claude/20250108143025"
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )
        test_file = test_repo / "feature.txt"
        test_file.write_text("feature work")
        subprocess.run(
            ["git", "add", "."], cwd=test_repo, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add feature"],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )

        # Branch is not merged yet
        assert not is_merged_claude_branch(branch_name, str(test_repo))

        # Merge branch to develop
        subprocess.run(
            ["git", "checkout", "develop"],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "merge", "--no-ff", branch_name],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )

        # Branch should now be detected as merged
        assert is_merged_claude_branch(branch_name, str(test_repo))

    def test_cleanup_empty_branches(self, test_repo):
        """Test automatic cleanup of empty and merged branches"""
        from claude.session.branch_management import cleanup_empty_branches
        from shared.git import create_branch, get_claude_branches

        # Create an empty branch (no commits)
        empty_branch = "claude/20250108143030"
        create_branch(empty_branch, "develop", str(test_repo))

        # Create a branch with commits
        work_branch = "claude/20250108143031"
        subprocess.run(
            ["git", "checkout", "-b", work_branch],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )
        test_file = test_repo / "work.txt"
        test_file.write_text("work in progress")
        subprocess.run(
            ["git", "add", "."], cwd=test_repo, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "WIP"],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )

        # Create a merged branch
        merged_branch = "claude/20250108143032"
        subprocess.run(
            ["git", "checkout", "-b", merged_branch, "develop"],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )
        merged_file = test_repo / "merged.txt"
        merged_file.write_text("merged work")
        subprocess.run(
            ["git", "add", "."], cwd=test_repo, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Merged feature"],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "develop"],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "merge", "--no-ff", merged_branch],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )

        # Should have 3 claude branches before cleanup
        branches_before = get_claude_branches(str(test_repo))
        assert len(branches_before) == 3

        # Run cleanup from work_branch (current branch should be preserved)
        subprocess.run(
            ["git", "checkout", work_branch],
            cwd=test_repo,
            check=True,
            capture_output=True,
        )
        cleanup_empty_branches(str(test_repo))

        # Should remove empty_branch and merged_branch, keep work_branch
        branches_after = get_claude_branches(str(test_repo))
        assert len(branches_after) == 1
        assert work_branch in branches_after
        assert empty_branch not in branches_after
        assert merged_branch not in branches_after


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
