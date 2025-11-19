"""
Session file management utilities

Handles:
1. Syncing CLAUDE.md template to .claude/sessions/ directories
2. Syncing .gitattributes rule for session files
3. Checking for uncommitted session files
"""

import hashlib
import subprocess
import sys
from pathlib import Path

from shared.hook_utils import emit_success, emit_warning

# .gitattributes rule for session files
GITATTRIBUTES_RULE = ".claude/sessions/*.yml linguist-generated=true"


def sync_sessions_claude_md(repo_root: str) -> None:
    """
    Sync CLAUDE.md template to .claude/sessions/ directory

    Creates or updates the CLAUDE.md file in the sessions directory
    to ensure documentation stays current across all repositories.

    Args:
        repo_root: Path to repository root
    """
    try:
        repo_path = Path(repo_root)
        sessions_dir = repo_path / ".claude" / "sessions"

        # Create sessions directory if it doesn't exist
        sessions_dir.mkdir(parents=True, exist_ok=True)

        target_file = sessions_dir / "CLAUDE.md"

        # Find template (hooks are symlinked, so resolve to actual location)
        hooks_dir = Path(__file__).resolve().parent.parent.parent
        template_file = hooks_dir / "templates" / "sessions-CLAUDE.md"

        if not template_file.exists():
            emit_warning(f"Template not found: {template_file}")
            return

        # Read template content
        template_content = template_file.read_text()
        template_hash = hashlib.sha256(template_content.encode()).hexdigest()

        # Check if target exists and is up to date
        needs_update = True
        if target_file.exists():
            target_content = target_file.read_text()
            target_hash = hashlib.sha256(target_content.encode()).hexdigest()
            needs_update = template_hash != target_hash

        if needs_update:
            target_file.write_text(template_content)
            emit_success(f"✅ Updated {target_file.relative_to(repo_path)}")

    except Exception as e:
        # Non-critical - just warn
        emit_warning(f"Could not sync sessions CLAUDE.md: {e}")


def sync_gitattributes_rule(repo_root: str) -> None:
    """
    Ensure .gitattributes has rule to collapse session files in GitHub PRs

    Adds or updates the linguist-generated rule for session files.
    Preserves existing .gitattributes content.

    Args:
        repo_root: Path to repository root
    """
    try:
        repo_path = Path(repo_root)
        gitattributes_file = repo_path / ".gitattributes"

        # Read existing content if file exists
        existing_lines = []
        if gitattributes_file.exists():
            existing_lines = gitattributes_file.read_text().splitlines()

        # Check if rule already exists
        rule_exists = any(
            GITATTRIBUTES_RULE in line or ".claude/sessions/*.yml" in line
            for line in existing_lines
        )

        if not rule_exists:
            # Add the rule
            if existing_lines and not existing_lines[-1].strip():
                # File exists but ends with blank line - append directly
                pass
            elif existing_lines:
                # File exists with content - add blank line separator
                existing_lines.append("")

            # Add comment and rule
            existing_lines.append(
                "# Session files are valuable for historical context but should be"
            )
            existing_lines.append(
                "# collapsed in GitHub PR views to reduce noise in code reviews"
            )
            existing_lines.append(GITATTRIBUTES_RULE)

            # Write back
            gitattributes_file.write_text("\n".join(existing_lines) + "\n")
            emit_success("✅ Added session files rule to .gitattributes")

    except Exception as e:
        # Non-critical - just warn
        emit_warning(f"Could not sync .gitattributes: {e}")


def check_uncommitted_session_files(repo_root: str) -> None:
    """
    Check for uncommitted session files and emit reminder

    Args:
        repo_root: Path to repository root
    """
    try:
        repo_path = Path(repo_root)

        # Check git status for .claude/sessions/ directory
        result = subprocess.run(
            ["git", "status", "--porcelain", ".claude/sessions/"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            # Git command failed - skip check
            return

        # Parse output for uncommitted .yml files
        uncommitted = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            # Format: "XY filename" where X=staged, Y=unstaged
            status = line[:2]
            filepath = line[2:].strip()  # Start at position 2, not 3

            # Check if it's a .yml session file
            # (Path may or may not start with ./ depending on status)
            if filepath.endswith(".yml") and "claude/sessions/" in filepath:
                # ?? = untracked, M = modified, A = added
                if "?" in status or "M" in status or "A" in status:
                    uncommitted.append(filepath)

        if uncommitted:
            print("", file=sys.stderr)
            emit_warning("=" * 60)
            emit_warning("📋 Uncommitted session files from previous work:")
            for filepath in uncommitted:
                print(f"   {filepath}", file=sys.stderr)
            emit_warning("")
            emit_warning("💡 Consider committing these to preserve development context")
            emit_warning("   See .claude/sessions/CLAUDE.md for details")
            emit_warning("=" * 60)

    except subprocess.TimeoutExpired:
        emit_warning("Git status check timed out")
    except Exception:
        # Non-critical - just skip
        pass
