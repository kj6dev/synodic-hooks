#!/usr/bin/env python3
"""Git branch operations"""

import subprocess
from typing import Optional


def branch_exists(branch_name: str, repo_path: Optional[str] = None) -> bool:
    """
    Check if a branch exists

    Args:
        branch_name: Branch name to check
        repo_path: Path to git repository

    Returns:
        True if branch exists
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=5
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def create_branch(branch_name: str, base_branch: str = "develop", repo_path: Optional[str] = None) -> bool:
    """
    Create a new git branch

    Args:
        branch_name: Name for the new branch
        base_branch: Branch to create from (default: develop)
        repo_path: Path to git repository

    Returns:
        True if branch created successfully
    """
    try:
        # Check if base branch exists
        result = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{base_branch}"],
            cwd=repo_path,
            timeout=5
        )

        if result.returncode != 0:
            # Base branch doesn't exist, try main/master
            for fallback in ["main", "master"]:
                result = subprocess.run(
                    ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{fallback}"],
                    cwd=repo_path,
                    timeout=5
                )
                if result.returncode == 0:
                    base_branch = fallback
                    break

        # Create branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name, base_branch],
            check=True,
            capture_output=True,
            cwd=repo_path,
            timeout=10
        )
        return True

    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False


def checkout_branch(branch_name: str, repo_path: Optional[str] = None) -> bool:
    """
    Checkout an existing branch

    Args:
        branch_name: Branch to checkout
        repo_path: Path to git repository

    Returns:
        True if checkout successful
    """
    try:
        subprocess.run(
            ["git", "checkout", branch_name],
            check=True,
            capture_output=True,
            cwd=repo_path,
            timeout=10
        )
        return True
    except Exception:
        return False


def delete_branch(branch_name: str, force: bool = False, repo_path: Optional[str] = None) -> bool:
    """
    Delete a git branch

    Args:
        branch_name: Branch to delete
        force: Force delete even if not merged
        repo_path: Path to git repository

    Returns:
        True if deleted successfully
    """
    try:
        flag = "-D" if force else "-d"
        subprocess.run(
            ["git", "branch", flag, branch_name],
            check=True,
            capture_output=True,
            cwd=repo_path,
            timeout=5
        )
        return True
    except Exception:
        return False


def get_branches(pattern: str = "*", repo_path: Optional[str] = None) -> list[str]:
    """
    Get list of branches matching pattern

    Args:
        pattern: Branch name pattern (default: all branches)
        repo_path: Path to git repository

    Returns:
        List of branch names
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--list", pattern],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=5
        )

        # Parse output (format: "  branch-name" or "* branch-name")
        branches = []
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if line:
                # Remove leading * (current branch marker)
                branch = line.lstrip('* ').strip()
                branches.append(branch)

        return branches

    except Exception:
        return []
