"""
JSON/YAML formatter and validator
Handles .json, .yaml, .yml files
"""

import json
import sys
from pathlib import Path

# Import parent hook_utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from claude.hook_utils import run_command, command_exists

# Register this formatter
from . import register_formatter


def format_json(file_path: Path, project_dir: Path) -> bool:
    """
    Validate and format JSON files

    Args:
        file_path: Path to JSON file
        project_dir: Project root directory

    Returns:
        True if successful, False otherwise
    """
    print(f"📋 JSON: {file_path.name}")

    try:
        # Read and parse JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            data = json.loads(content)

        # Re-serialize with consistent formatting
        formatted = json.dumps(data, indent=2, ensure_ascii=False)

        # Add trailing newline if not present
        if not formatted.endswith('\n'):
            formatted += '\n'

        # Only write if changed
        if content != formatted:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted)
            print("  ✓ JSON formatted (2-space indent)")
        else:
            print("  ✓ JSON valid (no changes needed)")

        return True

    except json.JSONDecodeError as e:
        print(f"  ❌ JSON validation failed: {e}")
        return False
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
        return False


def format_yaml(file_path: Path, project_dir: Path) -> bool:
    """
    Validate YAML files (and optionally format if prettier available)

    Args:
        file_path: Path to YAML file
        project_dir: Project root directory

    Returns:
        True if successful, False otherwise
    """
    print(f"📋 YAML: {file_path.name}")

    # Try PyYAML validation if available
    try:
        import yaml
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        print("  ✓ YAML valid")
    except ImportError:
        # PyYAML not available, skip validation
        print("  ⚠️  PyYAML not installed, skipping validation")
    except yaml.YAMLError as e:
        print(f"  ❌ YAML validation failed: {e}")
        return False
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
        return False

    # Try prettier formatting if available (Node project)
    package_json = project_dir / "package.json"
    if package_json.exists() and command_exists("npx"):
        success = run_command(
            ["npx", "prettier", "--write", str(file_path)],
            cwd=project_dir,
            show_output=False
        )
        if success:
            print("  ✓ Prettier formatted")

    return True


# Register for JSON files
register_formatter([".json", ".jsonc", ".json5"], format_json)

# Register for YAML files
register_formatter([".yaml", ".yml"], format_yaml)
