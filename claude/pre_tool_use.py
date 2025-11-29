#!/usr/bin/env python3
"""
PreToolUse Hook for Claude Code

Runs before Claude executes any tool.

Responsibilities:
1. Log Swift file edits for pattern analysis
2. Detect git commit, merge, and push operations
3. Enforce branch protection (only allow commits/merges to claude/* branches)
4. Prevent direct pushes to protected branches (main, master, production)
5. Warn when creating claude/* branches from other claude/* branches
6. Handle chained commands (e.g., cmd1 && cmd2 && cmd3)
7. Warn when using cd to change directory (prefer absolute paths)

Self-healing: Blocks dangerous operations but provides clear guidance
"""

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.git import get_current_branch, is_claude_branch
from shared.hook_utils import (
    emit_error,
    emit_info,
    emit_warning,
    format_hook_error,
    get_bash_command,
    get_hook_data,
    get_tool_input,
    get_tool_name,
)

# SQLite session logging (parallel with YAML during transition)
try:
    # Direct import from file path (avoids needing __init__.py package structure)
    import importlib.util

    _sqlite_path = Path(__file__).resolve().parent / "session" / "sqlite_logger.py"
    _spec = importlib.util.spec_from_file_location("sqlite_logger", _sqlite_path)
    _sqlite_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_sqlite_module)
    log_edit_to_sqlite = _sqlite_module.log_edit_to_sqlite

    SQLITE_LOGGING_AVAILABLE = True
except Exception:
    SQLITE_LOGGING_AVAILABLE = False


def should_log_edit(file_path: str, old_string: str, new_string: str) -> bool:
    """
    Determine if an edit should be logged based on filtering rules

    Filters out:
    - Binary files
    - Large files (> 1MB)
    - Massive edits (> 10,000 lines)
    - Lock files and build outputs

    Args:
        file_path: Path to file being edited
        old_string: Old content
        new_string: New content

    Returns:
        True if edit should be logged
    """
    file_path_lower = file_path.lower()

    # Size limits
    MAX_FILE_SIZE = 1_048_576  # 1MB
    MAX_EDIT_LINES = 10_000

    # Check edit size
    old_lines = len(old_string.splitlines())
    new_lines = len(new_string.splitlines())
    if old_lines > MAX_EDIT_LINES or new_lines > MAX_EDIT_LINES:
        return False  # Edit too large

    # Estimate file size from edit (conservative - assume edit is ~10% of file)
    estimated_size = max(len(old_string), len(new_string)) * 10
    if estimated_size > MAX_FILE_SIZE:
        return False

    # Exclude patterns - common noise files
    exclude_patterns = [
        # Session files (prevent infinite loop when committing)
        ".claude/sessions/",
        ".claude/current_session",
        # Lock files
        ".lock",
        "package-lock.json",
        "yarn.lock",
        "gemfile.lock",
        "cargo.lock",
        "poetry.lock",
        # Build outputs
        "/build/",
        "/dist/",
        "/.build/",
        "/target/",
        "/.next/",
        "/node_modules/",
        # Binary indicators
        ".o",
        ".pyc",
        ".class",
        ".exe",
        ".so",
        ".dylib",
    ]

    for pattern in exclude_patterns:
        if pattern in file_path_lower:
            return False

    return True


