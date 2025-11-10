#!/usr/bin/env python3
"""
PreCompact Hook for Claude Code
Executes before Claude compacts conversation context
Useful for preserving important information before compaction
"""

import sys
from hook_utils import get_hook_data, format_hook_error


def handle_pre_compact(hook_data: dict) -> None:
    """
    Handle pre-compaction event

    Example uses:
    - Save full conversation history before compaction
    - Extract and preserve critical context
    - Log compaction events for analysis
    - Archive important decisions/discussions
    """
    # Could save conversation state:
    # timestamp = datetime.now().isoformat()
    # save_path = f"{os.environ['HOME']}/.claude/archives/pre_compact_{timestamp}.json"
    # with open(save_path, "w") as f:
    #     json.dump(hook_data, f, indent=2)

    pass


def main():
    """Main entry point for PreCompact hook"""
    try:
        # Read hook data
        hook_data = get_hook_data()

        # Handle pre-compaction
        handle_pre_compact(hook_data)

        # Always exit 0 (permissive)
        sys.exit(0)

    except Exception as e:
        error_msg = format_hook_error("PreCompact", e, "Handling pre-compaction event")
        print(error_msg, file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
