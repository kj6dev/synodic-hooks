#!/usr/bin/env python3
"""
SessionEnd Hook for Claude Code

Runs when a Claude Code session ends.
Auto-commits synodic-planning beads state.

Self-healing: Never blocks session end. All errors are silent.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add current directory for local imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_utils import play_sound, SOUND_TINK

# synodic-planning repo location (contains .beads symlink to ~/Developer/.beads)
SYNODIC_PLANNING = Path.home() / "Developer" / "synodic-planning"


def auto_commit_synodic_planning() -> None:
    """
    Auto-commit and push synodic-planning if .beads has changes.
    Silent on all errors - never blocks session end.
    """
    if not SYNODIC_PLANNING.exists():
        return

    try:
        # Check for uncommitted changes (including untracked)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=SYNODIC_PLANNING,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0 or not result.stdout.strip():
            # No changes or git error - nothing to do
            return

        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=SYNODIC_PLANNING,
            capture_output=True,
            timeout=10,
        )

        # Commit with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "commit", "-m", f"beads: auto-sync {timestamp}"],
            cwd=SYNODIC_PLANNING,
            capture_output=True,
            timeout=10,
        )

        # Push (silent failure is fine - might be offline)
        subprocess.run(
            ["git", "push"],
            cwd=SYNODIC_PLANNING,
            capture_output=True,
            timeout=30,
        )

    except Exception:
        # Silent failure - never block session end
        pass


def finalize_session(project_dir: str) -> None:
    """
    Finalize session on end

    Args:
        project_dir: Current project directory
    """
    # Auto-commit synodic-planning beads state
    auto_commit_synodic_planning()

    # Completion sound (optional, uncomment to enable)
    # play_sound(SOUND_TINK)


def main():
    """
    Main entry point for SessionEnd hook

    Self-healing philosophy:
    - Always exit 0 (never block session end)
    - Silent on errors
    """
    try:
        # Get project directory
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Finalize session
        finalize_session(project_dir)

        # Always succeed
        sys.exit(0)

    except Exception:
        # Ultimate safety net - never block session end
        sys.exit(0)


if __name__ == "__main__":
    main()
