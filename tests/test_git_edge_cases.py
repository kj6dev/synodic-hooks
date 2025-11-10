#!/usr/bin/env python3
"""
Tests for git utility edge cases and error handling

Run with: python3 -m pytest tests/test_git_edge_cases.py
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


class TestBranchOperations:
    """Test suite for branch operation edge cases"""

    def test_branch_exists(self, test_repo):
        """Test branch existence checking"""
        from shared.git import branch_exists

        # Existing branch
        assert branch_exists("develop", str(test_repo))

        # Non-existing branch
        assert not branch_exists("nonexistent", str(test_repo))

    def test_delete_branch(self, test_repo):
        """Test branch deletion"""
        from shared.git import create_branch, delete_branch, branch_exists

        # Create a branch without switching to it
        subprocess.run(
            ["git", "branch", "to-delete"],
            cwd=test_repo, check=True, capture_output=True
        )
        assert branch_exists("to-delete", str(test_repo))

        # Delete it (use force since create_branch might switch to it)
        result = delete_branch("to-delete", force=True, repo_path=str(test_repo))
        assert result is True
        assert not branch_exists("to-delete", str(test_repo))

    def test_get_branches(self, test_repo):
        """Test listing all branches"""
        from shared.git import get_branches, create_branch

        branches = get_branches(repo_path=str(test_repo))
        assert "develop" in branches

        # Create more branches (switch back to develop after each)
        create_branch("feature1", repo_path=str(test_repo))
        subprocess.run(["git", "checkout", "develop"], cwd=test_repo, check=True, capture_output=True)
        create_branch("feature2", repo_path=str(test_repo))
        subprocess.run(["git", "checkout", "develop"], cwd=test_repo, check=True, capture_output=True)

        branches = get_branches(repo_path=str(test_repo))
        assert "feature1" in branches
        assert "feature2" in branches

    def test_checkout_branch(self, test_repo):
        """Test checking out branches"""
        from shared.git import create_branch, checkout_branch, get_current_branch

        # Create a branch
        create_branch("feature", repo_path=str(test_repo))

        # Checkout develop first
        checkout_branch("develop", str(test_repo))
        assert get_current_branch(str(test_repo)) == "develop"

        # Checkout feature
        checkout_branch("feature", str(test_repo))
        assert get_current_branch(str(test_repo)) == "feature"

    def test_create_branch_with_custom_base(self, test_repo):
        """Test creating branch from custom base"""
        from shared.git import create_branch, get_current_branch

        # Create feature branch from develop
        create_branch("feature", "develop", str(test_repo))
        assert get_current_branch(str(test_repo)) == "feature"


class TestRepoOperations:
    """Test suite for repository operation edge cases"""

    def test_find_repo_root_from_subdirectory(self, test_repo):
        """Test finding repo root from nested directory"""
        from shared.git import find_repo_root

        # Create nested directory
        nested = test_repo / "subdir" / "nested"
        nested.mkdir(parents=True)

        # Should find root from nested dir
        root = find_repo_root(str(nested))
        # Resolve both paths to handle symlinks (macOS /var vs /private/var)
        assert Path(root).resolve() == Path(test_repo).resolve()

    def test_find_repo_root_no_git(self, tmp_path):
        """Test repo root finding when not in a git repo"""
        from shared.git import find_repo_root

        # Not a git repo
        result = find_repo_root(str(tmp_path))
        assert result is None

    def test_is_git_repo_root_false_for_subdir(self, test_repo):
        """Test that subdirectories are not repo roots"""
        from shared.git import is_git_repo_root

        # Create subdirectory
        subdir = test_repo / "subdir"
        subdir.mkdir()

        # Subdir is not root
        assert not is_git_repo_root(str(subdir))
        # But parent is
        assert is_git_repo_root(str(test_repo))


class TestClaudeOperations:
    """Test suite for Claude-specific git operations"""

    def test_create_claude_branch_with_collision(self, test_repo):
        """Test that collision handling creates unique branches"""
        from shared.git import create_unique_claude_branch, branch_exists

        # Create first branch
        branch1 = create_unique_claude_branch(str(test_repo))
        assert branch1.startswith("claude/")

        # Actually create the branch
        subprocess.run(
            ["git", "branch", branch1],
            cwd=test_repo, check=True, capture_output=True
        )
        assert branch_exists(branch1, str(test_repo))

        # Try to create another in same second (may or may not collide)
        branch2 = create_unique_claude_branch(str(test_repo))
        assert branch2.startswith("claude/")

        # Branches should be different if created in same second
        if branch1.split("/")[1][:14] == branch2.split("/")[1][:14]:
            # Same timestamp base, should have suffix
            assert branch2 != branch1

    def test_is_empty_claude_branch_with_commits(self, test_repo):
        """Test empty branch detection with commits"""
        from shared.git import create_branch, is_empty_claude_branch

        # Create claude branch
        branch_name = "claude/test123"
        create_branch(branch_name, "develop", str(test_repo))

        # Empty at first
        assert is_empty_claude_branch(branch_name, str(test_repo))

        # Add commit
        test_file = test_repo / "test.txt"
        test_file.write_text("content")
        subprocess.run(["git", "add", "."], cwd=test_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "test"],
            cwd=test_repo, check=True, capture_output=True
        )

        # No longer empty
        assert not is_empty_claude_branch(branch_name, str(test_repo))

    def test_is_claude_branch_patterns(self):
        """Test various claude branch name patterns"""
        from shared.git import is_claude_branch

        # Valid claude branches
        assert is_claude_branch("claude/test")
        assert is_claude_branch("claude/20250108143022")
        assert is_claude_branch("claude/20250108143022a")
        assert is_claude_branch("claude/feature-name")

        # Not claude branches
        assert not is_claude_branch("develop")
        assert not is_claude_branch("main")
        assert not is_claude_branch("feature/test")
        assert not is_claude_branch("claude")  # No slash
        assert not is_claude_branch("claudes/test")  # Wrong prefix


class TestStatusOperations:
    """Test suite for git status operations"""

    def test_get_git_status(self, test_repo):
        """Test getting full git status"""
        from shared.git import get_git_status

        # Clean status (porcelain format returns empty for clean repo)
        status = get_git_status(str(test_repo))
        assert status.strip() == ""

        # With changes (porcelain format shows file status)
        test_file = test_repo / "new_file.txt"
        test_file.write_text("content")

        status = get_git_status(str(test_repo))
        assert "new_file.txt" in status

    def test_has_uncommitted_changes_staged_vs_unstaged(self, test_repo):
        """Test uncommitted changes detection for staged and unstaged"""
        from shared.git import has_uncommitted_changes

        # Clean
        assert not has_uncommitted_changes(str(test_repo))

        # Add unstaged file
        test_file = test_repo / "unstaged.txt"
        test_file.write_text("unstaged")
        assert has_uncommitted_changes(str(test_repo))

        # Stage it
        subprocess.run(["git", "add", "."], cwd=test_repo, check=True, capture_output=True)
        assert has_uncommitted_changes(str(test_repo))

        # Commit it
        subprocess.run(
            ["git", "commit", "-m", "commit"],
            cwd=test_repo, check=True, capture_output=True
        )
        assert not has_uncommitted_changes(str(test_repo))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
