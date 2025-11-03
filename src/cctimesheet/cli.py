#!/usr/bin/env python3
"""
Claude Code Timesheet - Unified CLI entry point.
Parse Claude messages and generate timesheets in one command.
"""

import argparse
import sys
import tempfile
import os
from pathlib import Path
from typing import Optional

from .parser import parse_messages
from .generator import generate_timesheet


def main():
    """Main entry point for cctimesheet command."""
    parser = argparse.ArgumentParser(
        prog='cctimesheet',
        description="Generate timesheets from Claude Code message history. Automatically parses messages and groups activity into 15-minute blocks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Date/Range Options:
  You can specify a date range in two ways:
  - Number of days: Use an integer (e.g., 7, 14, 30)
  - Since date: Use YYYYMMDD format (e.g., 20250101)

Examples:
  %(prog)s                                    # Last 7 days (default)
  %(prog)s 14                                 # Last 14 days
  %(prog)s 20250101                           # Since January 1, 2025
  %(prog)s -p "*acme*"                        # Last 7 days, acme projects only
  %(prog)s 30 -p "client*"                    # Last 30 days, client projects only
  %(prog)s -e "*test*"                        # Last 7 days, exclude test projects
  %(prog)s -p "*api*" -e "*legacy*"           # API projects, excluding legacy
  %(prog)s -p "*wallfacer*" -e "*Research*" -g  # Wallfacer projects, grouped time
  %(prog)s --db custom.db --keep-db           # Use persistent database

Database Options:
  By default, a temporary database is created and deleted after generating
  the timesheet. Use --keep-db to preserve the database for faster subsequent
  runs (you'll only need to parse messages once).

Filter Patterns:
  Use wildcards in --project-filter and --exclude-filter:
  - "*acme*"       : Any project with "acme" in the name
  - "client*"      : Projects starting with "client"
  - "*backend"     : Projects ending with "backend"
        """
    )

    parser.add_argument(
        'date_or_days',
        nargs='?',
        help='Number of days ago (e.g., 7) or date in YYYYMMDD format (e.g., 20250101). Default: 7 days'
    )

    parser.add_argument(
        '--project-filter',
        '-p',
        metavar='PATTERN',
        help='Filter projects by glob pattern (case-insensitive). Supports wildcards: *, ?'
    )

    parser.add_argument(
        '--exclude-filter',
        '-e',
        metavar='PATTERN',
        help='Exclude projects by glob pattern (case-insensitive). Supports wildcards: *, ?'
    )

    parser.add_argument(
        '--group-time',
        '-g',
        action='store_true',
        help='Group time by unique timeblocks (don\'t double-count same 15-min block across projects)'
    )

    parser.add_argument(
        '--db',
        metavar='PATH',
        help='Database file path. If not specified, uses a temporary database that is deleted after use.'
    )

    parser.add_argument(
        '--keep-db',
        action='store_true',
        help='Keep the database file after generating timesheet (only relevant if --db is specified)'
    )

    parser.add_argument(
        '--projects-dir',
        type=Path,
        metavar='PATH',
        help='Claude projects directory (default: ~/.claude/projects)'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show verbose output during message parsing'
    )

    args = parser.parse_args()

    # Determine database path
    use_temp_db = args.db is None
    if use_temp_db:
        # Create temporary database
        temp_fd, db_path = tempfile.mkstemp(suffix='.db', prefix='cctimesheet_')
        os.close(temp_fd)  # Close file descriptor, we'll use the path
    else:
        db_path = args.db

    try:
        # Parse messages into database
        if args.verbose or use_temp_db:
            print("Parsing Claude Code messages...", file=sys.stderr)

        try:
            files_count, messages_count = parse_messages(
                db_path=db_path,
                projects_dir=args.projects_dir,
                verbose=args.verbose
            )
            if args.verbose:
                print(f"Parsed {files_count} files, {messages_count} messages", file=sys.stderr)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            print(f"Use --projects-dir to specify a different location", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error parsing messages: {e}", file=sys.stderr)
            sys.exit(1)

        # Generate timesheet
        if args.verbose or use_temp_db:
            print("Generating timesheet...", file=sys.stderr)

        try:
            timesheet = generate_timesheet(
                db_path=db_path,
                date_or_days=args.date_or_days,
                project_filter=args.project_filter,
                exclude_filter=args.exclude_filter,
                group_time=args.group_time
            )
            print(timesheet)
        except Exception as e:
            print(f"Error generating timesheet: {e}", file=sys.stderr)
            sys.exit(1)

    finally:
        # Clean up temporary database
        if use_temp_db:
            try:
                os.unlink(db_path)
            except Exception:
                pass  # Ignore cleanup errors
        elif not args.keep_db and args.db:
            # User specified a database path but didn't request to keep it
            pass  # Don't delete user-specified databases by default


if __name__ == "__main__":
    main()
