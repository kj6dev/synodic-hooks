#!/usr/bin/env python3
"""Claude-specific git operations"""

import subprocess
from datetime import datetime
from typing import Optional

from .branch import branch_exists, get_branches
from .status import get_current_branch


def create_unique_claude_branch(repo_path: Optional[str] = None) -> str:
    """
    Create a unique claude/* branch with timestamp

    Handles collisions by adding letter suffixes (a, b, c, etc.)

    Args:
        repo_path: Path to git repository

    Returns:
        Created branch name (e.g., claude/20250108143022 or claude/20250108143022a)
    """
    base_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    branch_name = f"claude/{base_timestamp}"

    # Check for collision
    if not branch_exists(branch_name, repo_path):
        return branch_name

    # Add letter suffix
    for suffix in "abcdefghijklmnopqrstuvwxyz":
        candidate = f"claude/{base_timestamp}{suffix}"
        if not branch_exists(candidate, repo_path):
            return candidate

    # Extremely unlikely - use microseconds
    return f"claude/{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def is_claude_branch(
    branch_name: Optional[str] = None, repo_path: Optional[str] = None
) -> bool:
    """
    Check if current or specified branch is a claude/* branch

    Args:
        branch_name: Branch to check (default: current branch)
        repo_path: Path to git repository

    Returns:
        True if branch name starts with claude/
    """
    if branch_name is None:
        branch_name = get_current_branch(repo_path)

    return branch_name.startswith("claude/")


def get_claude_branches(repo_path: Optional[str] = None) -> list[str]:
    """
    Get list of all claude/* branches

    Args:
        repo_path: Path to git repository

    Returns:
        List of claude/* branch names
    """
    return get_branches("claude/*", repo_path)


def is_empty_claude_branch(branch_name: str, repo_path: Optional[str] = None) -> bool:
    """
    Check if a claude/* branch has any unique commits

    Args:
        branch_name: Branch to check
        repo_path: Path to git repository

    Returns:
        True if branch has no unique commits vs its base
    """
    try:
        # Try to find merge-base with develop/main/master
        for base in ["develop", "main", "master"]:
            result = subprocess.run(
                ["git", "merge-base", branch_name, base],
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=5,
            )

            if result.returncode == 0:
                merge_base = result.stdout.strip()

                # Get branch HEAD
                result = subprocess.run(
                    ["git", "rev-parse", branch_name],
                    capture_output=True,
                    text=True,
                    cwd=repo_path,
                    timeout=5,
                )

                branch_head = result.stdout.strip()

                # If HEAD == merge-base, no unique commits
                return merge_base == branch_head

        # Couldn't find merge-base, assume not empty (safe default)
        return False

    except Exception:
        return False


def is_merged_claude_branch(branch_name: str, repo_path: Optional[str] = None) -> bool:
    """
    Check if a claude/* branch is fully merged to its base

    Args:
        branch_name: Branch to check
        repo_path: Path to git repository

    Returns:
        True if branch is fully merged to develop/main/master
    """
    try:
        # Try to check if merged to develop/main/master
        for base in ["develop", "main", "master"]:
            # Check if base branch exists
            check_base = subprocess.run(
                ["git", "rev-parse", "--verify", base],
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=5,
            )

            if check_base.returncode != 0:
                continue  # Base doesn't exist, try next one

            # Check if branch is merged into base
            result = subprocess.run(
                ["git", "branch", "--merged", base],
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=5,
            )

            if result.returncode == 0:
                # Parse output to see if our branch is in the list
                merged_branches = [
                    b.strip().lstrip("* ") for b in result.stdout.strip().split("\n")
                ]
                if branch_name in merged_branches:
                    return True

        # Not merged to any base
        return False

    except Exception:
        return False
