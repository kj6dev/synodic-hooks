"""Session management components for Claude Code"""

from .branch_management import (
    cleanup_empty_branches,
    create_session_branch,
    should_auto_create_branch,
)
from .change_handler import handle_uncommitted_changes
from .reporter import report_session_context

__all__ = [
    "cleanup_empty_branches",
    "create_session_branch",
    "handle_uncommitted_changes",
    "report_session_context",
    "should_auto_create_branch",
]
