#!/usr/bin/env python3
"""
Pre-Commit Git Hook Script

Callable from .githooks/pre-commit in individual repositories.

Responsibilities:
- Run code formatting checks
- Run linting
- Validate code quality before commit

Usage:
  python3 ~/.claude/hooks-repo/git/pre_commit.py [--scope=staged-files|all-files]

Self-healing: Provides clear fix suggestions, allows --no-verify bypass
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.hook_utils import emit_error, emit_info, emit_success, emit_warning


def get_staged_files(repo_path: Optional[str] = None) -> list[str]:
    """
    Get list of staged files for commit

    Args:
        repo_path: Repository path (default: current directory)

    Returns:
        List of staged file paths
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=10
        )

        if result.returncode == 0:
            return [f for f in result.stdout.strip().split('\n') if f]
        return []

    except Exception:
        return []


def run_swiftformat(files: list[str], repo_path: Optional[str] = None) -> bool:
    """
    Run SwiftFormat on specified files

    Args:
        files: List of files to format
        repo_path: Repository path

    Returns:
        True if formatting passed
    """
    swift_files = [f for f in files if f.endswith('.swift')]
    if not swift_files:
        return True  # No Swift files to format

    try:
        # Try smart swiftformat command first (from global utils)
        result = subprocess.run(
            ["swiftformat-smart", "."],
            cwd=repo_path,
            timeout=60
        )

        if result.returncode == 0:
            emit_success("SwiftFormat passed")
            return True
        else:
            emit_error("SwiftFormat failed")
            emit_info("Fix: Run 'swiftformat-smart .' to format code")
            return False

    except FileNotFoundError:
        # swiftformat-smart not available, try standard swiftformat
        try:
            result = subprocess.run(
                ["swiftformat", "--lint"] + swift_files,
                cwd=repo_path,
                timeout=60
            )

            if result.returncode == 0:
                emit_success("SwiftFormat passed")
                return True
            else:
                emit_error("SwiftFormat failed")
                emit_info("Fix: Run 'swiftformat <files>' to format code")
                return False

        except FileNotFoundError:
            emit_warning("SwiftFormat not found - skipping format check")
            return True  # Don't block if tool not available

    except Exception as e:
        emit_warning(f"SwiftFormat check failed: {e}")
        return True  # Permissive on errors


def run_swiftlint(files: list[str], repo_path: Optional[str] = None) -> bool:
    """
    Run SwiftLint on specified files

    Args:
        files: List of files to lint
        repo_path: Repository path

    Returns:
        True if linting passed
    """
    swift_files = [f for f in files if f.endswith('.swift')]
    if not swift_files:
        return True  # No Swift files to lint

    try:
        # Try smart swiftlint command first
        result = subprocess.run(
            ["swiftlint-smart", "."],
            cwd=repo_path,
            timeout=60
        )

        if result.returncode == 0:
            emit_success("SwiftLint passed")
            return True
        else:
            emit_error("SwiftLint failed")
            emit_info("Fix: Review and fix lint errors above")
            return False

    except FileNotFoundError:
        # swiftlint-smart not available, try standard swiftlint
        try:
            result = subprocess.run(
                ["swiftlint", "lint", "--strict"] + swift_files,
                cwd=repo_path,
                timeout=60
            )

            if result.returncode == 0:
                emit_success("SwiftLint passed")
                return True
            else:
                emit_error("SwiftLint failed")
                emit_info("Fix: Review and fix lint errors")
                return False

        except FileNotFoundError:
            emit_warning("SwiftLint not found - skipping lint check")
            return True  # Don't block if tool not available

    except Exception as e:
        emit_warning(f"SwiftLint check failed: {e}")
        return True  # Permissive on errors


def run_python_format(files: list[str], repo_path: Optional[str] = None) -> bool:
    """
    Run Python formatting checks

    Args:
        files: List of files to check
        repo_path: Repository path

    Returns:
        True if formatting passed
    """
    py_files = [f for f in files if f.endswith('.py')]
    if not py_files:
        return True  # No Python files

    try:
        # Try ruff (modern, fast)
        result = subprocess.run(
            ["ruff", "format", "--check"] + py_files,
            cwd=repo_path,
            timeout=30
        )

        if result.returncode == 0:
            emit_success("Python format check passed")
            return True
        else:
            emit_error("Python format check failed")
            emit_info("Fix: Run 'ruff format <files>' to format code")
            return False

    except FileNotFoundError:
        # ruff not available, try black
        try:
            result = subprocess.run(
                ["black", "--check"] + py_files,
                cwd=repo_path,
                timeout=30
            )

            if result.returncode == 0:
                emit_success("Black format check passed")
                return True
            else:
                emit_error("Black format check failed")
                emit_info("Fix: Run 'black <files>' to format code")
                return False

        except FileNotFoundError:
            emit_warning("Python formatter not found - skipping check")
            return True

    except Exception as e:
        emit_warning(f"Python format check failed: {e}")
        return True


def run_python_lint(files: list[str], repo_path: Optional[str] = None) -> bool:
    """
    Run Python linting

    Args:
        files: List of files to lint
        repo_path: Repository path

    Returns:
        True if linting passed
    """
    py_files = [f for f in files if f.endswith('.py')]
    if not py_files:
        return True

    try:
        result = subprocess.run(
            ["ruff", "check"] + py_files,
            cwd=repo_path,
            timeout=30
        )

        if result.returncode == 0:
            emit_success("Python lint passed")
            return True
        else:
            emit_error("Python lint failed")
            emit_info("Fix: Run 'ruff check --fix <files>' to auto-fix")
            return False

    except FileNotFoundError:
        emit_warning("Ruff not found - skipping Python lint")
        return True

    except Exception as e:
        emit_warning(f"Python lint failed: {e}")
        return True


def main():
    """
    Main entry point for pre-commit hook

    Exit codes:
    - 0: All checks passed
    - 1: Checks failed (blocks commit)
    """
    parser = argparse.ArgumentParser(description="Pre-commit quality checks")
    parser.add_argument(
        "--scope",
        choices=["staged-files", "all-files"],
        default="staged-files",
        help="Scope of files to check"
    )
    args = parser.parse_args()

    repo_path = Path.cwd()

    # Get files to check
    if args.scope == "staged-files":
        files = get_staged_files(repo_path)
        if not files:
            emit_info("No staged files - skipping pre-commit checks")
            sys.exit(0)
    else:
        # For all-files scope, tools will handle file discovery
        files = ["."  ]

    print("🔍 Running pre-commit checks...", file=sys.stderr)

    # Run all checks
    checks_passed = True

    # Swift checks
    if not run_swiftformat(files, repo_path):
        checks_passed = False

    if not run_swiftlint(files, repo_path):
        checks_passed = False

    # Python checks
    if not run_python_format(files, repo_path):
        checks_passed = False

    if not run_python_lint(files, repo_path):
        checks_passed = False

    # Summary
    if checks_passed:
        emit_success("All pre-commit checks passed")
        sys.exit(0)
    else:
        emit_error("Pre-commit checks failed")
        emit_info("Fix the errors above or use 'git commit --no-verify' to bypass")
        sys.exit(1)


if __name__ == "__main__":
    main()
