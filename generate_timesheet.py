#!/usr/bin/env python3
"""
Generate a timesheet from Claude Code messages.
Groups activity into 15-minute chunks per project per day.
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import sys
import fnmatch


def get_messages_since_date(conn: sqlite3.Connection, since_date: datetime) -> List[Tuple]:
    """Fetch messages since a specific date."""
    cursor = conn.cursor()
    cutoff_iso = since_date.isoformat()

    cursor.execute("""
        SELECT timestamp, session_id, project_name
        FROM messages
        WHERE timestamp >= ?
        ORDER BY timestamp
    """, (cutoff_iso,))

    return cursor.fetchall()


def clean_project_name(project_name: str) -> str:
    """Convert directory format to readable project name."""
    # Remove leading dash and convert dashes to slashes
    if project_name.startswith('-'):
        project_name = project_name[1:]

    # Replace -Code- with simpler path
    project_name = project_name.replace('-Users-pdenya-Code-', '')
    project_name = project_name.replace('-Users-pdenya-', '~/')
    project_name = project_name.replace('-', '/')

    return project_name


def round_to_15min(dt: datetime) -> datetime:
    """Round datetime to nearest 15-minute block."""
    minutes = (dt.minute // 15) * 15
    return dt.replace(minute=minutes, second=0, microsecond=0)


def group_by_15min_chunks(messages: List[Tuple], project_filter: Optional[str] = None, exclude_filter: Optional[str] = None, group_time: bool = False) -> Dict[str, Dict[str, set]]:
    """
    Group messages into 15-minute chunks per day per project.

    Args:
        messages: List of (timestamp, session_id, project_name) tuples
        project_filter: Optional glob pattern to include projects
        exclude_filter: Optional glob pattern to exclude projects
        group_time: If True, count unique timeblocks (don't double-count same block for multiple projects)

    Returns: {date: {project: {set of 15min time blocks}}}
    """
    # First pass: collect all activity without filtering
    all_activity = defaultdict(lambda: defaultdict(set))

    for timestamp_str, session_id, project_name in messages:
        try:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            # Convert to local time (naive datetime)
            dt = dt.replace(tzinfo=None)

            # Round to 15-minute block
            block = round_to_15min(dt)

            # Get date string
            date_str = dt.strftime('%Y-%m-%d')

            # Clean project name
            project = clean_project_name(project_name)

            # Add this 15-min block to the project's activity for this day
            all_activity[date_str][project].add(block)

        except Exception as e:
            print(f"Warning: Failed to parse timestamp {timestamp_str}: {e}", file=sys.stderr)
            continue

    # Second pass: apply filters at the project level
    activity = defaultdict(lambda: defaultdict(set))

    for date_str, projects in all_activity.items():
        for project, blocks in projects.items():
            # Apply project filter if specified
            if project_filter and not fnmatch.fnmatch(project.lower(), project_filter.lower()):
                continue

            # Apply exclude filter if specified
            if exclude_filter and fnmatch.fnmatch(project.lower(), exclude_filter.lower()):
                continue

            # This project passes filters, include its blocks
            activity[date_str][project] = blocks

    # Third pass: if group_time is enabled, merge all timeblocks into a single combined entry
    if group_time and activity:
        grouped_activity = defaultdict(lambda: defaultdict(set))
        for date_str, projects in activity.items():
            # Collect all unique timeblocks across all projects for this date
            all_blocks = set()
            project_names = []
            for project, blocks in projects.items():
                all_blocks.update(blocks)
                project_names.append(project)
            # Create a combined project name
            combined_name = "Combined: " + ", ".join(sorted(project_names))
            grouped_activity[date_str][combined_name] = all_blocks
        return grouped_activity

    return activity


def calculate_hours(time_blocks: set) -> float:
    """Calculate total hours from set of 15-minute time blocks."""
    return len(time_blocks) * 0.25


def format_timesheet(activity: Dict[str, Dict[str, set]], since_date: datetime, project_filter: Optional[str] = None, exclude_filter: Optional[str] = None, group_time: bool = False) -> str:
    """Format the timesheet for display."""
    output = []
    output.append("=" * 80)

    # Calculate date range for header
    days_ago = (datetime.now() - since_date).days
    if days_ago <= 1:
        range_text = "TODAY"
    elif days_ago <= 7:
        range_text = f"LAST {days_ago} DAYS"
    else:
        range_text = f"SINCE {since_date.strftime('%B %d, %Y').upper()}"

    # Add filters to header if specified
    if project_filter:
        range_text = f"{range_text} - FILTER: {project_filter}"
    if exclude_filter:
        range_text = f"{range_text} - EXCLUDE: {exclude_filter}"
    if group_time:
        range_text = f"{range_text} - GROUPED TIME"

    output.append(f"CLAUDE CODE TIMESHEET - {range_text}")
    output.append("=" * 80)
    output.append("")

    # Sort dates
    sorted_dates = sorted(activity.keys(), reverse=True)

    grand_total_hours = 0

    for date_str in sorted_dates:
        projects = activity[date_str]

        # Parse date for nice formatting
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = date_obj.strftime('%A')
        formatted_date = date_obj.strftime('%B %d, %Y')

        output.append(f"{day_name}, {formatted_date}")
        output.append("-" * 80)

        # Sort projects by hours (descending)
        project_hours = [(proj, calculate_hours(blocks)) for proj, blocks in projects.items()]
        project_hours.sort(key=lambda x: x[1], reverse=True)

        day_total = 0

        for project, hours in project_hours:
            output.append(f"  {project:<60} {hours:>6.2f} hrs")
            day_total += hours

        output.append("")
        output.append(f"  {'Daily Total:':<60} {day_total:>6.2f} hrs")
        output.append("")

        grand_total_hours += day_total

    output.append("=" * 80)
    output.append(f"  {'TOTAL HOURS:':<60} {grand_total_hours:>6.2f} hrs")
    output.append("=" * 80)

    return "\n".join(output)


def parse_date_arg(arg: str) -> Optional[datetime]:
    """Parse command line argument as either days ago or YYYYMMDD date."""
    # Try parsing as YYYYMMDD first
    try:
        return datetime.strptime(arg, '%Y%m%d')
    except ValueError:
        pass

    # Try parsing as integer (days ago)
    try:
        days = int(arg)
        return datetime.now() - timedelta(days=days)
    except (ValueError, OverflowError):
        pass

    return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate timesheets from Claude Code message history. Groups activity into 15-minute blocks.",
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
  %(prog)s --db custom.db                     # Use custom database file

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
        default='claude_messages.db',
        help='Database file path (default: claude_messages.db)'
    )

    args = parser.parse_args()

    # Connect to database
    try:
        conn = sqlite3.connect(args.db)
    except sqlite3.Error as e:
        print(f"Error: Could not connect to database {args.db}: {e}", file=sys.stderr)
        print(f"Have you run parse_claude_messages.py to import data?", file=sys.stderr)
        sys.exit(1)

    try:
        # Parse date/days argument
        since_date = datetime.now() - timedelta(days=7)

        if args.date_or_days:
            parsed = parse_date_arg(args.date_or_days)
            if parsed:
                since_date = parsed
            else:
                print(f"Error: Invalid argument '{args.date_or_days}'.", file=sys.stderr)
                print(f"Use a number of days (e.g., 7) or date in YYYYMMDD format (e.g., 20250101)", file=sys.stderr)
                sys.exit(1)

        # Fetch messages since date
        messages = get_messages_since_date(conn, since_date)

        if not messages:
            print(f"No messages found since {since_date.strftime('%Y-%m-%d')}.")
            print(f"Database: {args.db}")
            return

        # Group into 15-minute chunks
        activity = group_by_15min_chunks(messages, args.project_filter, args.exclude_filter, args.group_time)

        if not activity:
            filter_msg = []
            if args.project_filter:
                filter_msg.append(f"filter '{args.project_filter}'")
            if args.exclude_filter:
                filter_msg.append(f"exclude '{args.exclude_filter}'")
            if filter_msg:
                print(f"No messages found matching {' and '.join(filter_msg)}.")
            else:
                print("No messages found.")
            return

        # Format and display timesheet
        timesheet = format_timesheet(activity, since_date, args.project_filter, args.exclude_filter, args.group_time)
        print(timesheet)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
