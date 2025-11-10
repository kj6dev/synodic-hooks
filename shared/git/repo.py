#!/usr/bin/env python3
"""Git repository operations"""

from pathlib import Path
from typing import Optional


def is_git_repo_root(path: str) -> bool:
    """
    Check if path is the root of a git repository

    Args:
        path: Directory path to check

    Returns:
        True if path is a git repo root
    """
    git_dir = Path(path) / ".git"
    return git_dir.exists() and git_dir.is_dir()


def find_repo_root(start_path: str) -> Optional[str]:
    """
    Find git repository root by walking up directory tree

    Args:
        start_path: Starting directory path

    Returns:
        Path to repo root, or None if not in a git repo
    """
    current = Path(start_path).resolve()

    # Walk up until we find .git or reach root
    while current != current.parent:
        if is_git_repo_root(str(current)):
            return str(current)
        current = current.parent

    return None
