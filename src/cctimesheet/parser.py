"""
Parse Claude Code JSONL files and store message timestamps in SQLite database.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional


def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database with messages table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT NOT NULL,
            project_name TEXT NOT NULL,
            message_type TEXT,
            uuid TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_session_id ON messages(session_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_project_name ON messages(project_name)
    """)

    conn.commit()
    return conn


def extract_project_name(file_path: Path) -> str:
    """Extract project name from directory path."""
    # Project name is the parent directory name
    return file_path.parent.name


def parse_jsonl_file(file_path: Path, conn: sqlite3.Connection, verbose: bool = False) -> int:
    """Parse a single JSONL file and insert records into database."""
    project_name = extract_project_name(file_path)
    cursor = conn.cursor()
    count = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())

                    # Extract relevant fields if they exist
                    timestamp = data.get('timestamp')
                    session_id = data.get('sessionId')
                    message_type = data.get('type')
                    uuid = data.get('uuid')

                    # Only insert if we have timestamp and session_id
                    if timestamp and session_id:
                        cursor.execute("""
                            INSERT INTO messages (timestamp, session_id, project_name, message_type, uuid)
                            VALUES (?, ?, ?, ?, ?)
                        """, (timestamp, session_id, project_name, message_type, uuid))
                        count += 1

                except json.JSONDecodeError as e:
                    if verbose:
                        print(f"Warning: Failed to parse line {line_num} in {file_path}: {e}", file=sys.stderr)
                    continue

    except Exception as e:
        if verbose:
            print(f"Error processing file {file_path}: {e}", file=sys.stderr)
        return count

    conn.commit()
    return count


def process_all_files(base_path: Path, conn: sqlite3.Connection, verbose: bool = False) -> tuple[int, int]:
    """Process all JSONL files in the Claude projects directory."""
    jsonl_files = list(base_path.glob("**/*.jsonl"))
    total_files = len(jsonl_files)
    total_messages = 0

    for i, jsonl_file in enumerate(jsonl_files, 1):
        count = parse_jsonl_file(jsonl_file, conn, verbose=verbose)
        total_messages += count
        if verbose and (i % 10 == 0 or i == total_files):
            print(f"Processed {i}/{total_files} files, {total_messages} messages inserted", end='\r')

    if verbose:
        print()  # New line after progress
    return total_files, total_messages


def parse_messages(db_path: str, projects_dir: Optional[Path] = None, verbose: bool = False) -> tuple[int, int]:
    """
    Parse Claude Code messages and store in database.

    Args:
        db_path: Path to SQLite database file
        projects_dir: Path to Claude projects directory (defaults to ~/.claude/projects)
        verbose: Whether to print progress messages

    Returns:
        Tuple of (files_count, messages_count)
    """
    if projects_dir is None:
        projects_dir = Path.home() / ".claude" / "projects"

    if not projects_dir.exists():
        raise FileNotFoundError(f"Claude projects directory not found at {projects_dir}")

    conn = init_database(db_path)
    try:
        return process_all_files(projects_dir, conn, verbose=verbose)
    finally:
        conn.close()
