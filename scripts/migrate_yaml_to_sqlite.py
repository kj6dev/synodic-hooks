#!/usr/bin/env python3
"""
Migrate YAML session files to SQLite database

Handles:
- Multi-document YAML files (session metadata + edits)
- Malformed YAML from merge conflicts
- Tracks failures for manual review
- Deduplication by timestamp

Usage:
    python scripts/migrate_yaml_to_sqlite.py [--dry-run]
    python scripts/migrate_yaml_to_sqlite.py --sessions-dir .claude/sessions/
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

# Central database location
DB_PATH = Path.home() / "Developer" / "claude-session-db" / "edits.db"

# Try to import yaml, provide helpful error if missing
try:
    import yaml
except ImportError:
    print("Error: PyYAML not installed")
    print("Install with: pip install pyyaml")
    print("Or with uv: uv pip install pyyaml")
    sys.exit(1)


def create_schema(conn: sqlite3.Connection) -> None:
    """Create database schema if it doesn't exist (flat schema)"""
    cursor = conn.cursor()

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


def parse_edit_with_regex(raw_doc: str) -> dict | None:
    """
    Fallback parser using regex for malformed YAML edit documents

    Extracts key fields when YAML parsing fails (e.g., due to merge conflicts
    causing inconsistent indentation in block scalars).

    Args:
        raw_doc: Raw YAML document content

    Returns:
        Dict with extracted fields, or None if not an edit document
    """
    # Must look like an edit document
    if "time:" not in raw_doc or "file:" not in raw_doc:
        return None

    result = {}

    # Extract simple single-line fields
    patterns = {
        "time": r"^time:\s*(.+?)$",
        "file": r"^file:\s*(.+?)$",
        "change_type": r"^change_type:\s*(.+?)$",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, raw_doc, re.MULTILINE)
        if match:
            result[field] = match.group(1).strip()

    # Extract user_prompt (block scalar)
    prompt_match = re.search(
        r"^user_prompt:\s*\|\s*\n((?:  .+\n?)+)", raw_doc, re.MULTILINE
    )
    if prompt_match:
        # Remove leading indentation
        lines = prompt_match.group(1).split("\n")
        result["user_prompt"] = "\n".join(
            line[2:] if line.startswith("  ") else line for line in lines
        ).strip()

    # For old/new content - these are often corrupted by merge conflicts
    # Skip them to avoid data corruption - metadata is most valuable anyway
    result["old"] = "[content not recovered - malformed YAML]"
    result["new"] = "[content not recovered - malformed YAML]"

    return result if result.get("time") else None


def parse_yaml_documents(content: str) -> list[dict]:
    """
    Parse YAML content that may contain multiple documents

    Handles malformed YAML by attempting individual document parsing.

    Args:
        content: Raw YAML file content

    Returns:
        List of parsed documents (dicts), empty dicts for failures
    """
    documents = []

    # Split by document separator
    # Handle both "---\n" at start and between documents
    raw_docs = re.split(r"^---\s*$", content, flags=re.MULTILINE)

    for raw_doc in raw_docs:
        raw_doc = raw_doc.strip()
        if not raw_doc:
            continue

        # Skip comment-only sections
        if raw_doc.startswith("#") and "\n" not in raw_doc.strip("#").strip():
            continue

        try:
            doc = yaml.safe_load(raw_doc)
            if doc and isinstance(doc, dict):
                documents.append(doc)
        except yaml.YAMLError as e:
            # Try regex fallback for malformed documents
            fallback = parse_edit_with_regex(raw_doc)
            if fallback:
                fallback["_recovered"] = True
                documents.append(fallback)
            else:
                # Track the failure but continue
                documents.append(
                    {
                        "_parse_error": True,
                        "_raw_content": raw_doc[:500],  # First 500 chars for debugging
                        "_error": str(e),
                    }
                )

    return documents


def get_existing_timestamps(conn: sqlite3.Connection, repo: str) -> set[str]:
    """Get all existing timestamps for a repo to avoid duplicates."""
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp FROM edits WHERE repo = ?", (repo,))
    return {row[0] for row in cursor.fetchall()}