def find_git_root(cwd: str) -> Path | None:
    """
    Find the git repository root by walking up from current directory

    Args:
        cwd: Current working directory

    Returns:
        Path to git root, or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass

    return None


def classify_change_type(
    user_prompt: str, file_path: str, old_code: str, new_code: str
) -> str:
    """
    Classify the type of change being made (Phase 4)

    Args:
        user_prompt: User's request
        file_path: File being edited
        old_code: Old code
        new_code: New code

    Returns:
        Change type: refactor, bugfix, feature, docs, style, test, or unknown
    """
    prompt_lower = user_prompt.lower()
    file_lower = file_path.lower()

    # Documentation changes
    if ".md" in file_lower or "readme" in file_lower or "changelog" in file_lower:
        return "docs"

    # Test changes
    if "test" in file_lower or "spec" in file_lower:
        return "test"

    # Bug fixes (check prompt keywords)
    bug_keywords = ["fix", "bug", "error", "crash", "issue", "broken", "repair"]
    if any(keyword in prompt_lower for keyword in bug_keywords):
        return "bugfix"

    # Refactoring (check prompt keywords)
    refactor_keywords = [
        "refactor",
        "extract",
        "rename",
        "move",
        "reorganize",
        "clean up",
        "simplify",
        "reduce",
        "dependency",
    ]
    if any(keyword in prompt_lower for keyword in refactor_keywords):
        return "refactor"

    # Style/formatting
    style_keywords = ["format", "style", "lint", "whitespace", "indent"]
    if any(keyword in prompt_lower for keyword in style_keywords):
        return "style"

    # Features (check for new functionality)
    feature_keywords = ["add", "new", "create", "implement", "feature"]
    # But exclude "add comment" type changes
    if any(keyword in prompt_lower for keyword in feature_keywords):
        if "comment" not in prompt_lower and "doc" not in prompt_lower:
            return "feature"

    # Default
    return "unknown"


def log_file_edit(hook_data: dict) -> None:
    """
    Log file edits to SQLite database for pattern analysis

    Behavior:
    - Logs ALL text file edits to central SQLite database
    - Implements filtering (size limits, exclude patterns)
    - Adds change type classification
    """
    if not SQLITE_LOGGING_AVAILABLE:
        return

    try:
        tool_name = get_tool_name(hook_data)
        if tool_name != "Edit":
            return

        tool_input = get_tool_input(hook_data)
        file_path = tool_input.get("file_path", "")
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")

        # Apply filtering
        if not should_log_edit(file_path, old_string, new_string):
            return

        # Detect if the file being edited is in a git repo
        file_dir = str(Path(file_path).parent)
        git_root = find_git_root(file_dir)

        if not git_root:
            return  # Only log edits in git repos

        # Get user prompt from session-specific cache (primary method)
        user_prompt = ""
        session_id = hook_data.get("session_id", "")

        if session_id:
            prompt_cache = Path.home() / f".claude-prompt-{session_id}.json"
            if prompt_cache.exists():
                try:
                    prompt_data = json.loads(prompt_cache.read_text())
                    user_prompt = prompt_data.get("prompt", "")
                except Exception:
                    pass

        # Fallback: Read from transcript if cache doesn't have it
        if not user_prompt:
            transcript_path = hook_data.get("transcript_path", "")
            if transcript_path:
                try:
                    transcript_file = Path(transcript_path)
                    if transcript_file.exists():
                        with transcript_file.open("r") as f:
                            lines = f.readlines()
                            for line in reversed(lines[-50:]):
                                try:
                                    entry = json.loads(line)
                                    message = entry.get("message", {})
                                    if message.get("role") == "user":
                                        content = message.get("content", "")
                                        if isinstance(content, str):
                                            user_prompt = content
                                            break
                                except json.JSONDecodeError:
                                    continue
                except Exception:
                    pass

        # Classify change type
        change_type = classify_change_type(
            user_prompt, file_path, old_string, new_string
        )

        # Log to SQLite
        log_edit_to_sqlite(
            repo_path=str(git_root),
            branch=get_current_branch(str(git_root)),
            file_path=file_path,
            change_type=change_type,
            user_prompt=user_prompt,
            old_content=old_string,
            new_content=new_string,
        )
    except Exception:
        # Silent failure - don't block workflow for logging errors
        pass


def is_git_commit_command(command: str) -> bool:
    """
    Detect if a bash command is a git commit operation

    Handles various git commit formats:
    - git commit -m "message"
    - git commit --amend
    - git -C /path commit
    - git --no-pager commit

    Args:
        command: Bash command string

    Returns:
        True if this is a git commit operation
    """
    try:
        # Parse command into tokens (handles quotes properly)
        tokens = shlex.split(command)
    except ValueError:
        # Unparseable command - use regex fallback
        return bool(re.search(r"\bgit\b.*\bcommit\b", command))

    if len(tokens) < 2:
        return False

    # First token should be git (or path/to/git)
    if not tokens[0].endswith("git"):
        return False

    # Find first non-flag token after 'git'
    # This handles: git -C /path commit, git --no-pager commit, etc.
    skip_next = False
    for token in tokens[1:]:
        if skip_next:
            skip_next = False
            continue
        if token.startswith("-"):
            # Flags like -C take an argument, so skip next token
            if token in ["-C", "-c", "--git-dir", "--work-tree"]:
                skip_next = True
            continue  # Skip flags
        # First non-flag token should be "commit"
        return token == "commit"

    return False


def is_initial_commit(repo_path: str) -> bool:
    """
    Check if this would be the first commit in the repository

    Args:
        repo_path: Path to git repository

    Returns:
        True if there are no commits yet (initial commit scenario)
    """
    try:
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            cwd=repo_path,
            timeout=5,
            check=True,
        )
        return False  # HEAD exists, so there are commits
    except subprocess.CalledProcessError:
        return True  # No HEAD, this is the initial commit
    except Exception:
        return False  # On error, assume not initial commit


def is_git_merge_command(command: str) -> bool:
    """
    Detect if a bash command is a git merge operation

    Handles various git merge formats:
    - git merge branch-name
    - git merge --no-ff branch-name
    - git merge --abort (allowed - escape hatch)
    - git -C /path merge

    Args:
        command: Bash command string

    Returns:
        True if this is a git merge operation (excluding merge --abort)
    """
    try:
        # Parse command into tokens (handles quotes properly)
        tokens = shlex.split(command)
    except ValueError:
        # Unparseable command - use regex fallback
        return (
            bool(re.search(r"\bgit\b.*\bmerge\b", command)) and "--abort" not in command
        )

    if len(tokens) < 2:
        return False

    # First token should be git (or path/to/git)
    if not tokens[0].endswith("git"):
        return False

    # Find first non-flag token after 'git'
    skip_next = False
    for token in tokens[1:]:
        if skip_next:
            skip_next = False
            continue
        if token.startswith("-"):
            # Allow merge --abort (escape hatch)
            if token == "--abort":
                return False
            # Flags like -C take an argument, so skip next token
            if token in ["-C", "-c", "--git-dir", "--work-tree"]:
                skip_next = True
            continue  # Skip flags
        # First non-flag token should be "merge"
        return token == "merge"

    return False


def validate_git_merge(command: str, cwd: str) -> tuple[bool, str]:
    """
    Validate git merge operation

    Enforces:
    - Can only merge on claude/* branches
    - Merging INTO non-claude/* branches is blocked
    - git merge --abort is always allowed (escape hatch)

    Args:
        command: Git merge command
        cwd: Current working directory

    Returns:
        Tuple of (allowed, reason)
        - allowed: True if merge should proceed
        - reason: Explanation for decision
    """
    try:
        # Get current branch
        current_branch = get_current_branch(cwd)

        if not current_branch:
            return False, "Not in a git repository or detached HEAD state"

        # Block merges on non-claude/* branches
        if not is_claude_branch(current_branch, cwd):
            reason = (
                f"🚨 🚨 Merges only allowed on claude/* branches!\n"
                f"\n"
                f"Current branch: {current_branch}\n"
                f"\n"
                f"📋 You're trying to merge INTO '{current_branch}'.\n"
                f"   This would modify a non-claude/* branch directly.\n"
                f"\n"
                f"Correct workflow:\n"
                f"   1. Abort: git merge --abort\n"
                f"   2. Create feature branch: git checkout -b claude/feature-name\n"
                f"   3. Merge there: git merge <source-branch>\n"
                f"   4. Then I can help you create a PR or fast-forward if appropriate\n"
                f"\n"
                f"Or just ask me to handle the merge!"
            )
            return False, reason

        # On claude/* branch - allow merge
        return True, f"✅ Merging on safe branch: {current_branch}"

    except Exception as e:
        # On error, be permissive but warn
        return True, f"⚠️ Could not validate branch: {e}"


def validate_git_commit(command: str, cwd: str) -> tuple[bool, str]:
    """
    Validate git commit operation

    Enforces:
    - Can only commit to claude/* branches (after initial commit)
    - Initial commit allowed on any branch (repo bootstrap)
    - Current branch must start with claude/ (after bootstrap)

    Args:
        command: Git commit command
        cwd: Current working directory

    Returns:
        Tuple of (allowed, reason)
        - allowed: True if commit should proceed
        - reason: Explanation for decision
    """
    try:
        # Get current branch
        current_branch = get_current_branch(cwd)

        if not current_branch:
            return False, "Not in a git repository or detached HEAD state"

        # Allow initial commit on any branch (repo bootstrap)
        if is_initial_commit(cwd):
            if current_branch == "develop":
                return (
                    True,
                    "✅ Initial commit on develop - branch protection not enforced yet",
                )
            else:
                return (
                    True,
                    f"✅ Initial commit on {current_branch} - consider using 'develop' for initial commit",
                )

        # After initial commit, enforce branch protection
        if not is_claude_branch(current_branch, cwd):
            reason = (
                f"🚨 Commits only allowed on claude/* branches!\n"
                f"\n"
                f"Current branch: {current_branch}\n"
                f"\n"
                f"📋 Create a claude/* branch:\n"
                f"   git checkout -b claude/$(date -Iseconds | tr -d ':-')-feature-name\n"
                f"\n"
                f"Or I can create one for you - just ask!"
            )
            return False, reason

        # On claude/* branch - allow commit
        return True, f"✅ Committing to safe branch: {current_branch}"

    except Exception as e:
        # On error, be permissive but warn
        return True, f"⚠️ Could not validate branch: {e}"


def is_git_branch_create_command(command: str) -> bool:
    """
    Detect if a bash command creates a new git branch

    Handles:
    - git checkout -b branch-name
    - git branch branch-name
    - git switch -c branch-name

    Args:
        command: Command to check

    Returns:
        True if command creates a branch
    """
    # Normalize command
    cmd = command.strip().lower()

    # Remove git prefix
    if cmd.startswith("git "):
        cmd = cmd[4:].strip()

    # Check for branch creation patterns
    return (
        cmd.startswith("checkout -b ")
        or cmd.startswith("checkout --branch ")
        or cmd.startswith("branch ")
        and not any(x in cmd for x in ["-d", "-D", "-m", "-M", "--delete", "--move"])
        or cmd.startswith("switch -c ")
        or cmd.startswith("switch --create ")
    )


def get_base_branch(repo_path: str) -> str:
    """
    Get the default base branch for the repository

    Tries in order: develop, main, master
    Returns first one that exists

    Args:
        repo_path: Path to git repository

    Returns:
        Base branch name (develop/main/master) or "develop" as fallback
    """
    import subprocess

    for branch in ["develop", "main", "master"]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=2,
            )
            if result.returncode == 0:
                return branch
        except Exception:
            continue

    # Fallback to develop if nothing found
    return "develop"


def validate_git_branch_create(command: str, cwd: str) -> tuple[bool, str]:
    """
    Validate git branch creation operation

    Warns when:
    - Creating a claude/* branch from another claude/* branch
    - This prevents work accumulation on long-lived feature branches

    Args:
        command: Git branch creation command
        cwd: Current working directory

    Returns:
        Tuple of (allowed, reason)
        - allowed: True (always - this is a warning, not a blocker)
        - reason: Warning message if creating claude/* from claude/*
    """
    try:
        # Get current branch
        current_branch = get_current_branch(cwd)

        if not current_branch:
            return True, ""

        # Check if creating a claude/* branch
        # Extract branch name from command
        parts = command.split()
        branch_name = None

        for i, part in enumerate(parts):
            if part in ["-b", "--branch", "-c", "--create"]:
                if i + 1 < len(parts):
                    branch_name = parts[i + 1]
                    break
            elif part in ["branch"]:
                # git branch <name> format
                if i + 1 < len(parts):
                    branch_name = parts[i + 1]
                    break

        if not branch_name:
            return True, ""

        # Check if new branch is claude/* and current is also claude/*
        if branch_name.startswith("claude/") and is_claude_branch(current_branch, cwd):
            # Get the actual base branch for this repo
            base_branch = get_base_branch(cwd)

            warning = (
                f"⚠️  WARNING: Creating claude/* branch from another claude/* branch\n"
                f"\n"
                f"Current branch: {current_branch}\n"
                f"New branch: {branch_name}\n"
                f"\n"
                f"⚠️  This can lead to lost work if you:\n"
                f"   1. Create PR: {branch_name} → {current_branch}\n"
                f"   2. Merge that PR\n"
                f"   3. Delete {current_branch} before its PR to {base_branch} gets merged\n"
                f"\n"
                f"💡 Safer workflow:\n"
                f"   1. Switch to {base_branch}: git checkout {base_branch}\n"
                f"   2. Create branch: git checkout -b {branch_name}\n"
                f"   3. All PRs go directly: {branch_name} → {base_branch}\n"
                f"\n"
                f"Allowing operation, but be careful with merge workflow!"
            )
            return True, warning

        return True, ""

    except Exception as e:
        # On error, be permissive
        return True, f"⚠️ Could not validate branch creation: {e}"


def is_git_push_command(command: str) -> bool:
    """
    Detect if a bash command is a git push operation

    Handles various git push formats:
    - git push
    - git push origin main
    - git push -u origin branch
    - git -C /path push

    Args:
        command: Bash command string

    Returns:
        True if this is a git push operation
    """
    try:
        # Parse command into tokens (handles quotes properly)
        tokens = shlex.split(command)
    except ValueError:
        # Unparseable command - use regex fallback
        return bool(re.search(r"\bgit\b.*\bpush\b", command))

    if len(tokens) < 2:
        return False

    # First token should be git (or path/to/git)
    if not tokens[0].endswith("git"):
        return False

    # Find first non-flag token after 'git'
    skip_next = False
    for token in tokens[1:]:
        if skip_next:
            skip_next = False
            continue
        if token.startswith("-"):
            # Flags like -C, -u take an argument, so skip next token
            if token in ["-C", "-c", "--git-dir", "--work-tree", "-u"]:
                skip_next = True
            continue  # Skip flags
        # First non-flag token should be "push"
        return token == "push"

    return False


def extract_push_target_branch(command: str) -> str | None:
    """
    Extract the target branch from a git push command

    Handles:
    - git push (pushes current branch)
    - git push origin branch-name
    - git push -u origin branch-name
    - git push origin HEAD:branch-name

    Args:
        command: Git push command

    Returns:
        Target branch name, or None if current branch (implicit push)
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None

    # Find 'push' token and extract what comes after
    found_push = False
    remote_seen = False

    for i, token in enumerate(tokens):
        if found_push:
            # Skip flags
            if token.startswith("-"):
                continue

            # First non-flag after push is remote name (origin, etc.)
            if not remote_seen:
                remote_seen = True
                continue

            # Next non-flag is the branch spec
            # Handle refspec formats: branch-name or local:remote or HEAD:branch
            if ":" in token:
                # Refspec format (e.g., HEAD:main or local:remote)
                return token.split(":")[1]
            else:
                # Simple branch name
                return token

        if token == "push":
            found_push = True

    # No explicit branch - pushing current branch
    return None


def validate_git_push(command: str, cwd: str) -> tuple[bool, str]:
    """
    Validate git push operation

    Enforces:
    - Cannot push to main, master, or production branches
    - Suggests using PRs instead of direct pushes

    Args:
        command: Git push command
        cwd: Current working directory

    Returns:
        Tuple of (allowed, reason)
        - allowed: True if push should proceed
        - reason: Explanation for decision
    """
    try:
        # Extract target branch from command
        target_branch = extract_push_target_branch(command)

        # If no explicit target, get current branch
        if target_branch is None:
            target_branch = get_current_branch(cwd)

        if not target_branch:
            return False, "Not in a git repository or detached HEAD state"

        # Block pushes to protected branches
        protected_branches = ["main", "master", "develop", "production", "prod"]

        if target_branch in protected_branches:
            reason = (
                f"🚨 Direct push to '{target_branch}' is blocked!\n"
                f"\n"
                f"Protected branches: {', '.join(protected_branches)}\n"
                f"\n"
                f"📋 Correct workflow:\n"
                f"   1. Push to your claude/* branch: git push origin {get_current_branch(cwd) or 'claude/feature'}\n"
                f"   2. Create a pull request\n"
                f"   3. Merge via GitHub after review\n"
                f"\n"
                f"Or ask me to help create a PR!"
            )
            return False, reason

        # Allow push to non-protected branches
        return True, f"✅ Pushing to safe branch: {target_branch}"

    except Exception as e:
        # On error, be permissive but warn
        return True, f"⚠️ Could not validate push target: {e}"


def is_bare_swift_tool_command(command: str) -> tuple[bool, str]:
    """
    Check if command uses bare swiftlint/swiftformat instead of -smart versions

    Args:
        command: Bash command to check

    Returns:
        Tuple of (is_bare, tool_name)
    """
    # Parse command safely
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False, ""

    if not tokens:
        return False, ""

    # Check first token (handles both bare command and paths like /usr/bin/swiftlint)
    first_token = tokens[0]

    # Info-only flags that should always be allowed
    info_flags = {"--help", "-h", "--version", "-v", "help", "version", "rules"}

    # Check if any token is an info flag
    if len(tokens) > 1 and any(token in info_flags for token in tokens[1:]):
        return False, ""  # Allow info commands

    # Bare swiftlint (but not swiftlint-smart)
    if first_token.endswith("swiftlint") and not first_token.endswith(
        "swiftlint-smart"
    ):
        return True, "swiftlint"

    # Bare swiftformat (but not swiftformat-smart)
    if first_token.endswith("swiftformat") and not first_token.endswith(
        "swiftformat-smart"
    ):
        return True, "swiftformat"

    return False, ""


def is_cd_command(command: str) -> bool:
    """
    Detect if a bash command changes directory

    Handles:
    - cd /path
    - cd ..
    - cd (home directory)
    - pushd/popd

    Does NOT flag:
    - git -C /path (uses -C flag, doesn't change shell cwd)
    - (cd /path && cmd) - subshell, doesn't affect parent

    Args:
        command: Bash command to check

    Returns:
        True if command changes directory
    """
    cmd = command.strip()

    # Check for subshell pattern - these don't affect parent shell
    if cmd.startswith("(") and cmd.endswith(")"):
        return False

    # Check for cd or pushd at start of command
    if cmd.startswith("cd ") or cmd == "cd":
        return True
    if cmd.startswith("pushd ") or cmd == "pushd":
        return True

    return False


def check_cd_command(command: str) -> None:
    """
    Emit warning if command uses cd

    Non-blocking warning to prefer absolute paths over changing directories.

    Args:
        command: Bash command to check
    """
    if not is_cd_command(command):
        return

    emit_warning("=" * 60)
    emit_warning("Using 'cd' to change directory")
    emit_warning("")
    emit_warning("Prefer running commands from the project root using absolute paths.")
    emit_warning("This keeps the working directory predictable and avoids issues.")
    emit_warning("")
    emit_warning("Instead of:")
    emit_warning("  cd src/components && npm test")
    emit_warning("")
    emit_warning("Prefer:")
    emit_warning("  npm test --prefix src/components")
    emit_warning("  # or")
    emit_warning("  (cd src/components && npm test)  # subshell, doesn't affect cwd")
    emit_warning("=" * 60)


def split_chained_commands(command: str) -> list[str]:
    """
    Split a bash command into individual commands if chained with && or ;

    Args:
        command: Bash command string (possibly chained)

    Returns:
        List of individual commands
    """
    # Split by && and ; (simple split, doesn't handle quotes perfectly but good enough)
    # Use regex to split on && or ; while preserving the command parts
    import re

    # Split on && or ; not inside quotes
    parts = re.split(r"(?:&&|;)\s*", command)
    return [part.strip() for part in parts if part.strip()]


def validate_bash_command(hook_data: dict) -> bool:
    """
    Validate bash commands before execution

    Currently validates:
    - Git commit operations (must be on claude/* branch)
    - Git merge operations (must be on claude/* branch)
    - Git push operations (must not push to main/master/production)
    - Git branch creation (warns when creating claude/* from claude/*)
    - Swift quality tools (must use -smart versions)

    Handles chained commands (e.g., cmd1 && cmd2 && cmd3)

    Args:
        hook_data: Hook event data

    Returns:
        True if command should proceed, False to block
    """
    command = get_bash_command(hook_data)
    if not command:
        return True  # Not a Bash command

    cwd = hook_data.get("cwd", ".")

    # Check for cd command (warning only, non-blocking)
    check_cd_command(command)

    # Split chained commands and validate each one
    subcommands = split_chained_commands(command)

    for subcmd in subcommands:
        # Check for bare Swift quality tools
        is_bare, tool_name = is_bare_swift_tool_command(subcmd)
        if is_bare:
            emit_error(
                f"🚨 Don't use bare '{tool_name}' - use '{tool_name}-smart' instead"
            )
            emit_error("")
            emit_error("Why this matters:")
            emit_error(
                f"  • Bare '{tool_name}' uses SwiftLint defaults that REJECT trailing commas"
            )
            emit_error(
                "  • swiftformat is configured to ADD trailing commas (modern Swift style)"
            )
            emit_error("  • This creates a conflict where the tools fight each other")
            emit_error("")
            emit_error(f"  • {tool_name}-smart automatically finds the correct config:")
            emit_error("    1. Project-specific .swiftlint.yml/.swiftformat config")
            emit_error(
                "    2. Walks up directory tree to find config in parent directories"
            )
            emit_error(
                "    3. Falls back to ~/Developer/swift-quality-tools/Configs/ (shared)"
            )
            emit_error("")
            emit_error(f"Fix: Use {tool_name}-smart instead")
            emit_error(
                "  Available at: ~/Developer/swift-quality-tools/.build/release/"
            )
            return False

        # Check for git commit
        if is_git_commit_command(subcmd):
            allowed, reason = validate_git_commit(subcmd, cwd)

            if not allowed:
                emit_error(reason)
                return False
            else:
                # Log that commit is allowed
                print(reason, file=sys.stderr)

        # Check for git merge
        if is_git_merge_command(subcmd):
            allowed, reason = validate_git_merge(subcmd, cwd)

            if not allowed:
                emit_error(reason)
                return False
            else:
                # Log that merge is allowed
                print(reason, file=sys.stderr)

        # Check for git push
        if is_git_push_command(subcmd):
            allowed, reason = validate_git_push(subcmd, cwd)

            if not allowed:
                emit_error(reason)
                return False
            else:
                # Log that push is allowed
                print(reason, file=sys.stderr)

        # Check for git branch creation (warning only)
        if is_git_branch_create_command(subcmd):
            allowed, reason = validate_git_branch_create(subcmd, cwd)

            # Always allowed, but may have warning
            if reason:
                print(reason, file=sys.stderr)

    # All subcommands validated successfully
    return True


def main():
    """
    Main entry point for PreToolUse hook

    Exit codes:
    - 0: Allow operation
    - 2: Block operation (stderr shown to Claude)
    - 1: Non-blocking error

    Self-healing:
    - Blocks dangerous operations (commits to wrong branch)
    - Provides clear instructions for fixing
    - Permissive on errors (fail open)
    """
    try:
        hook_data = get_hook_data()
        tool_name = get_tool_name(hook_data)

        # Log file edits (silent, non-blocking)
        log_file_edit(hook_data)

        # Only validate Bash commands
        if tool_name == "Bash":
            allowed = validate_bash_command(hook_data)
            sys.exit(0 if allowed else 2)
        else:
            # Other tools - allow
            sys.exit(0)

    except Exception as e:
        # Self-healing: On unexpected error, allow operation but warn
        error_msg = format_hook_error("PreToolUse", e)
        print(error_msg, file=sys.stderr)
        emit_info("Allowing operation due to hook error")
        sys.exit(0)  # Permissive


if __name__ == "__main__":
    main()
