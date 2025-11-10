"""
Python formatter using uv + ruff
Handles .py files
"""

import sys
from pathlib import Path

# Import parent hook_utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from hook_utils import run_command, command_exists

# Register this formatter
from . import register_formatter


def format_python(file_path: Path, project_dir: Path) -> bool:
    """
    Format Python file using uv + ruff

    Args:
        file_path: Path to Python file
        project_dir: Project root directory

    Returns:
        True if successful, False otherwise
    """
    print(f"🐍 Python: {file_path.name}")

    if not command_exists("uv"):
        print("  ⚠️  Warning: uv not found, skipping Python checks")
        return True

    # Run ruff check with auto-fix
    success = run_command(
        ["uv", "run", "ruff", "check", "--fix", str(file_path)],
        cwd=project_dir
    )
    if success:
        print("  ✓ Ruff check passed")

    # Run ruff format
    success = run_command(
        ["uv", "run", "ruff", "format", str(file_path)],
        cwd=project_dir
    )
    if success:
        print("  ✓ Ruff format passed")

    return True


# Register for Python files
register_formatter([".py", ".pyx"], format_python)
