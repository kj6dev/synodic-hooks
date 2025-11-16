"""
TypeScript/JavaScript formatter using prettier
Handles .ts, .tsx, .js, .jsx files
"""

import sys
from pathlib import Path

# Import parent hook_utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from claude.hook_utils import run_command, command_exists

# Register this formatter
from . import register_formatter


def format_typescript(file_path: Path, project_dir: Path) -> bool:
    """
    Format TypeScript/JavaScript file using prettier

    Only runs if project has package.json (Node project)

    Args:
        file_path: Path to TypeScript/JavaScript file
        project_dir: Project root directory

    Returns:
        True if successful, False otherwise
    """
    print(f"📘 TypeScript/JavaScript: {file_path.name}")

    # Check if this is a Node project
    package_json = project_dir / "package.json"
    if not package_json.exists():
        # Not a Node project, skip silently
        return True

    if not command_exists("npx"):
        print("  ⚠️  Warning: npx not found")
        return True

    # Run prettier
    success = run_command(
        ["npx", "prettier", "--write", str(file_path)],
        cwd=project_dir
    )
    if success:
        print("  ✓ Prettier passed")

    return True


# Register for TypeScript and JavaScript files
register_formatter([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"], format_typescript)
