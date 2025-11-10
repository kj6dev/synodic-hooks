"""
Shared utilities for Claude Code hooks
Provides common functionality across all hook types
Combines capabilities from shared/hook_utils.py and additional features
"""

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_hook_data() -> Dict[str, Any]:
    """
    Read and parse hook data from stdin

    Returns:
        Dictionary containing hook data, or empty dict if unavailable
    """
    try:
        if not sys.stdin.isatty():
            return json.load(sys.stdin)
        return {}
    except (json.JSONDecodeError, Exception):
        return {}


def get_tool_name(hook_data: Dict[str, Any]) -> str:
    """
    Extract tool name from hook data

    Args:
        hook_data: Parsed hook data dictionary

    Returns:
        Tool name or "Unknown"
    """
    return hook_data.get("tool_name", "Unknown")


def get_tool_input(hook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract tool input parameters from hook data

    Args:
        hook_data: Hook event data

    Returns:
        Tool input dictionary
    """
    return hook_data.get("tool_input", {})


def get_bash_command(hook_data: Dict[str, Any]) -> str:
    """
    Extract bash command from hook data (for Bash tool)

    Args:
        hook_data: Hook event data

    Returns:
        Bash command string, or empty string if not a Bash tool
    """
    if get_tool_name(hook_data) != "Bash":
        return ""

    tool_input = get_tool_input(hook_data)
    return tool_input.get("command", "")


def get_file_paths() -> List[str]:
    """
    Get modified file paths from environment

    Returns:
        List of file path strings
    """
    file_paths = os.environ.get("CLAUDE_FILE_PATHS", "")
    return [f.strip() for f in file_paths.split() if f.strip()]


def get_project_dir() -> Path:
    """
    Get project directory from environment

    Returns:
        Path object for project directory
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir)


def resolve_file_path(file_path: str, project_dir: Path) -> Optional[Path]:
    """
    Resolve file path to absolute path

    Args:
        file_path: Relative or absolute file path
        project_dir: Project root directory

    Returns:
        Resolved Path object or None if file doesn't exist
    """
    path = Path(file_path)
    if path.is_absolute():
        resolved = path
    else:
        resolved = project_dir / path

    return resolved if resolved.exists() else None


def play_sound(sound_path: str, timeout: int = 5) -> bool:
    """
    Play a system sound using afplay (macOS)

    Args:
        sound_path: Path to sound file
        timeout: Maximum seconds to wait

    Returns:
        True if successful, False otherwise
    """
    try:
        subprocess.run(
            ["afplay", sound_path], check=False, capture_output=True, timeout=timeout
        )
        return True
    except Exception as e:
        print(f"⚠️  Failed to play sound: {e}", file=sys.stderr)
        return False


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    timeout: int = 30,
    show_output: bool = True,
) -> bool:
    """
    Run a command and return success status

    Args:
        cmd: Command and arguments as list
        cwd: Working directory (optional)
        timeout: Maximum seconds to wait
        show_output: Whether to print command output

    Returns:
        True if command succeeded (exit 0), False otherwise
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
        )

        if show_output:
            # Show non-empty output
            if result.stdout.strip():
                print(f"  {result.stdout.strip()}")
            if result.stderr.strip() and result.returncode != 0:
                print(f"  ⚠️  {result.stderr.strip()}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        if show_output:
            print(f"  ⚠️  Command timed out: {' '.join(cmd)}")
        return False
    except FileNotFoundError:
        if show_output:
            print(f"  ⚠️  Command not found: {cmd[0]}")
        return False
    except Exception as e:
        if show_output:
            print(f"  ⚠️  Error: {e}")
        return False


def command_exists(command: str) -> bool:
    """
    Check if a command exists in PATH

    Args:
        command: Command name to check

    Returns:
        True if command is available, False otherwise
    """
    result = subprocess.run(["which", command], capture_output=True, check=False)
    return result.returncode == 0


def should_process_tool(tool_name: str, allowed_tools: List[str]) -> bool:
    """
    Check if a tool should be processed by this hook

    Args:
        tool_name: Name of the tool being used
        allowed_tools: List of tool names this hook handles

    Returns:
        True if tool should be processed, False otherwise
    """
    return tool_name in allowed_tools


# System sound paths (macOS)
SOUND_SOSUMI = "/System/Library/Sounds/Sosumi.aiff"
SOUND_GLASS = "/System/Library/Sounds/Glass.aiff"
SOUND_PING = "/System/Library/Sounds/Ping.aiff"
SOUND_PURR = "/System/Library/Sounds/Purr.aiff"
SOUND_TINK = "/System/Library/Sounds/Tink.aiff"

# Tool categories
EDIT_TOOLS = ["Edit", "MultiEdit", "Write", "NotebookEdit"]
READ_TOOLS = ["Read", "Glob", "Grep"]
BASH_TOOLS = ["Bash"]
ALL_TOOLS = EDIT_TOOLS + READ_TOOLS + BASH_TOOLS


def format_hook_error(hook_name: str, error: Exception, context: str = "") -> str:
    """
    Format a hook error with actionable information for the LLM

    Args:
        hook_name: Name of the hook that failed
        error: The exception that occurred
        context: Additional context about what was being done

    Returns:
        Formatted error message string
    """
    error_lines = [
        f"🚨 Hook Error: {hook_name}",
        f"Problem: {type(error).__name__}: {str(error)}",
    ]

    if context:
        error_lines.append(f"Context: {context}")

    # Add file location if it's an ImportError or similar
    if hasattr(error, "__traceback__"):
        tb = traceback.extract_tb(error.__traceback__)
        if tb:
            last_frame = tb[-1]
            error_lines.append(f"File: {last_frame.filename}:{last_frame.lineno}")

    # Add actionable fix suggestions based on error type
    if isinstance(error, ImportError):
        error_lines.append(
            f"Fix: Check imports in the hook file - missing module: {error.name if hasattr(error, 'name') else 'unknown'}"
        )
    elif isinstance(error, KeyError):
        error_lines.append(f"Fix: Missing expected key in hook data: {str(error)}")
    elif isinstance(error, FileNotFoundError):
        error_lines.append(
            f"Fix: File not found - check path: {error.filename if hasattr(error, 'filename') else 'unknown'}"
        )
    elif isinstance(error, AttributeError):
        error_lines.append(f"Fix: Check object attributes - {str(error)}")
    elif isinstance(error, subprocess.CalledProcessError):
        error_lines.append(f"Fix: Command failed with exit code {error.returncode}")
        error_lines.append(f"Command: {error.cmd}")
    else:
        error_lines.append("Fix: Review stack trace below for details")

    # Add stack trace
    error_lines.append("\nStack trace:")
    error_lines.append(traceback.format_exc())

    return "\n".join(error_lines)


def emit_warning(message: str) -> None:
    """
    Emit a warning to stderr (visible to user and Claude)

    Args:
        message: Warning message to display
    """
    print(f"⚠️  {message}", file=sys.stderr)


def emit_error(message: str) -> None:
    """
    Emit an error to stderr

    Args:
        message: Error message to display
    """
    print(f"🚨 {message}", file=sys.stderr)


def emit_success(message: str) -> None:
    """
    Emit a success message to stderr

    Args:
        message: Success message to display
    """
    print(f"✅ {message}", file=sys.stderr)


def emit_info(message: str) -> None:
    """
    Emit an info message to stderr

    Args:
        message: Info message to display
    """
    print(f"💡 {message}", file=sys.stderr)
