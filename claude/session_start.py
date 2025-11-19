#!/usr/bin/env python3
"""
SessionStart Hook for Claude Code

Runs when a Claude Code session starts or resumes.

Responsibilities:
1. Sync CLAUDE.md template to .claude/sessions/ directories
2. Sync .gitattributes rule for session files (collapses in GitHub PRs)
3. Check for uncommitted session files from previous work
4. Clean up empty claude/* branches
5. Provide session context to user

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
    check_uncommitted_session_files,
    cleanup_empty_branches,
    create_session_branch,
    report_session_context,
    should_auto_create_branch,
    sync_gitattributes_rule,
    sync_sessions_claude_md,
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

        # 1. Sync CLAUDE.md template to .claude/sessions/
        sync_sessions_claude_md(cwd)

        # 2. Sync .gitattributes rule for session files
        sync_gitattributes_rule(cwd)

        # 3. Check for uncommitted session files from previous work
        check_uncommitted_session_files(cwd)

        # 4. Clean up empty branches from previous sessions
        cleanup_empty_branches(cwd)

        # 5. Create new session branch if appropriate
        if should_auto_create_branch(cwd):
            create_session_branch(cwd)

        # 6. Report context
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
