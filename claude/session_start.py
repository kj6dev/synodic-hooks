#!/usr/bin/env python3
"""
SessionStart Hook for Claude Code

Runs when a Claude Code session starts or resumes.

Responsibilities:
1. Auto-create timestamped claude/* branches (if at repo root)
2. Clean up empty claude/* branches
3. Provide session context to user

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

        # Only proceed if in a git repository
        if not is_git_repo_root(cwd):
            # Not in git repo - nothing to do
            sys.exit(0)

        # 1. Clean up empty branches from previous sessions
        cleanup_empty_branches(cwd)

        # 2. Create new session branch if appropriate
        if should_auto_create_branch(cwd):
            create_session_branch(cwd)

        # 3. Report context
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
