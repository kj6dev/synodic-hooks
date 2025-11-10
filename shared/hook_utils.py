#!/usr/bin/env python3
"""Hook utility functions for synodic-hooks

Common utilities for Claude Code hooks.
Based on existing ~/.claude/hooks/hook_utils.py patterns.
"""

import json
import subprocess
import sys
from typing import Any, Optional


def get_hook_data() -> dict[str, Any]:
    """
    Read hook data from stdin (JSON format)

    Returns:
        Dictionary containing hook event data
    """
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def get_tool_name(hook_data: dict[str, Any]) -> str:
    """
    Extract tool name from hook data

    Args:
        hook_data: Hook event data

    Returns:
        Tool name (e.g., "Bash", "Edit", "Write")
    """
    return hook_data.get("tool_name", "")


def get_tool_input(hook_data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract tool input parameters from hook data

    Args:
        hook_data: Hook event data

    Returns:
        Tool input dictionary
    """
    return hook_data.get("tool_input", {})


def get_bash_command(hook_data: dict[str, Any]) -> str:
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


def format_hook_error(component: str, error: Exception, context: str = "") -> str:
    """
    Format error with actionable information for LLM self-healing

    Args:
        component: Component name (e.g., "SessionStart", "PreToolUse")
        error: Exception that occurred
        context: Additional context about what was being attempted

    Returns:
        Formatted error message with fix suggestions
    """
    import traceback

    lines = [
        f"🚨 {component} Hook Error: {type(error).__name__}",
        f"Problem: {str(error)}",
    ]

    if context:
        lines.append(f"Context: {context}")

    # Add file location from traceback
    if hasattr(error, '__traceback__'):
        tb = traceback.extract_tb(error.__traceback__)
        if tb:
            frame = tb[-1]
            lines.append(f"File: {frame.filename}:{frame.lineno}")

    # Add type-specific fix suggestions
    if isinstance(error, ImportError):
        module = error.name if hasattr(error, 'name') else 'unknown'
        lines.append(f"Fix: Add 'import {module}' or install package")
    elif isinstance(error, KeyError):
        lines.append(f"Fix: Missing key {str(error)} in hook data structure")
    elif isinstance(error, FileNotFoundError):
        path = error.filename if hasattr(error, 'filename') else 'unknown'
        lines.append(f"Fix: Check path exists: {path}")
    elif isinstance(error, subprocess.CalledProcessError):
        lines.append(f"Fix: Command failed with exit code {error.returncode}")
        lines.append(f"Command: {error.cmd}")
    else:
        lines.append("Fix: Review stack trace below for details")

    # Include full traceback
    lines.append("\nStack trace:")
    lines.append(traceback.format_exc())

    return "\n".join(lines)


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
