#!/usr/bin/env python3
"""
SessionStart Hook for Claude Code

Runs when a Claude Code session starts or resumes.

Responsibilities:
1. Show high-level planning reminder
2. Clean up empty claude/* branches
3. Provide session context to user

NOTE: Auto-branch creation is DISABLED. Claude must explicitly create
branches with meaningful names to prevent work accumulation on long-lived
feature branches.

Self-healing: Never blocks session start. All errors emit warnings only.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.git import is_git_repo_root
from shared.hook_utils import format_hook_error, get_hook_data

from session import (
    cleanup_empty_branches,
    create_session_branch,
    report_session_context,
    should_auto_create_branch,
)

# High-level planning database
PLANNING_DB = Path.home() / "Developer" / ".beads" / "beads.db"


def show_planning_reminder() -> None:
    """
    Show reminder about high-level cross-project planning.
    Runs every session to keep planning top of mind.
    """
    if not PLANNING_DB.exists():
        return

    print("📋 Cross-project planning: ~/Developer/synodic-planning", file=sys.stderr)
    print("   Create:  bd --db ~/Developer/.beads/beads.db create \"...\"", file=sys.stderr)
    print("   View:    bd --db ~/Developer/.beads/beads.db ready", file=sys.stderr)
    print("   Link:    bd dep add <local> <Developer-xxx> --type related", file=sys.stderr)


def main():
    """
    Main entry point for SessionStart hook

    Self-healing philosophy:
    - Never exit non-zero (never block session start)
    - All errors emit warnings and continue
    - Graceful degradation on failures
    """
    try:
        # Get hook data
        hook_data = get_hook_data()
        cwd = hook_data.get("cwd", os.getcwd())

        # 1. Show planning reminder (always, regardless of git status)
        show_planning_reminder()

        # Only proceed with git operations if in a git repository
        if not is_git_repo_root(cwd):
            # Not in git repo - done
            sys.exit(0)

        # 2. Clean up empty branches from previous sessions
        cleanup_empty_branches(cwd)

        # 3. Create new session branch if appropriate
        if should_auto_create_branch(cwd):
            create_session_branch(cwd)

        # 4. Report context
        report_session_context(cwd)

        # Always succeed
        sys.exit(0)

    except Exception as e:
        # Ultimate safety net - never block session
        error_msg = format_hook_error("SessionStart", e)
        print(error_msg, file=sys.stderr)
        sys.exit(0)  # Permissive - session continues


if __name__ == "__main__":
    main()
