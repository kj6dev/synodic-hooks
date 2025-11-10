# Synodic Hooks - File Structure

Complete file tree with line counts and descriptions.

## Complete File Tree

```
synodic-hooks/ (19 files total, ~1,882 lines of Python)
│
├── .gitignore                              # Python/IDE/OS exclusions
├── README.md                               # Complete user documentation (~550 lines)
├── REFACTORING_NOTES.md                    # Modularization documentation
│
├── claude/                                 # Claude Code hooks (5 files)
│   ├── session_start.py           78 lines # Main entry point - delegates to session/
│   ├── pre_tool_use.py           191 lines # Git commit validation & blocking
│   └── session/                            # Session management package (4 files)
│       ├── __init__.py            13 lines # Public API exports
│       ├── branch_management.py  117 lines # Branch creation, cleanup, auto-create
│       ├── change_handler.py      74 lines # Uncommitted changes auto-commit
│       └── reporter.py            47 lines # Session context reporting
│
├── git/                                    # Git operation scripts (2 files)
│   ├── pre_commit.py             326 lines # SwiftFormat, SwiftLint, Ruff validation
│   └── pre_push.py               227 lines # Test execution (scripts/pre_push)
│
├── shared/                                 # Shared utilities (6 files)
│   ├── hook_utils.py             157 lines # Hook data parsing, error formatting
│   └── git/                                # Git operations package (5 files)
│       ├── __init__.py            39 lines # Public API re-exports
│       ├── repo.py                40 lines # is_git_repo_root, find_repo_root
│       ├── status.py              65 lines # get_current_branch, has_uncommitted_changes
│       ├── branch.py             162 lines # create_branch, delete_branch, etc.
│       └── claude.py             114 lines # create_unique_claude_branch, is_claude_branch
│
├── templates/                              # Per-repo .githooks wrappers (2 files)
│   ├── pre-commit                          # Bash → git/pre_commit.py
│   └── pre-push                            # Bash → git/pre_push.py
│
└── tests/                                  # Test suite (2 files)
    ├── test_git_utils.py         166 lines # Git utilities tests
    └── test_pre_tool_use.py       66 lines # Git commit detection tests
```

## Module Breakdown by Size

**Smallest to Largest:**
```
   13  claude/session/__init__.py          # Minimal package API
   39  shared/git/__init__.py              # Re-exports for convenience
   40  shared/git/repo.py                  # Repository detection only
   47  claude/session/reporter.py          # Session context output
   65  shared/git/status.py                # Status queries
   66  tests/test_pre_tool_use.py          # Focused test suite
   74  claude/session/change_handler.py    # Auto-commit logic
   78  claude/session_start.py             # Lean entry point
  114  shared/git/claude.py                # Claude-specific git ops
  117  claude/session/branch_management.py # Branch operations
  157  shared/hook_utils.py                # Hook utilities
  162  shared/git/branch.py                # Core branch operations
  166  tests/test_git_utils.py             # Comprehensive tests
  191  claude/pre_tool_use.py              # Commit validation
  227  git/pre_push.py                     # Test execution
  326  git/pre_commit.py                   # Quality checks
```

**Average:** ~98 lines per file
**Largest:** 326 lines (git/pre_commit.py - comprehensive quality tool)
**Smallest:** 13 lines (claude/session/__init__.py - simple re-exports)

## Import Patterns

**Backward Compatible Package Imports:**
```python
# Everything available from package root
from shared.git import (
    # Repository
    is_git_repo_root,
    find_repo_root,

    # Status
    get_current_branch,
    get_git_status,
    has_uncommitted_changes,

    # Branches
    branch_exists,
    create_branch,
    checkout_branch,
    delete_branch,
    get_branches,

    # Claude-specific
    create_unique_claude_branch,
    get_claude_branches,
    is_claude_branch,
    is_empty_claude_branch,
)

# Session management
from claude.session import (
    cleanup_empty_branches,
    create_session_branch,
    handle_uncommitted_changes,
    report_session_context,
    should_auto_create_branch,
)
```

**Focused Module Imports (Alternative):**
```python
# Import specific modules when you only need subset
from shared.git.status import get_current_branch
from shared.git.claude import is_claude_branch
from claude.session.reporter import report_session_context
```

## Benefits of Current Structure

### Maintainability
- **Easy to find code**: Clear module names indicate purpose
- **Small cognitive load**: No file over 326 lines
- **Obvious organization**: Related functions grouped logically

### Testability
- **Isolated modules**: Test one concern at a time
- **Clear dependencies**: Easy to mock/stub
- **Focused test files**: Match module structure

### Extensibility
- **Add features easily**: New modules don't bloat existing code
- **Package growth**: Add to `git/` or `session/` packages as needed
- **No merge conflicts**: Small files reduce collision risk

### Developer Experience
- **IDE navigation**: Jump to definition works great
- **Search efficiency**: Find what you need quickly
- **Code review**: Small diffs, clear changes
