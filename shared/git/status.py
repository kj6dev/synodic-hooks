#!/usr/bin/env python3
"""Git status and state operations"""

import subprocess
from typing import Optional


def get_current_branch(repo_path: Optional[str] = None) -> str:
    """
    Get the current git branch name

    Args:
        repo_path: Path to git repository (default: current directory)

    Returns:
        Current branch name, or empty string if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_git_status(repo_path: Optional[str] = None) -> str:
    """
    Get git status output (porcelain format)

    Args:
        repo_path: Path to git repository

    Returns:
        Git status output, or empty string on error
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=5
        )
        return result.stdout
    except Exception:
        return ""


def has_uncommitted_changes(repo_path: Optional[str] = None) -> bool:
    """
    Check if repository has uncommitted changes

    Args:
        repo_path: Path to git repository

    Returns:
        True if there are uncommitted changes
    """
    status = get_git_status(repo_path)
    return bool(status.strip())
