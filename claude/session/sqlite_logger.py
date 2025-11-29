"""
SQLite Session Logger

Logs Claude Code edit operations to a centralized SQLite database.
Database location: ~/Developer/claude-session-db/{repo-name}.db

Simple flat schema - just edits with timestamp, no session grouping.

This module can be tested directly:
    python -m claude.session.sqlite_logger --test

Or imported and used:
    from claude.session.sqlite_logger import log_edit_to_sqlite
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path


# Single database for all repos
SESSION_DB_PATH = Path.home() / "Developer" / "claude-session-db" / "edits.db"


def get_db_path() -> Path:
    """
    Get path to the single shared database

    Returns:
        Path to SQLite database
    """
    SESSION_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return SESSION_DB_PATH


def create_schema(conn: sqlite3.Connection) -> None:
    """Create database schema if it doesn't exist"""
    cursor = conn.cursor()

    # Flat edits table - no session grouping needed
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS edits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        repo TEXT NOT NULL,
        branch TEXT,
        file_path TEXT NOT NULL,
        change_type TEXT,
        user_prompt TEXT,
        old_content TEXT,
        new_content TEXT
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_edits_file ON edits(file_path)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_edits_timestamp ON edits(timestamp)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_edits_repo ON edits(repo)
    """)

    conn.commit()


def get_repo_name(git_root: Path) -> str:
    """
    Extract repository name from git root path

    Args:
        git_root: Path to git repository root

    Returns:
        Repository name (directory name)
    """
    return git_root.name


def log_edit_to_sqlite(
    repo_path: str,
    branch: str,
    file_path: str,
    change_type: str,
    user_prompt: str,
    old_content: str,
    new_content: str,
) -> bool:
    """
    Log an edit to the SQLite database

    Args:
        repo_path: Full path to repository
        branch: Current git branch
        file_path: Path to file being edited
        change_type: Type of change (refactor, bugfix, feature, etc.)
        user_prompt: User's request that triggered the edit
        old_content: Old content being replaced
        new_content: New content

    Returns:
        True if logged successfully, False otherwise
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))

        create_schema(conn)

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO edits (
                timestamp, repo, branch, file_path, change_type,
                user_prompt, old_content, new_content
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                repo_path,
                branch,
                file_path,
                change_type,
                user_prompt,
                old_content,
                new_content,
            ),
        )
        conn.commit()
        conn.close()
        return True

    except Exception as e:
        # Loud failure - make sure Claude sees this
        import traceback

        print("🚨" * 20, file=sys.stderr)
        print("🚨 SQLite SESSION LOGGING FAILED", file=sys.stderr)
        print("🚨" * 20, file=sys.stderr)
        print(f"🚨 Error: {type(e).__name__}: {e}", file=sys.stderr)
        print(f"🚨 Database: {db_path}", file=sys.stderr)
        print(f"🚨 File being logged: {file_path}", file=sys.stderr)
        print("🚨", file=sys.stderr)
        print("🚨 This needs to be fixed! Edit logging is broken.", file=sys.stderr)
        print("🚨", file=sys.stderr)
        print("🚨 Stack trace:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("🚨" * 20, file=sys.stderr)
        return False


def get_stats() -> dict:
    """
    Get statistics for the session database

    Returns:
        Dict with edit count
    """
    try:
        db_path = get_db_path()
        if not db_path.exists():
            return {"edits": 0, "exists": False}

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM edits")
        edits = cursor.fetchone()[0]

        conn.close()
        return {"edits": edits, "exists": True}

    except Exception as e:
        return {"edits": 0, "exists": False, "error": str(e)}


def run_test() -> None:
    """
    Test the SQLite logger with sample data
    """
    print("Testing SQLite Session Logger (single database)")
    print("=" * 60)

    db_path = get_db_path()
    print(f"Database: {db_path}")
    print()

    # Log a test edit
    print("Logging test edit...")
    success = log_edit_to_sqlite(
        repo_path="/tmp/test-repo",
        branch="main",
        file_path="/tmp/test-repo/src/main.py",
        change_type="test",
        user_prompt="Test the SQLite logger",
        old_content="def hello():\n    pass",
        new_content="def hello():\n    print('Hello, world!')",
    )

    if success:
        print("  Edit logged successfully")
    else:
        print("  FAILED to log edit")
        return

    # Log another edit from different repo
    print("Logging edit from different repo...")
    success = log_edit_to_sqlite(
        repo_path="/tmp/other-repo",
        branch="develop",
        file_path="/tmp/other-repo/src/utils.py",
        change_type="feature",
        user_prompt="Add utility function",
        old_content="",
        new_content="def format_name(name: str) -> str:\n    return name.title()",
    )

    if success:
        print("  Edit logged successfully")
    else:
        print("  FAILED to log edit")

    # Get stats
    print()
    print("Database stats:")
    stats = get_stats()
    print(f"  Total edits: {stats['edits']}")

    print()
    print(f"File size: {db_path.stat().st_size} bytes")

    # Query to show the edits
    print()
    print("Recent edits:")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, repo, branch, change_type FROM edits ORDER BY timestamp DESC LIMIT 5"
    )
    for row in cursor.fetchall():
        repo_name = Path(row[1]).name if row[1] else "unknown"
        print(f"  {row[0][:19]} | {repo_name} | {row[2]} | {row[3]}")
    conn.close()

    print()
    print("=" * 60)
    print("Test completed successfully!")


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_test()
    else:
        print("Usage: python -m claude.session.sqlite_logger --test")
        print()
        print(
            "This module provides SQLite-based session logging for Claude Code hooks."
        )
        print("Run with --test to verify the logger is working correctly.")
