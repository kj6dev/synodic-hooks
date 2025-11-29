#!/usr/bin/env python3
"""
Stop Hook for Claude Code

Runs when Claude finishes a task/session.

Responsibilities:
1. Send Discord notification
2. Commit and push edit log database
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports (resolve symlinks first)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hook_utils import format_hook_error, get_hook_data
from shared.discord import send_notification

# Database location
DB_REPO = Path.home() / "Developer" / "claude-session-db"
DB_FILE = DB_REPO / "edits.db"


def get_db_stats() -> dict:
    """Get stats from the database for commit message"""
    import sqlite3

    stats = {"total_edits": 0, "size_kb": 0}

    try:
        if DB_FILE.exists():
            stats["size_kb"] = DB_FILE.stat().st_size / 1024

            conn = sqlite3.connect(str(DB_FILE))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM edits")
            stats["total_edits"] = cursor.fetchone()[0]
            conn.close()
    except Exception:
        pass

    return stats


def commit_and_push_database() -> None:
    """Commit and push the edit log database"""
    if not DB_REPO.exists():
        print("⚠️ Database repo not found, skipping commit", file=sys.stderr)
        return

    if not DB_FILE.exists():
        print("⚠️ Database file not found, skipping commit", file=sys.stderr)
        return

    try:
        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(DB_REPO),
            timeout=10,
        )

        if not result.stdout.strip():
            # No changes to commit
            return

        # Get stats for commit message
        stats = get_db_stats()

        # Stage the database file
        subprocess.run(
            ["git", "add", "edits.db"],
            cwd=str(DB_REPO),
            timeout=10,
            check=True,
        )

        # Commit with stats
        commit_msg = (
            f"Update edit log - {stats['total_edits']} total edits\n\n"
            f"Database size: {stats['size_kb']:.1f} KB\n"
            f"Timestamp: {datetime.now().isoformat()}"
        )

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(DB_REPO),
            capture_output=True,
            timeout=30,
            check=True,
        )

        # Push to remote
        subprocess.run(
            ["git", "push"],
            cwd=str(DB_REPO),
            capture_output=True,
            timeout=60,
            check=True,
        )

        print(
            f"✅ Edit log committed and pushed ({stats['total_edits']} edits)",
            file=sys.stderr,
        )

    except subprocess.CalledProcessError as e:
        print("🚨" * 10, file=sys.stderr)
        print("🚨 FAILED TO COMMIT/PUSH EDIT LOG DATABASE", file=sys.stderr)
        print("🚨" * 10, file=sys.stderr)
        print(f"🚨 Error: {e}", file=sys.stderr)
        if e.stderr:
            print(f"🚨 Stderr: {e.stderr}", file=sys.stderr)
        print(f"🚨 Repo: {DB_REPO}", file=sys.stderr)
        print("🚨", file=sys.stderr)
        print("🚨 Edit log data may be lost if not backed up!", file=sys.stderr)
        print("🚨" * 10, file=sys.stderr)
    except Exception as e:
        print(f"🚨 Edit log commit error: {e}", file=sys.stderr)


def main():
    """Main entry point for Stop hook"""
    try:
        # Read hook data (for potential future use)
        get_hook_data()

        # Send Discord notification
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        send_notification(message="🛑", project=Path(project_dir).name)

        # Commit and push the edit log database
        commit_and_push_database()

        # Always exit 0 (permissive)
        sys.exit(0)

    except Exception as e:
        error_msg = format_hook_error("Stop", e, "Stop hook cleanup")
        print(error_msg, file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
