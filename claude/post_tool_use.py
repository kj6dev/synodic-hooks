#!/usr/bin/env python3
"""
PostToolUse Hook for Claude Code
Routes file edits to appropriate formatters based on file type
"""

import os
import re
import sys
from pathlib import Path

# Add directories to path for imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent))  # claude/ for hook_utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # root for formatters

from hook_utils import (
    emit_warning,
    format_hook_error,
    get_file_paths,
    get_hook_data,
    get_project_dir,
    get_tool_input,
    get_tool_name,
    resolve_file_path,
    should_process_tool,
    EDIT_TOOLS,
)

# Import formatter registry
from formatters import get_formatter

# Pattern to match Swift disable directives
# Matches: swiftlint:disable, swiftformat:disable, swiftlint:disable:next, etc.
SWIFT_DISABLE_PATTERN = re.compile(r"swift\w*:disable[ :]", re.IGNORECASE)


def check_swift_disable_directive(hook_data: dict) -> None:
    """
    Check if an Edit added a SwiftLint/SwiftFormat disable directive

    Emits a warning to remind Claude to:
    - Have explicit user approval, OR
    - Include justification in a comment

    This is a warning only - does not block the edit.

    Args:
        hook_data: Hook event data
    """
    tool_name = get_tool_name(hook_data)
    if tool_name != "Edit":
        return

    tool_input = get_tool_input(hook_data)
    file_path = tool_input.get("file_path", "")
    new_string = tool_input.get("new_string", "")
    old_string = tool_input.get("old_string", "")

    # Only check Swift files
    if not file_path.lower().endswith(".swift"):
        return

    # Check if adding a new disable directive (not already present in old_string)
    new_has_disable = SWIFT_DISABLE_PATTERN.search(new_string)
    old_has_disable = SWIFT_DISABLE_PATTERN.search(old_string)

    # Only warn if this edit is ADDING a disable directive
    if new_has_disable and not old_has_disable:
        # Find the actual directive for context
        match = SWIFT_DISABLE_PATTERN.search(new_string)
        directive_context = (
            new_string[match.start() : match.start() + 50] if match else ""
        )

        emit_warning("=" * 60)
        emit_warning("Adding Swift lint/format disable directive")
        emit_warning(f"File: {file_path}")
        emit_warning(f"Directive: {directive_context}...")
        emit_warning("")
        emit_warning("Before proceeding, ensure ONE of:")
        emit_warning("  1. User explicitly approved this disable directive")
        emit_warning("  2. A justification comment explains WHY it's needed")
        emit_warning("")
        emit_warning("Example: // swiftlint:disable:next rule_name - [explain why]")
        emit_warning("=" * 60)


def get_repo_root(file_path: Path) -> Path | None:
    """Find git repository root for a file path"""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "-C", str(file_path.parent), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_repo_tracker_file(repo_root: Path) -> Path:
    """Get tracker file path for a repository (using hash of repo path)"""
    import hashlib

    repo_hash = hashlib.md5(str(repo_root).encode()).hexdigest()[:12]
    return Path.home() / ".claude" / f"recent-edits-{repo_hash}.txt"


def track_edited_file(file_path: Path) -> None:
    """
    Track edited files for status line display (repo-scoped)

    Maintains a rolling list of the last 10 edited files per repository.
    Status line can read this to show the most recently edited files.
    """
    try:
        # Find repo root for this file
        repo_root = get_repo_root(file_path)
        if repo_root is None:
            return  # Not in a git repo, skip tracking

        tracker_file = get_repo_tracker_file(repo_root)

        # Read existing files (keep last 10)
        existing_files = []
        if tracker_file.exists():
            existing_files = [
                line.strip()
                for line in tracker_file.read_text().splitlines()
                if line.strip()
            ]

        # Remove this file if it already exists (to move it to top)
        file_str = str(file_path.resolve())
        existing_files = [f for f in existing_files if f != file_str]

        # Add new file to top
        existing_files.insert(0, file_str)

        # Keep only last 10 files
        existing_files = existing_files[:10]

        # Write back
        tracker_file.parent.mkdir(parents=True, exist_ok=True)
        tracker_file.write_text("\n".join(existing_files) + "\n")

    except (OSError, Exception):
        # Silently fail - this is just for status line display
        pass


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


def main():
    """Main entry point for PostToolUse hook"""
    try:
        # Read hook data
        hook_data = get_hook_data()
        tool_name = get_tool_name(hook_data)

        # Check for Swift disable directives (warning only, non-blocking)
        check_swift_disable_directive(hook_data)

        # Don't process Bash commands for formatting
        if tool_name == "Bash":
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
                # Track this edit for status line display
                track_edited_file(file_path)

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
