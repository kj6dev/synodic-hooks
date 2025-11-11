#!/usr/bin/env python3
"""
UserPromptSubmit Hook for Claude Code
Processes user prompts before Claude sees them
Can modify, log, or validate prompts
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from hook_utils import format_hook_error, get_hook_data


def process_prompt(hook_data: dict) -> None:
    """
    Process user prompt before Claude receives it

    Stores prompt for correlation with subsequent tool uses (Swift edits)
    """
    prompt = hook_data.get("prompt", "")
    session_id = hook_data.get("session_id", "")

    if not prompt or not session_id:
        return

    # Store prompt with timestamp in session-specific cache
    prompt_cache = Path.home() / f".claude-prompt-{session_id}.json"
    with prompt_cache.open("w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "prompt": prompt}, f)


def main():
    """Main entry point for UserPromptSubmit hook"""
    try:
        # Read hook data
        hook_data = get_hook_data()

        # Process the prompt
        process_prompt(hook_data)

        # Always exit 0 (permissive)
        sys.exit(0)

    except Exception as e:
        error_msg = format_hook_error("UserPromptSubmit", e, "Processing user prompt")
        print(error_msg, file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
