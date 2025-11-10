#!/usr/bin/env python3
"""
UserPromptSubmit Hook for Claude Code
Processes user prompts before Claude sees them
Can modify, log, or validate prompts
"""

import sys
from hook_utils import get_hook_data, format_hook_error


def process_prompt(hook_data: dict) -> None:
    """
    Process user prompt before Claude receives it

    Example uses:
    - Log prompts for later analysis
    - Add project-specific context automatically
    - Validate prompt formatting
    - Insert template expansions
    """
    # Get prompt text if available
    user_message = hook_data.get("user_message", "")

    # Could add logging here:
    # with open(f"{os.environ['HOME']}/.claude/prompt_log.txt", "a") as f:
    #     f.write(f"{datetime.now()}: {user_message}\n")

    # Could modify prompt here (though this requires careful handling)
    pass


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
