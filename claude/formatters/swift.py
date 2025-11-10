"""
Swift formatter using smart formatting tools
Handles .swift files with swiftformat-smart, swiftlint-smart, swiftlintcustom-smart
"""

import sys
from pathlib import Path

# Import parent hook_utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from hook_utils import run_command

# Register this formatter
from . import register_formatter

# Path to swift-quality-tools binaries
SWIFT_TOOLS_PATH = Path.home() / "Developer" / "swift-quality-tools" / ".build" / "release"


def format_swift(file_path: Path, project_dir: Path) -> bool:
    """
    Format Swift file using smart formatting tools

    These smart commands automatically discover project-specific configs:
    - swiftformat-smart: Finds .swiftformat config
    - swiftlint-smart: Finds .swiftlint.yml config
    - swiftlintcustom-smart: Runs custom SwiftSyntax rules

    Args:
        file_path: Path to Swift file
        project_dir: Project root directory

    Returns:
        True if successful, False otherwise
    """
    print(f"🔶 Swift: {file_path.name}")

    # SwiftFormat
    swiftformat_bin = SWIFT_TOOLS_PATH / "swiftformat-smart"
    if swiftformat_bin.exists():
        success = run_command(
            [str(swiftformat_bin), str(file_path)],
            cwd=project_dir
        )
        if success:
            print("  ✓ SwiftFormat passed")
    else:
        print("  ⚠️  Warning: swiftformat-smart not found at", swiftformat_bin)

    # SwiftLint
    swiftlint_bin = SWIFT_TOOLS_PATH / "swiftlint-smart"
    if swiftlint_bin.exists():
        success = run_command(
            [str(swiftlint_bin), str(file_path)],
            cwd=project_dir
        )
        if success:
            print("  ✓ SwiftLint passed")
    else:
        print("  ⚠️  Warning: swiftlint-smart not found at", swiftlint_bin)

    # Custom SwiftLint rules (SwiftSyntax)
    swiftlintcustom_bin = SWIFT_TOOLS_PATH / "swiftlintcustom-smart"
    if swiftlintcustom_bin.exists():
        success = run_command(
            [str(swiftlintcustom_bin), str(file_path)],
            cwd=project_dir
        )
        if success:
            print("  ✓ Custom SwiftLint passed")
    else:
        print("  ⚠️  Warning: swiftlintcustom-smart not found at", swiftlintcustom_bin)

    return True


# Register for Swift files
register_formatter([".swift"], format_swift)
