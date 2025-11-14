#!/usr/bin/env python3
"""
PostToolUse Hook for Claude Code
Routes file edits to appropriate formatters based on file type
"""

import os
import sys
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

    Creates session-specific counter and shows hint once after 5 Swift edits.
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

        # Show hint once after 5 edits
        if count == 5:
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
