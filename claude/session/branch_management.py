#!/usr/bin/env python3
"""Branch management for Claude Code sessions"""

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.git import (
    create_branch,
    create_unique_claude_branch,
    delete_branch,
    get_claude_branches,
    get_current_branch,
    is_claude_branch,
    is_empty_claude_branch,
    is_git_repo_root,
    is_merged_claude_branch,
)
from shared.hook_utils import emit_info, emit_success, emit_warning

# Home-level directories where auto-branch should NOT happen
HOME_DIRS = [
    str(Path.home()),
    str(Path.home() / "Developer"),
    str(Path.home() / "Downloads"),
    str(Path.home() / "Documents"),
    str(Path.home() / "Desktop"),
]


def should_auto_create_branch(cwd: str) -> bool:
    """
    Determine if we should auto-create a claude/* branch

    DISABLED: Auto-branch creation disabled to prevent accumulating work
    on long-lived claude/* branches that can be deleted before merging.

    Claude should explicitly create branches with meaningful names.

    Args:
        cwd: Current working directory where Claude started

    Returns:
        Always False (auto-branch creation disabled)
    """
    return False


def cleanup_empty_branches(repo_path: str) -> None:
    """
    Remove claude/* branches with no unique commits or that are fully merged

    Removes branches that are:
    1. Empty (no unique commits compared to base branch)
    2. Fully merged to develop/main/master

    Self-healing: Errors only emit warnings, don't fail

    Args:
        repo_path: Path to git repository
    """
    try:
        branches = get_claude_branches(repo_path)
        current = get_current_branch(repo_path)

        for branch in branches:
            # Skip current branch
            if branch == current:
                continue

            # Check if empty (zero commits)
            if is_empty_claude_branch(branch, repo_path):
                if delete_branch(branch, force=True, repo_path=repo_path):
                    emit_info(f"Removed empty branch: {branch}")
                else:
                    emit_warning(f"Could not remove empty branch: {branch}")
                continue

            # Check if merged
            if is_merged_claude_branch(branch, repo_path):
                if delete_branch(branch, force=False, repo_path=repo_path):
                    emit_info(f"Removed merged branch: {branch}")
                else:
                    emit_warning(f"Could not remove merged branch: {branch}")
                continue

    except Exception as e:
        emit_warning(f"Branch cleanup failed: {e}")
        # Don't fail - this is housekeeping


def create_session_branch(repo_path: str) -> None:
    """
    Create a new timestamped claude/* branch for this session

    Branch name format: claude/20250108143022
    Collision handling: Adds letter suffix (a, b, c, etc.)

    Self-healing: Errors only emit warnings

    Args:
        repo_path: Path to git repository
    """
    try:
        # Generate unique branch name
        branch_name = create_unique_claude_branch(repo_path)

        # Create and checkout branch
        if create_branch(branch_name, repo_path=repo_path):
            emit_success(f"Created session branch: {branch_name}")
        else:
            emit_warning(f"Could not create branch: {branch_name}")
            emit_info("Continuing on current branch")

    except Exception as e:
        emit_warning(f"Branch creation failed: {e}")
        emit_info("Continuing on current branch")
