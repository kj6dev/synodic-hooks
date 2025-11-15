#!/usr/bin/env python3
"""
Edit Log Indexer - Build searchable index from session files

Scans .claude/sessions/*.yml files and generates .claude/index.json
for fast searching of edits by file, symbol, or session.

Usage:
    python3 edit-log-indexer.py [repo-path]
    python3 edit-log-indexer.py  # Uses current directory
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_yaml_value(lines: list[str], start_idx: int) -> tuple[str, int]:
    """
    Parse a YAML multi-line string value (|)

    Args:
        lines: All lines from file
        start_idx: Index of line with '|'

    Returns:
        Tuple of (value, next_line_index)
    """
    value_lines = []
    idx = start_idx + 1

    if idx >= len(lines):
        return "", idx

    # Get indentation of first content line
    base_indent = len(lines[idx]) - len(lines[idx].lstrip())

    while idx < len(lines):
        line = lines[idx]

        # Check if we hit a new YAML key (not indented enough)
        if line.strip() and not line.startswith(" " * base_indent):
            break

        # Remove base indentation
        if line.strip():
            value_lines.append(line[base_indent:])
        else:
            value_lines.append("")

        idx += 1

    return "\n".join(value_lines), idx


def parse_session_file(session_file: Path) -> dict[str, Any]:
    """
    Parse a session YAML file into structured data

    Args:
        session_file: Path to session .yml file

    Returns:
        Dict with session metadata, edits, and commits (Phase 4)
    """
    with session_file.open("r") as f:
        lines = f.readlines()

    session_data = {
        "file": str(session_file),
        "metadata": {},
        "edits": [],
        "commits": [],  # Phase 4
    }

    i = 0
    current_edit = None
    current_commit = None

    while i < len(lines):
        line = lines[i].rstrip()

        # Session metadata section
        if "session_id:" in line:
            session_data["metadata"]["session_id"] = line.split(":", 1)[1].strip()
        elif "started:" in line:
            session_data["metadata"]["started"] = line.split(":", 1)[1].strip()
        elif "repo:" in line:
            session_data["metadata"]["repo"] = line.split(":", 1)[1].strip()
        elif "branch:" in line:
            session_data["metadata"]["branch"] = line.split(":", 1)[1].strip()

        # Commit entries (Phase 4)
        elif line.startswith("commit_sha:"):
            # Save previous commit if exists
            if current_commit:
                session_data["commits"].append(current_commit)

            current_commit = {
                "sha": line.split(":", 1)[1].strip(),
                "time": "",
                "message": "",
            }

        elif current_commit and line.startswith("commit_time:"):
            current_commit["time"] = line.split(":", 1)[1].strip()

        elif current_commit and line.startswith("commit_message: |"):
            value, next_i = parse_yaml_value(lines, i)
            current_commit["message"] = value
            i = next_i - 1

        # Edit entries
        elif line.startswith("time:"):
            # Save previous edit if exists
            if current_edit:
                session_data["edits"].append(current_edit)
            # Save previous commit if exists
            if current_commit:
                session_data["commits"].append(current_commit)
                current_commit = None

            current_edit = {
                "time": line.split(":", 1)[1].strip(),
                "file": "",
                "change_type": "unknown",  # Phase 4
                "user_prompt": "",
                "old": "",
                "new": "",
            }

        elif current_edit and line.startswith("file:"):
            current_edit["file"] = line.split(":", 1)[1].strip()

        elif current_edit and line.startswith("change_type:"):  # Phase 4
            current_edit["change_type"] = line.split(":", 1)[1].strip()

        elif current_edit and line.startswith("user_prompt: |"):
            value, next_i = parse_yaml_value(lines, i)
            current_edit["user_prompt"] = value
            i = next_i - 1

        elif current_edit and line.startswith("old: |"):
            value, next_i = parse_yaml_value(lines, i)
            current_edit["old"] = value
            i = next_i - 1

        elif current_edit and line.startswith("new: |"):
            value, next_i = parse_yaml_value(lines, i)
            current_edit["new"] = value
            i = next_i - 1

        i += 1

    # Don't forget last edit/commit
    if current_edit:
        session_data["edits"].append(current_edit)
    if current_commit:
        session_data["commits"].append(current_commit)

    return session_data


def extract_symbols(code: str) -> list[dict[str, str]]:
    """
    Extract symbol definitions from code (struct, class, func, let, var, enum)

    Args:
        code: Source code text

    Returns:
        List of dicts with {type, name, line}
    """
    symbols = []

    # Swift patterns
    patterns = [
        (r"^\s*(public\s+|private\s+|internal\s+)?(struct|class|enum|protocol)\s+(\w+)", "type"),
        (r"^\s*(public\s+|private\s+|internal\s+)?func\s+(\w+)", "function"),
        (r"^\s*(public\s+|private\s+|internal\s+)?(let|var)\s+(\w+)", "property"),
    ]

    for line_num, line in enumerate(code.split("\n"), 1):
        for pattern, symbol_type in patterns:
            match = re.search(pattern, line)
            if match:
                # Extract symbol name (last captured group)
                name = match.group(match.lastindex)
                symbols.append({
                    "type": symbol_type,
                    "name": name,
                    "line": line_num,
                })

    return symbols


def build_index(sessions_dir: Path) -> dict[str, Any]:
    """
    Build searchable index from all session files

    Args:
        sessions_dir: Path to .claude/sessions/ directory

    Returns:
        Index dictionary
    """
    index = {
        "version": "2.0",  # Phase 4
        "generated": datetime.now().isoformat(),
        "sessions": {},
        "by_file": {},
        "by_symbol": {},
        "by_change_type": {},  # Phase 4
    }

    # Find all session files
    session_files = sorted(sessions_dir.glob("*.yml"))

    print(f"Found {len(session_files)} session files")

    for session_file in session_files:
        print(f"Indexing {session_file.name}...")

        try:
            session_data = parse_session_file(session_file)
        except Exception as e:
            print(f"  ⚠️  Error parsing {session_file.name}: {e}")
            continue

        session_id = session_data["metadata"].get("session_id", session_file.stem)

        # Add to sessions index (Phase 4: include commits)
        index["sessions"][session_id] = {
            "file": session_file.name,
            "started": session_data["metadata"].get("started", ""),
            "branch": session_data["metadata"].get("branch", ""),
            "edit_count": len(session_data["edits"]),
            "commit_count": len(session_data["commits"]),  # Phase 4
            "commits": session_data["commits"],  # Phase 4
            "files_modified": [],
        }

        # Process each edit
        for edit in session_data["edits"]:
            file_path = edit["file"]
            edit_time = edit["time"]

            # Track files modified
            if file_path not in index["sessions"][session_id]["files_modified"]:
                index["sessions"][session_id]["files_modified"].append(file_path)

            # Index by file
            if file_path not in index["by_file"]:
                index["by_file"][file_path] = []

            # Check if we already have an entry for this session
            file_entry = next(
                (e for e in index["by_file"][file_path] if e["session"] == session_id),
                None,
            )

            if file_entry:
                file_entry["edit_times"].append(edit_time)
            else:
                index["by_file"][file_path].append({
                    "session": session_id,
                    "edit_times": [edit_time],
                })

            # Extract symbols from old code (removed)
            old_symbols = extract_symbols(edit["old"])
            for symbol in old_symbols:
                symbol_name = symbol["name"]
                if symbol_name not in index["by_symbol"]:
                    index["by_symbol"][symbol_name] = []

                # Check if symbol exists in new code
                new_symbols = extract_symbols(edit["new"])
                if not any(s["name"] == symbol_name for s in new_symbols):
                    # Symbol was removed
                    index["by_symbol"][symbol_name].append({
                        "session": session_id,
                        "file": file_path,
                        "action": "removed",
                        "time": edit_time,
                    })

            # Extract symbols from new code (added)
            new_symbols = extract_symbols(edit["new"])
            for symbol in new_symbols:
                symbol_name = symbol["name"]
                if symbol_name not in index["by_symbol"]:
                    index["by_symbol"][symbol_name] = []

                # Check if symbol existed in old code
                if not any(s["name"] == symbol_name for s in old_symbols):
                    # Symbol was added
                    index["by_symbol"][symbol_name].append({
                        "session": session_id,
                        "file": file_path,
                        "action": "added",
                        "time": edit_time,
                    })

            # Index by change type (Phase 4)
            change_type = edit.get("change_type", "unknown")
            if change_type not in index["by_change_type"]:
                index["by_change_type"][change_type] = []

            index["by_change_type"][change_type].append({
                "session": session_id,
                "file": file_path,
                "time": edit_time,
            })

    print(f"\n✅ Indexed {len(index['sessions'])} sessions")
    print(f"   - {len(index['by_file'])} files modified")
    print(f"   - {len(index['by_symbol'])} symbols tracked")
    print(f"   - {len(index['by_change_type'])} change types recorded")

    return index


def main():
    """Main entry point"""
    # Get repo path from args or use current directory
    if len(sys.argv) > 1:
        repo_path = Path(sys.argv[1])
    else:
        repo_path = Path.cwd()

    # Find .claude/sessions directory
    claude_dir = repo_path / ".claude"
    sessions_dir = claude_dir / "sessions"

    if not sessions_dir.exists():
        print(f"❌ No sessions directory found at {sessions_dir}")
        print(f"   Make sure you're in a git repository with .claude/sessions/")
        sys.exit(1)

    # Build index
    index = build_index(sessions_dir)

    # Write index file
    index_file = claude_dir / "index.json"
    with index_file.open("w") as f:
        json.dump(index, f, indent=2)

    print(f"\n💾 Index written to {index_file}")


if __name__ == "__main__":
    main()