def migrate_file(
    yaml_path: Path, conn: sqlite3.Connection, dry_run: bool = False
) -> tuple[int, int, int, int, list[str]]:
    """
    Migrate a single YAML file to SQLite (flat schema)

    Args:
        yaml_path: Path to YAML file
        conn: SQLite connection
        dry_run: If True, don't actually insert

    Returns:
        Tuple of (edits_migrated, edits_recovered, edits_skipped, edits_failed, error_messages)
    """
    cursor = conn.cursor()
    edits_migrated = 0
    edits_recovered = 0
    edits_skipped = 0
    edits_failed = 0
    errors = []

    try:
        content = yaml_path.read_text()
    except Exception as e:
        return 0, 0, 0, 0, [f"Could not read file: {e}"]

    documents = parse_yaml_documents(content)

    if not documents:
        return 0, 0, 0, 0, ["No valid documents found"]

    # First document should be session metadata
    session_doc = documents[0]
    repo = session_doc.get("repo", "unknown")
    branch = session_doc.get("branch", "")

    # Get existing timestamps for deduplication
    existing_timestamps = get_existing_timestamps(conn, repo)

    # Process edit documents
    for doc in documents[1:]:
        if doc.get("_parse_error"):
            edits_failed += 1
            errors.append(f"Parse error: {doc.get('_error', 'unknown')}")
            continue

        # Skip if not an edit document
        if "file" not in doc and "time" not in doc:
            continue

        timestamp = doc.get("time", "")

        # Skip duplicates
        if timestamp in existing_timestamps:
            edits_skipped += 1
            continue

        # Track if this was recovered via regex fallback
        is_recovered = doc.get("_recovered", False)

        if not dry_run:
            try:
                cursor.execute(
                    """
                INSERT INTO edits (timestamp, repo, branch, file_path, change_type, user_prompt, old_content, new_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        timestamp,
                        repo,
                        branch,
                        doc.get("file", ""),
                        doc.get("change_type", ""),
                        doc.get("user_prompt", ""),
                        doc.get("old", ""),
                        doc.get("new", ""),
                    ),
                )
                existing_timestamps.add(timestamp)  # Track for dedup within file
                if is_recovered:
                    edits_recovered += 1
                else:
                    edits_migrated += 1
            except Exception as e:
                edits_failed += 1
                errors.append(f"Edit insert error: {e}")
        else:
            if is_recovered:
                edits_recovered += 1
            else:
                edits_migrated += 1

    if not dry_run:
        conn.commit()

    return edits_migrated, edits_recovered, edits_skipped, edits_failed, errors


def main():
    parser = argparse.ArgumentParser(description="Migrate YAML sessions to SQLite")
    parser.add_argument("--dry-run", action="store_true", help="Parse but don't insert")
    parser.add_argument(
        "--sessions-dir",
        type=Path,
        default=Path(".claude/sessions"),
        help="Path to sessions directory",
    )
    args = parser.parse_args()

    if not args.sessions_dir.exists():
        print(f"Sessions directory not found: {args.sessions_dir}")
        sys.exit(1)

    yaml_files = list(args.sessions_dir.glob("*.yml"))
    if not yaml_files:
        print("No YAML files found")
        sys.exit(0)

    print(f"Found {len(yaml_files)} YAML files")
    print(f"Database: {DB_PATH}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Create/connect to database
    if args.dry_run:
        conn = sqlite3.connect(":memory:")
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))

    create_schema(conn)

    total_migrated = 0
    total_recovered = 0
    total_skipped = 0
    total_failed = 0
    all_errors = []

    for yaml_path in sorted(yaml_files):
        print(f"Processing: {yaml_path.name}...", end=" ")
        migrated, recovered, skipped, failed, errors = migrate_file(
            yaml_path, conn, args.dry_run
        )
        total_migrated += migrated
        total_recovered += recovered
        total_skipped += skipped
        total_failed += failed

        parts = [f"✓ {migrated} edits"]
        if recovered:
            parts.append(f"🔧 {recovered} recovered")
        if skipped:
            parts.append(f"⏭ {skipped} skipped")
        if failed:
            parts.append(f"⚠ {failed} failed")
        print(", ".join(parts))

        if errors:
            all_errors.extend([(yaml_path.name, e) for e in errors])

    conn.close()

    print()
    print("=" * 60)
    print(f"Total edits migrated: {total_migrated}")
    if total_recovered:
        print(
            f"Total edits recovered: {total_recovered} (metadata only, code content lost)"
        )
    if total_skipped:
        print(f"Total edits skipped (duplicates): {total_skipped}")
    print(f"Total edits failed: {total_failed}")

    if all_errors:
        print()
        print("Errors encountered:")
        for filename, error in all_errors:
            print(f"  {filename}: {error[:100]}")

    if not args.dry_run and DB_PATH.exists():
        size_kb = DB_PATH.stat().st_size / 1024
        print()
        print(f"Database size: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
