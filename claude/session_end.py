#!/usr/bin/env python3
"""
SessionEnd Hook for Claude Code

Runs when a Claude Code session ends.
Sends Discord notification if webhook is configured.
Optionally plays completion sound.

Self-healing: Never blocks session end. All errors are silent.

Example uses:
- Save session state to disk
- Generate session summary report
- Commit pending changes
- Clean up temporary files
- Archive conversation logs
"""

import os
import sys
from pathlib import Path

# Add current directory for local imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_utils import play_sound, SOUND_TINK


def finalize_session(project_dir: str) -> None:
    """
    Finalize session on end

    Args:
        project_dir: Current project directory
    """
    # Could save session state:
    # state_file = Path(project_dir) / ".claude_state.json"
    # with open(state_file, "w") as f:
    #     json.dump(session_state, f, indent=2)

    # Completion sound (optional, uncomment to enable)
    # play_sound(SOUND_TINK)

    pass


def main():
    """
    Main entry point for SessionEnd hook

    Self-healing philosophy:
    - Always exit 0 (never block session end)
    - Silent on errors
    - Graceful if Discord not configured
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
