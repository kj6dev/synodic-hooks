#!/usr/bin/env python3
"""
PostToolUse Hook for Claude Code
Routes file edits to appropriate formatters based on file type
Tracks git commits for session metadata (Phase 4)
"""

import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add directories to path for imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent))  # claude/ for hook_utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # root for formatters

from hook_utils import (
    get_hook_data,
    get_tool_name,
    get_file_paths,
    get_project_dir,
    resolve_file_path,
    should_process_tool,
    format_hook_error,
    EDIT_TOOLS,
)

# Import formatter registry
from formatters import get_formatter


def track_swift_edits_and_suggest_batching(file_path: Path) -> None:
    """
    Track Swift file edits and suggest batch editing after threshold

    Creates session-specific counter and shows hint once after 3 Swift edits.
    This helps Claude optimize workflow when fixing many violations.
    """
    if not file_path.suffix == ".swift":
        return

    # Get session ID from environment (set by Claude Code)
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")
    counter_file = Path.home() / f".claude-swift-edits-{session_id}.count"

    try:
        # Read current count
        count = 0
        if counter_file.exists():
            count = int(counter_file.read_text().strip())

        count += 1

        # Write updated count
        counter_file.write_text(str(count))

        # Show hint once after 3 edits
        if count == 3:
            print()
            print("💡 Performance Tip: Consider batch editing for similar changes")
            print(
                "   Hooks run after every Edit - batching multiple files into one Edit"
            )
            print("   operation reduces hook overhead significantly.")
            print()
            print("   Example: Instead of editing 10 files individually,")
            print('   ask me to "batch edit all files to fix trailing whitespace"')
            print()

    except (ValueError, OSError):
        # Silently fail - this is just a helpful hint
        pass


def process_file(file_path: Path, project_dir: Path) -> bool:
    """
    Process a file using its registered formatter

    Args:
        file_path: Path to file
        project_dir: Project root directory

    Returns:
        True if successful, False otherwise
    """
    # Get formatter for this file type
    formatter = get_formatter(file_path)

    if formatter is None:
        # No formatter registered for this file type - skip silently
        return True

    try:
        return formatter(file_path, project_dir)
    except Exception as e:
        print(f"  ⚠️  Formatter error: {e}")
        return False


def is_git_commit_command(command: str) -> bool:
    """
    Detect if a bash command is a git commit operation

    Handles chained commands (e.g., "git add -A && git commit -m 'msg'")
    and complex shell syntax.

    Args:
        command: Bash command string

    Returns:
        True if this is a git commit operation
    """
    # Use regex to detect git commit in command (handles chained commands)
    return bool(re.search(r"\bgit\b.*\bcommit\b", command))


def find_git_root(cwd: str) -> Path | None:
    """
    Find the git repository root

    Args:
        cwd: Current working directory

    Returns:
        Path to git root, or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass

    return None


def record_commit_to_session(cwd: str) -> None:
    """
    Record the latest commit to the current session file

    Called after a git commit command succeeds.
    Appends commit metadata to the session file.

    Args:
        cwd: Current working directory (repo)
    """
    try:
        # Find git root
        git_root = find_git_root(cwd)
        if not git_root:
            return

        # Check if session file exists
        claude_dir = git_root / ".claude"
        current_session_file = claude_dir / "current_session"

        if not current_session_file.exists():
            return  # No active session

        # Read session ID
        session_id = current_session_file.read_text().strip()

        # Get session file
        session_filename = session_id.replace("claude-", "") + ".yml"
        session_file = claude_dir / "sessions" / session_filename

        if not session_file.exists():
            return  # Session file doesn't exist

        # Get latest commit info
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H%n%s%n%ai"],
            capture_output=True,
            text=True,
            cwd=str(git_root),
            timeout=5,
        )

        if result.returncode != 0:
            return  # Couldn't get commit info

        lines = result.stdout.strip().split("\n")
        if len(lines) < 3:
            return

        commit_sha = lines[0]
        commit_message = lines[1]
        commit_time = lines[2]

        # Append commit record to session file
        with session_file.open("a") as f:
            f.write("---\n")
            f.write(f"# Commit {commit_sha[:8]}\n")
            f.write(f"commit_sha: {commit_sha}\n")
            f.write(f"commit_time: {commit_time}\n")
            f.write("commit_message: |\n")
            for line in commit_message.splitlines():
                f.write(f"  {line}\n")
            f.write("\n")

    except Exception:
        # Silent failure - don't block workflow
        pass


def main():
    """Main entry point for PostToolUse hook"""
    try:
        # Read hook data
        hook_data = get_hook_data()
        tool_name = get_tool_name(hook_data)

        # Handle git commit tracking (Phase 4)
        if tool_name == "Bash":
            tool_input = hook_data.get("tool_input", {})
            command = tool_input.get("command", "")
            cwd = hook_data.get("cwd", ".")

            if is_git_commit_command(command):
                record_commit_to_session(cwd)

            # Don't process Bash commands for formatting
            sys.exit(0)

        # Only process file edit operations
        if not should_process_tool(tool_name, EDIT_TOOLS):
            sys.exit(0)

        # Get files to process
        file_paths = get_file_paths(hook_data)
        if not file_paths:
            sys.exit(0)

        print("🔧 Running quality checks on modified files...")

        # Get project directory
        project_dir = get_project_dir()

        # Process each file
        all_success = True
        for file_path_str in file_paths:
            file_path = resolve_file_path(file_path_str, project_dir)

            if file_path is None:
                print(f"⚠️  Warning: File not found: {file_path_str}")
                continue

            try:
                # Track Swift edits and suggest batching if appropriate
                track_swift_edits_and_suggest_batching(file_path)

                success = process_file(file_path, project_dir)
                all_success = all_success and success
            except Exception as e:
                print(f"⚠️  Error processing {file_path}: {e}")
                all_success = False

        print("✅ Quality checks complete")

        # Permissive mode: always exit 0 (warn but don't fail)
        sys.exit(0)

    except Exception as e:
        error_msg = format_hook_error(
            "PostToolUse",
            e,
            f"Processing files for tool: {tool_name if 'tool_name' in locals() else 'unknown'}",
        )
        print(error_msg, file=sys.stderr)
        # Exit 0 to avoid blocking workflow
        sys.exit(0)


if __name__ == "__main__":
    main()
