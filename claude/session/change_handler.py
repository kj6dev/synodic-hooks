#!/usr/bin/env python3
"""Uncommitted changes handler for Claude Code sessions"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.git import get_current_branch, get_git_status, has_uncommitted_changes, is_claude_branch
from shared.hook_utils import emit_info, emit_success, emit_warning


def handle_uncommitted_changes(repo_path: str) -> None:
    """
    Handle uncommitted changes from previous session

    If on a claude/* branch with uncommitted work:
    - Auto-commit with AUTOCOMMIT⚠️ prefix
    - Let git hooks handle quality checking

    Self-healing: Errors only emit warnings, don't block session

    Args:
        repo_path: Path to git repository
    """
    try:
        if not has_uncommitted_changes(repo_path):
            return  # Nothing to do

        current_branch = get_current_branch(repo_path)

        # Only auto-commit on claude/* branches
        if not is_claude_branch(current_branch, repo_path):
            emit_warning(f"Uncommitted changes on non-claude branch: {current_branch}")
            emit_info("Leaving as-is for manual handling")
            return

        # Get status for commit message context
        status = get_git_status(repo_path)
        file_count = len([line for line in status.strip().split('\n') if line])

        # Commit - let git hooks handle quality
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        commit_msg = f"⚠️ AUTOCOMMIT {timestamp}\n\nAuto-committed {file_count} file(s) from previous session"

        try:
            subprocess.run(
                ["git", "add", "-A"],
                check=True,
                cwd=repo_path,
                timeout=10
            )

            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True,
                cwd=repo_path,
                timeout=30
            )

            emit_success(f"Auto-committed {file_count} file(s) to {current_branch}")

        except subprocess.CalledProcessError as e:
            # Git hooks may have rejected commit (quality failed)
            emit_warning("Auto-commit failed - quality checks didn't pass")
            emit_info("Fix issues manually or commit with --no-verify")
            # Don't block session - user can handle it

    except Exception as e:
        emit_warning(f"Could not handle uncommitted changes: {e}")
        # Don't block session
