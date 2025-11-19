"""Session management components for Claude Code"""

from .branch_management import (
    cleanup_empty_branches,
    create_session_branch,
    should_auto_create_branch,
)
from .change_handler import handle_uncommitted_changes
from .reporter import report_session_context
from .session_files import (
    check_uncommitted_session_files,
    sync_gitattributes_rule,
    sync_sessions_claude_md,
)

__all__ = [
    "check_uncommitted_session_files",
    "cleanup_empty_branches",
    "create_session_branch",
    "handle_uncommitted_changes",
    "report_session_context",
    "should_auto_create_branch",
    "sync_gitattributes_rule",
    "sync_sessions_claude_md",
]
