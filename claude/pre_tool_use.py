#!/usr/bin/env python3
"""
PreToolUse Hook for Claude Code

Runs before Claude executes any tool.

Responsibilities:
1. Log Swift file edits for pattern analysis
2. Detect git commit operations
3. Enforce branch protection (only allow commits to claude/* branches)
4. Validate commit operations

Self-healing: Blocks dangerous operations but provides clear guidance
"""

import json
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.git import get_current_branch, is_claude_branch
from shared.hook_utils import (
    emit_error,
    emit_info,
    format_hook_error,
    get_bash_command,
    get_hook_data,
    get_tool_input,
    get_tool_name,
)


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


def get_or_create_session_id(git_root: Path) -> str:
    """
    Get current session ID or create a new one

    Session ID format: claude-YYYYMMDD-HHMMSS
    Stored in .claude/current_session

    Args:
        git_root: Path to git repository root

    Returns:
        Session ID string
    """
    claude_dir = git_root / ".claude"
    session_file = claude_dir / "current_session"

    # Check if session file exists and is recent (< 4 hours old)
    if session_file.exists():
        try:
            session_id = session_file.read_text().strip()
            # Parse timestamp from session ID
            timestamp_str = session_id.replace("claude-", "")
            # Simple heuristic: if file modified < 4 hours ago, reuse session
            mtime = session_file.stat().st_mtime
            import time
            if (time.time() - mtime) < (4 * 3600):
                return session_id
        except Exception:
            pass

    # Create new session ID
    session_id = datetime.now().strftime("claude-%Y%m%d-%H%M%S")

    # Write to file
    claude_dir.mkdir(exist_ok=True)
    session_file.write_text(session_id)

    return session_id


def get_session_metadata(git_root: Path, session_id: str) -> dict:
    """
    Get or create session metadata

    Args:
        git_root: Path to git repository root
        session_id: Current session ID

    Returns:
        Dict with session metadata
    """
    try:
        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(git_root),
            timeout=5,
        )
        branch = result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        branch = "unknown"

    return {
        "session_id": session_id,
        "started": datetime.now().isoformat(),
        "repo": str(git_root),
        "branch": branch,
    }


def write_session_metadata(session_file: Path, metadata: dict) -> None:
    """
    Write session metadata to the beginning of session file

    Args:
        session_file: Path to session file
        metadata: Session metadata dict
    """
    with session_file.open("w") as f:
        f.write("---\n")
        f.write("# Session Metadata\n")
        f.write(f"session_id: {metadata['session_id']}\n")
        f.write(f"started: {metadata['started']}\n")
        f.write(f"repo: {metadata['repo']}\n")
        f.write(f"branch: {metadata['branch']}\n")
        f.write("edit_count: 0\n")
        f.write("---\n\n")


def log_file_edit(hook_data: dict) -> None:
    """
    Log file edits to per-repo session YAML files for pattern analysis

    New behavior (Phase 1):
    - Logs ALL text file edits (not just Swift)
    - Detects git repos and logs to .claude/sessions/SESSION_ID.yml
    - Falls back to global log if not in git repo
    - Implements filtering (size limits, exclude patterns)
    - Adds session metadata (session_id, repo, branch)
    """
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
        # Use the file's directory, not the current working directory
        file_dir = str(Path(file_path).parent)
        git_root = find_git_root(file_dir)

        if git_root:
            # Per-repo session logging
            session_id = get_or_create_session_id(git_root)
            sessions_dir = git_root / ".claude" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)

            # Session file format: YYYYMMDD-HHMMSS.yml
            session_filename = session_id.replace("claude-", "") + ".yml"
            log_file = sessions_dir / session_filename

            # Create session file with metadata if new
            if not log_file.exists():
                metadata = get_session_metadata(git_root, session_id)
                write_session_metadata(log_file, metadata)
        else:
            # Fallback to global log
            log_file = Path.home() / "Developer" / "swift-edits.yml"
            log_file.parent.mkdir(exist_ok=True)

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
                        # Read last ~50 lines to find most recent user message
                        with transcript_file.open("r") as f:
                            lines = f.readlines()
                            # Search backwards for user message
                            for line in reversed(lines[-50:]):
                                try:
                                    entry = json.loads(line)
                                    message = entry.get("message", {})
                                    if message.get("role") == "user":
                                        # Get text content from user message
                                        content = message.get("content", "")
                                        if isinstance(content, str):
                                            user_prompt = content
                                            break
                                except json.JSONDecodeError:
                                    continue
                except Exception:
                    pass

        # Write YAML entry (append to session file)
        with log_file.open("a") as f:
            f.write("---\n")
            f.write(f"# Edit {datetime.now().isoformat()}\n")
            f.write(f"time: {datetime.now().isoformat()}\n")
            f.write(f"file: {file_path}\n")
            if user_prompt:
                f.write("user_prompt: |\n")
                for line in user_prompt.splitlines():
                    f.write(f"  {line}\n")
            f.write("old: |\n")
            for line in old_string.splitlines():
                f.write(f"  {line}\n")
            f.write("new: |\n")
            for line in new_string.splitlines():
                f.write(f"  {line}\n")
            f.write("\n")
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

    # Bare swiftlint (but not swiftlint-smart)
    if first_token.endswith("swiftlint") and not first_token.endswith("swiftlint-smart"):
        return True, "swiftlint"

    # Bare swiftformat (but not swiftformat-smart)
    if first_token.endswith("swiftformat") and not first_token.endswith(
        "swiftformat-smart"
    ):
        return True, "swiftformat"

    return False, ""


def validate_bash_command(hook_data: dict) -> bool:
    """
    Validate bash commands before execution

    Currently validates:
    - Git commit operations (must be on claude/* branch)
    - Swift quality tools (must use -smart versions)

    Args:
        hook_data: Hook event data

    Returns:
        True if command should proceed, False to block
    """
    command = get_bash_command(hook_data)
    if not command:
        return True  # Not a Bash command

    cwd = hook_data.get("cwd", ".")

    # Check for bare Swift quality tools
    is_bare, tool_name = is_bare_swift_tool_command(command)
    if is_bare:
        emit_error(f"🚨 Don't use bare '{tool_name}' - use '{tool_name}-smart' instead")
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
        emit_error(f"  Available at: ~/Developer/swift-quality-tools/.build/release/")
        return False

    # Check for git commit
    if is_git_commit_command(command):
        allowed, reason = validate_git_commit(command, cwd)

        if not allowed:
            emit_error(reason)
            return False
        else:
            # Log that commit is allowed
            print(reason, file=sys.stderr)
            return True

    # Other bash commands - allow
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
