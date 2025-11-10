#!/usr/bin/env python3
"""
PreToolUse Hook for Claude Code

Runs before Claude executes any tool.

Responsibilities:
1. Detect git commit operations
2. Enforce branch protection (only allow commits to claude/* branches)
3. Validate commit operations

Self-healing: Blocks dangerous operations but provides clear guidance
"""

import re
import shlex
import sys
from pathlib import Path

# Add parent directory to path for imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.git import get_current_branch, is_claude_branch
from shared.hook_utils import (
    emit_error,
    emit_info,
    format_hook_error,
    get_bash_command,
    get_hook_data,
    get_tool_name,
)


def is_git_commit_command(command: str) -> bool:
    """
    Detect if a bash command is a git commit operation

    Handles various git commit formats:
    - git commit -m "message"
    - git commit --amend
    - git -C /path commit
    - git --no-pager commit

    Args:
        command: Bash command string

    Returns:
        True if this is a git commit operation
    """
    try:
        # Parse command into tokens (handles quotes properly)
        tokens = shlex.split(command)
    except ValueError:
        # Unparseable command - use regex fallback
        return bool(re.search(r'\bgit\b.*\bcommit\b', command))

    if len(tokens) < 2:
        return False

    # First token should be git (or path/to/git)
    if not tokens[0].endswith("git"):
        return False

    # Find first non-flag token after 'git'
    # This handles: git -C /path commit, git --no-pager commit, etc.
    skip_next = False
    for token in tokens[1:]:
        if skip_next:
            skip_next = False
            continue
        if token.startswith("-"):
            # Flags like -C take an argument, so skip next token
            if token in ["-C", "-c", "--git-dir", "--work-tree"]:
                skip_next = True
            continue  # Skip flags
        # First non-flag token should be "commit"
        return token == "commit"

    return False


def validate_git_commit(command: str, cwd: str) -> tuple[bool, str]:
    """
    Validate git commit operation

    Enforces:
    - Can only commit to claude/* branches
    - Current branch must start with claude/

    Args:
        command: Git commit command
        cwd: Current working directory

    Returns:
        Tuple of (allowed, reason)
        - allowed: True if commit should proceed
        - reason: Explanation for decision
    """
    try:
        # Get current branch
        current_branch = get_current_branch(cwd)

        if not current_branch:
            return False, "Not in a git repository or detached HEAD state"

        # Check if on claude/* branch
        if not is_claude_branch(current_branch, cwd):
            reason = (
                f"🚨 Commits only allowed on claude/* branches!\n"
                f"\n"
                f"Current branch: {current_branch}\n"
                f"\n"
                f"📋 Create a claude/* branch:\n"
                f"   git checkout -b claude/$(date -Iseconds | tr -d ':-')-feature-name\n"
                f"\n"
                f"Or I can create one for you - just ask!"
            )
            return False, reason

        # On claude/* branch - allow commit
        return True, f"✅ Committing to safe branch: {current_branch}"

    except Exception as e:
        # On error, be permissive but warn
        return True, f"⚠️ Could not validate branch: {e}"


def validate_bash_command(hook_data: dict) -> bool:
    """
    Validate bash commands before execution

    Currently validates:
    - Git commit operations (must be on claude/* branch)

    Args:
        hook_data: Hook event data

    Returns:
        True if command should proceed, False to block
    """
    command = get_bash_command(hook_data)
    if not command:
        return True  # Not a Bash command

    cwd = hook_data.get("cwd", ".")

    # Check for git commit
    if is_git_commit_command(command):
        allowed, reason = validate_git_commit(command, cwd)

        if not allowed:
            emit_error(reason)
            return False
        else:
            # Log that commit is allowed
            print(reason, file=sys.stderr)
            return True

    # Other bash commands - allow
    return True


def main():
    """
    Main entry point for PreToolUse hook

    Exit codes:
    - 0: Allow operation
    - 2: Block operation (stderr shown to Claude)
    - 1: Non-blocking error

    Self-healing:
    - Blocks dangerous operations (commits to wrong branch)
    - Provides clear instructions for fixing
    - Permissive on errors (fail open)
    """
    try:
        hook_data = get_hook_data()
        tool_name = get_tool_name(hook_data)

        # Only validate Bash commands
        if tool_name == "Bash":
            allowed = validate_bash_command(hook_data)
            sys.exit(0 if allowed else 2)
        else:
            # Other tools - allow
            sys.exit(0)

    except Exception as e:
        # Self-healing: On unexpected error, allow operation but warn
        error_msg = format_hook_error("PreToolUse", e)
        print(error_msg, file=sys.stderr)
        emit_info("Allowing operation due to hook error")
        sys.exit(0)  # Permissive


if __name__ == "__main__":
    main()
