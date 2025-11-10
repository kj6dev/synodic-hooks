"""Git utilities package for synodic-hooks"""

# Re-export all public functions for convenience
from .branch import (
    branch_exists,
    checkout_branch,
    create_branch,
    delete_branch,
    get_branches,
)
from .claude import (
    create_unique_claude_branch,
    get_claude_branches,
    is_claude_branch,
    is_empty_claude_branch,
)
from .repo import find_repo_root, is_git_repo_root
from .status import get_current_branch, get_git_status, has_uncommitted_changes

__all__ = [
    # Branch operations
    "branch_exists",
    "checkout_branch",
    "create_branch",
    "delete_branch",
    "get_branches",
    # Claude-specific operations
    "create_unique_claude_branch",
    "get_claude_branches",
    "is_claude_branch",
    "is_empty_claude_branch",
    # Repository operations
    "find_repo_root",
    "is_git_repo_root",
    # Status operations
    "get_current_branch",
    "get_git_status",
    "has_uncommitted_changes",
]
