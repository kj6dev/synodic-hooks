#!/usr/bin/env python3
"""
Notification Hook for Claude Code
Plays a sound when Claude sends notifications
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Add current directory for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_utils import get_hook_data, play_sound, format_hook_error, SOUND_SOSUMI
from shared.discord import send_notification


def main():
    """Main entry point for Notification hook"""
    try:
        # Read hook data (for potential future use)
        hook_data = get_hook_data()

        # Play notification sound
        play_sound(SOUND_SOSUMI)

        # Send Discord notification
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        send_notification(
            message="🔔",
            project=Path(project_dir).name
        )

        # Could add custom logic here:
        # - Log notifications to file
        # - Send to external monitoring system
        # - Display OS notification

        # Always exit 0 (permissive)
        sys.exit(0)

    except Exception as e:
        error_msg = format_hook_error("Notification", e, "Playing notification sound")
        print(error_msg, file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
