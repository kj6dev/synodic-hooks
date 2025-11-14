"""
Swift formatter using smart formatting tools
Handles .swift files with swiftformat-smart, swiftlint-smart, swiftlintcustom-smart
"""

import subprocess
import sys
from pathlib import Path

# Import parent hook_utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from claude.hook_utils import emit_error, emit_success, emit_warning

# Register this formatter
from . import register_formatter

# Path to swift-quality-tools binaries
SWIFT_TOOLS_PATH = Path.home() / "Developer" / "swift-quality-tools" / ".build" / "release"


def run_lint_tool(tool_name: str, tool_path: Path, file_path: Path, project_dir: Path) -> bool:
    """
    Run a Swift lint/format tool and report violations as ERRORS

    Args:
        tool_name: Display name of the tool
        tool_path: Path to tool binary
        file_path: Path to Swift file
        project_dir: Project root directory

    Returns:
        True if tool passed (exit 0), False if violations found
    """
    if not tool_path.exists():
        emit_warning(f"{tool_name} not found at {tool_path}")
        return True  # Don't fail on missing tools

    try:
        result = subprocess.run(
            [str(tool_path), str(file_path)],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            emit_success(f"{tool_name} passed")
            return True
        else:
            # Violations found - treat as ERRORS
            emit_error(f"LINT VIOLATIONS in {file_path.name} - {tool_name}")
            emit_error("=" * 60)

            # Print all output as errors
            if result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    emit_error(line)

            if result.stderr.strip():
                for line in result.stderr.strip().split("\n"):
                    emit_error(line)

            emit_error("=" * 60)
            emit_error(f"FIX THESE {tool_name} VIOLATIONS BEFORE PROCEEDING")
            return False

    except subprocess.TimeoutExpired:
        emit_error(f"{tool_name} timed out after 30 seconds")
        return False
    except Exception as e:
        emit_error(f"{tool_name} failed: {e}")
        return False


def format_swift(file_path: Path, project_dir: Path) -> bool:
    """
    Format Swift file using smart formatting tools

    These smart commands automatically discover project-specific configs:
    - swiftformat-smart: Finds .swiftformat config
    - swiftlint-smart: Finds .swiftlint.yml config
    - swiftlintcustom-smart: Runs custom SwiftSyntax rules

    All violations are reported as ERRORS to ensure Claude's attention.

    Args:
        file_path: Path to Swift file
        project_dir: Project root directory

    Returns:
        True if successful, False otherwise
    """
    print(f"🔶 Swift Quality Checks: {file_path.name}")

    has_violations = False

    # SwiftFormat
    swiftformat_bin = SWIFT_TOOLS_PATH / "swiftformat-smart"
    if not run_lint_tool("SwiftFormat", swiftformat_bin, file_path, project_dir):
        has_violations = True

    # SwiftLint
    swiftlint_bin = SWIFT_TOOLS_PATH / "swiftlint-smart"
    if not run_lint_tool("SwiftLint", swiftlint_bin, file_path, project_dir):
        has_violations = True

    # Custom SwiftLint rules (SwiftSyntax)
    swiftlintcustom_bin = SWIFT_TOOLS_PATH / "swiftlintcustom-smart"
    if not run_lint_tool("SwiftLintCustom", swiftlintcustom_bin, file_path, project_dir):
        has_violations = True

    if has_violations:
        emit_error(f"❌ {file_path.name} has quality violations - MUST BE FIXED")
        return False

    return True


# Register for Swift files
register_formatter([".swift"], format_swift)
