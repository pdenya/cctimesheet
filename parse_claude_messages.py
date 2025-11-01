#!/usr/bin/env python3
"""
Parse Claude Code JSONL files and store message timestamps in SQLite database.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional


def init_database(db_path: str = "claude_messages.db") -> sqlite3.Connection:
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


def parse_jsonl_file(file_path: Path, conn: sqlite3.Connection) -> int:
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
                    print(f"Warning: Failed to parse line {line_num} in {file_path}: {e}", file=sys.stderr)
                    continue

    except Exception as e:
        print(f"Error processing file {file_path}: {e}", file=sys.stderr)
        return count

    conn.commit()
    return count


def process_all_files(base_path: Path, conn: sqlite3.Connection) -> tuple[int, int]:
    """Process all JSONL files in the Claude projects directory."""
    jsonl_files = list(base_path.glob("**/*.jsonl"))
    total_files = len(jsonl_files)
    total_messages = 0

    for i, jsonl_file in enumerate(jsonl_files, 1):
        count = parse_jsonl_file(jsonl_file, conn)
        total_messages += count
        if i % 10 == 0 or i == total_files:
            print(f"Processed {i}/{total_files} files, {total_messages} messages inserted", end='\r')

    print()  # New line after progress
    return total_files, total_messages


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Parse Claude Code JSONL files and store message timestamps in SQLite database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Import all JSONL files from ~/.claude/projects
  %(prog)s file.jsonl                # Import single file
  %(prog)s --db custom.db            # Use custom database file
  %(prog)s --projects-dir /path      # Use custom projects directory
        """
    )

    parser.add_argument(
        'file',
        nargs='?',
        help='Path to a single JSONL file to process (optional)'
    )

    parser.add_argument(
        '--db',
        default='claude_messages.db',
        help='Database file path (default: claude_messages.db)'
    )

    parser.add_argument(
        '--projects-dir',
        type=Path,
        default=Path.home() / ".claude" / "projects",
        help='Claude projects directory (default: ~/.claude/projects)'
    )

    args = parser.parse_args()

    # Check projects directory exists
    if not args.file and not args.projects_dir.exists():
        print(f"Error: Claude projects directory not found at {args.projects_dir}", file=sys.stderr)
        print(f"Use --projects-dir to specify a different location", file=sys.stderr)
        sys.exit(1)

    # Initialize database
    conn = init_database(args.db)

    try:
        if args.file:
            # Process single file
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File not found: {file_path}", file=sys.stderr)
                sys.exit(1)

            count = parse_jsonl_file(file_path, conn)
            print(f"Processed {file_path.name}: {count} messages inserted")
        else:
            # Process all files
            print(f"Processing all JSONL files in {args.projects_dir}...")
            files_count, messages_count = process_all_files(args.projects_dir, conn)
            print(f"Complete! Processed {files_count} files, inserted {messages_count} messages")
            print(f"Database: {args.db}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
