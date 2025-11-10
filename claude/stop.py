#!/usr/bin/env python3
"""
Stop Hook for Claude Code
Plays a sound when Claude finishes a task/session
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hook_utils import get_hook_data, play_sound, format_hook_error, SOUND_GLASS
from shared.discord import send_notification


def main():
    """Main entry point for Stop hook"""
    try:
        # Read hook data (for potential future use)
        hook_data = get_hook_data()

        # Play completion sound
        play_sound(SOUND_GLASS)

        # Send Discord notification
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        send_notification(
            message="🛑",
            project=Path(project_dir).name
        )

        # Could add session cleanup logic here:
        # - Save session state
        # - Commit pending changes
        # - Generate summary report
        # - Log session metrics

        # Always exit 0 (permissive)
        sys.exit(0)

    except Exception as e:
        error_msg = format_hook_error("Stop", e, "Playing stop sound and cleanup")
        print(error_msg, file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
