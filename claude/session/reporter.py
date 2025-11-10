#!/usr/bin/env python3
"""Session context reporter for Claude Code"""

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.git import get_claude_branches, get_current_branch, get_git_status, has_uncommitted_changes
from shared.discord import notify_session_start


def report_session_context(repo_path: str) -> None:
    """
    Report useful session context to user

    Shows:
    - Current branch
    - Uncommitted changes status
    - Number of existing claude/* branches

    Args:
        repo_path: Path to git repository
    """
    try:
        current = get_current_branch(repo_path)
        has_changes = has_uncommitted_changes(repo_path)
        claude_branches = get_claude_branches(repo_path)

        print("", file=sys.stderr)
        print("🚀 Session Started", file=sys.stderr)
        print(f"📁 Project: {Path(repo_path).name}", file=sys.stderr)
        print(f"📌 Branch: {current}", file=sys.stderr)

        if has_changes:
            status = get_git_status(repo_path)
            file_count = len([line for line in status.strip().split('\n') if line])
            print(f"⚠️  {file_count} uncommitted file(s)", file=sys.stderr)

        if len(claude_branches) > 1:
            print(f"🌿 {len(claude_branches)} claude/* branches exist", file=sys.stderr)

        print("", file=sys.stderr)

        # Send Discord notification (non-blocking)
        notify_session_start(repo_path, current)

    except Exception:
        # Don't fail on reporting errors
        pass
