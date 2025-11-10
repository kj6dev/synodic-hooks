#!/usr/bin/env python3
"""
SubagentStop Hook for Claude Code
Executes when subagent tasks complete
Useful for cleanup, logging, or aggregating subagent results
"""

import sys
from hook_utils import get_hook_data, format_hook_error


def handle_subagent_completion(hook_data: dict) -> None:
    """
    Handle subagent task completion

    Example uses:
    - Aggregate results from multiple subagents
    - Log subagent performance metrics
    - Clean up subagent-specific resources
    - Trigger next phase of multi-agent workflow
    """
    # Could extract subagent info:
    # subagent_id = hook_data.get("subagent_id")
    # subagent_type = hook_data.get("subagent_type")
    # execution_time = hook_data.get("execution_time")

    pass


def main():
    """Main entry point for SubagentStop hook"""
    try:
        # Read hook data
        hook_data = get_hook_data()

        # Handle subagent completion
        handle_subagent_completion(hook_data)

        # Always exit 0 (permissive)
        sys.exit(0)

    except Exception as e:
        error_msg = format_hook_error("SubagentStop", e, "Handling subagent completion")
        print(error_msg, file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
