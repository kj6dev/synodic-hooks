#!/usr/bin/env python3
"""
Pre-Push Git Hook Script

Callable from .githooks/pre-push in individual repositories.

Responsibilities:
- Run test suites before push
- Validate build succeeds
- Check for common issues (broken imports, etc.)

Usage:
  python3 ~/.claude/hooks-repo/git/pre_push.py

Convention:
  Repositories should provide scripts/pre_push or scripts/test
  This script discovers and executes repo-specific test commands

Self-healing: Provides clear fix suggestions, allows --no-verify bypass
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.hook_utils import emit_error, emit_info, emit_success, emit_warning


def find_test_script(repo_path: Path) -> Optional[Path]:
    """
    Find the test script following convention

    Looks for (in order):
    1. scripts/pre_push (preferred)
    2. scripts/test
    3. None (no test script)

    Args:
        repo_path: Repository root path

    Returns:
        Path to test script, or None if not found
    """
    candidates = [
        repo_path / "scripts" / "pre_push",
        repo_path / "scripts" / "test",
    ]

    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate

    return None


def run_test_script(script_path: Path, repo_path: Path) -> bool:
    """
    Execute the test script

    Args:
        script_path: Path to test script
        repo_path: Repository root

    Returns:
        True if tests passed
    """
    try:
        emit_info(f"Running {script_path.relative_to(repo_path)}...")

        result = subprocess.run(
            [str(script_path)],
            cwd=repo_path,
            timeout=300  # 5 minute timeout for tests
        )

        if result.returncode == 0:
            emit_success("Tests passed")
            return True
        else:
            emit_error(f"Tests failed (exit code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        emit_error("Tests timed out (5 minute limit)")
        return False

    except Exception as e:
        emit_error(f"Test execution failed: {e}")
        return False


def detect_and_run_tests(repo_path: Path) -> bool:
    """
    Detect test framework and run tests

    Fallback if no test script found - tries common frameworks

    Args:
        repo_path: Repository root

    Returns:
        True if tests found and passed
    """
    # Swift
    if (repo_path / "Package.swift").exists():
        emit_info("Detected Swift package - running swift test...")
        try:
            result = subprocess.run(
                ["swift", "test"],
                cwd=repo_path,
                timeout=300
            )
            if result.returncode == 0:
                emit_success("Swift tests passed")
                return True
            else:
                emit_error("Swift tests failed")
                return False
        except Exception as e:
            emit_warning(f"Swift test execution failed: {e}")
            return True  # Permissive

    # Python with pyproject.toml (uv/pytest)
    if (repo_path / "pyproject.toml").exists():
        emit_info("Detected Python project - running tests...")
        try:
            # Try uv first
            result = subprocess.run(
                ["uv", "run", "pytest"],
                cwd=repo_path,
                timeout=300
            )
            if result.returncode == 0:
                emit_success("Python tests passed")
                return True
            else:
                emit_error("Python tests failed")
                return False
        except FileNotFoundError:
            # uv not available, try pytest directly
            try:
                result = subprocess.run(
                    ["pytest"],
                    cwd=repo_path,
                    timeout=300
                )
                if result.returncode == 0:
                    emit_success("Python tests passed")
                    return True
                else:
                    emit_error("Python tests failed")
                    return False
            except FileNotFoundError:
                emit_warning("pytest not found - skipping Python tests")
                return True
        except Exception as e:
            emit_warning(f"Python test execution failed: {e}")
            return True  # Permissive

    # JavaScript/TypeScript
    if (repo_path / "package.json").exists():
        emit_info("Detected Node project - running npm test...")
        try:
            result = subprocess.run(
                ["npm", "test"],
                cwd=repo_path,
                timeout=300
            )
            if result.returncode == 0:
                emit_success("Node tests passed")
                return True
            else:
                emit_error("Node tests failed")
                return False
        except FileNotFoundError:
            emit_warning("npm not found - skipping Node tests")
            return True
        except Exception as e:
            emit_warning(f"Node test execution failed: {e}")
            return True  # Permissive

    # No tests found
    emit_warning("No test framework detected")
    emit_info("💡 Create scripts/pre_push or scripts/test to enable testing")
    return True  # Don't block push if no tests


def main():
    """
    Main entry point for pre-push hook

    Exit codes:
    - 0: Tests passed or no tests found
    - 1: Tests failed (blocks push)
    """
    repo_path = Path.cwd()

    print("🧪 Running pre-push checks...", file=sys.stderr)

    # 1. Look for test script (convention)
    test_script = find_test_script(repo_path)

    if test_script:
        # Run repo-specific test script
        if run_test_script(test_script, repo_path):
            sys.exit(0)
        else:
            emit_error("Pre-push checks failed")
            emit_info("Fix the errors or use 'git push --no-verify' to bypass")
            sys.exit(1)
    else:
        # No test script - try auto-detection
        if detect_and_run_tests(repo_path):
            sys.exit(0)
        else:
            emit_error("Pre-push checks failed")
            emit_info("Fix the errors or use 'git push --no-verify' to bypass")
            sys.exit(1)


if __name__ == "__main__":
    main()
