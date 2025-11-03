"""
Generate a timesheet from Claude Code messages.
Groups activity into 15-minute chunks per project per day.
"""

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

    # Strip common prefixes for cleaner display
    if project_name.startswith('Users/pdenya/Code/'):
        project_name = project_name[18:]  # len('Users/pdenya/Code/')
    elif project_name.startswith('Users/pdenya/'):
        project_name = '~/' + project_name[13:]  # len('Users/pdenya/')

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
            if len(project_names) == 1:
                combined_name = project_names[0]
            else:
                combined_name = "Multiple projects: " + ", ".join(sorted(project_names))
            grouped_activity[date_str][combined_name] = all_blocks
        return grouped_activity

    return activity


def calculate_hours(time_blocks: set) -> float:
    """Calculate total hours from set of 15-minute time blocks."""
    return len(time_blocks) * 0.25


def get_week_start(date_obj: datetime) -> datetime:
    """Get the Monday of the week for a given date."""
    # 0 = Monday, 6 = Sunday
    days_since_monday = date_obj.weekday()
    return date_obj - timedelta(days=days_since_monday)


def calculate_weekly_summaries(activity: Dict[str, Dict[str, set]]) -> List[Tuple[datetime, datetime, float]]:
    """
    Calculate weekly summaries from activity data.

    Returns: List of (week_start, week_end, total_hours) tuples, sorted newest first
    """
    weekly_totals = defaultdict(float)

    for date_str, projects in activity.items():
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        week_start = get_week_start(date_obj)

        # Calculate total hours for this day
        day_total = sum(calculate_hours(blocks) for blocks in projects.values())
        weekly_totals[week_start] += day_total

    # Convert to list of tuples with week ranges
    weekly_summary = []
    for week_start, total_hours in weekly_totals.items():
        week_end = week_start + timedelta(days=6)
        weekly_summary.append((week_start, week_end, total_hours))

    # Sort by week start (newest first)
    weekly_summary.sort(key=lambda x: x[0], reverse=True)

    return weekly_summary


def format_timesheet(activity: Dict[str, Dict[str, set]], since_date: datetime, project_filter: Optional[str] = None, exclude_filter: Optional[str] = None, group_time: bool = False) -> str:
    """Format the timesheet for display."""
    output = []

    # Header
    output.append("")
    output.append("=" * 80)
    output.append("CLAUDE CODE TIMESHEET")
    output.append("=" * 80)

    # Calculate date range for subheader
    days_ago = (datetime.now() - since_date).days
    if days_ago <= 1:
        range_text = "Today"
    elif days_ago <= 7:
        range_text = f"Last {days_ago} days"
    else:
        range_text = f"Since {since_date.strftime('%B %d, %Y')}"

    # Add filters to subheader
    filters = []
    if project_filter:
        filters.append(f"Filter: {project_filter}")
    if exclude_filter:
        filters.append(f"Exclude: {exclude_filter}")
    if group_time:
        filters.append("Grouped time")

    if filters:
        range_text += " | " + " | ".join(filters)

    output.append(range_text)
    output.append("")

    # Calculate weekly summaries
    weekly_summaries = calculate_weekly_summaries(activity)

    # Display weekly summaries
    if len(weekly_summaries) > 1:
        output.append("WEEKLY SUMMARY")
        output.append("-" * 80)
        for week_start, week_end, total_hours in weekly_summaries:
            week_range = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
            output.append(f"  {week_range:<60} {total_hours:>6.2f} hrs")
        output.append("")
        output.append("")

    # Calculate grand total
    grand_total_hours = sum(hours for _, _, hours in weekly_summaries)

    # Display daily breakdown
    output.append("DAILY BREAKDOWN")
    output.append("-" * 80)

    # Sort dates newest first
    sorted_dates = sorted(activity.keys(), reverse=True)

    for date_str in sorted_dates:
        projects = activity[date_str]

        # Parse date for nice formatting
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = date_obj.strftime('%A')
        formatted_date = date_obj.strftime('%b %d, %Y')

        output.append("")
        output.append(f"{day_name}, {formatted_date}")
        output.append("")

        # Sort projects by hours (descending)
        project_hours = [(proj, calculate_hours(blocks)) for proj, blocks in projects.items()]
        project_hours.sort(key=lambda x: x[1], reverse=True)

        day_total = 0

        for project, hours in project_hours:
            output.append(f"  {project:<65} {hours:>5.2f} hrs")
            day_total += hours

        output.append(f"  {'-' * 65} {'-' * 9}")
        output.append(f"  {'Daily Total':<65} {day_total:>5.2f} hrs")

    # Grand total
    output.append("")
    output.append("=" * 80)
    output.append(f"  {'TOTAL HOURS':<65} {grand_total_hours:>5.2f} hrs")
    output.append("=" * 80)
    output.append("")

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


def generate_timesheet(db_path: str, date_or_days: Optional[str] = None, project_filter: Optional[str] = None, exclude_filter: Optional[str] = None, group_time: bool = False) -> str:
    """
    Generate a timesheet from the database.

    Args:
        db_path: Path to SQLite database file
        date_or_days: Number of days ago or YYYYMMDD date string (default: 7 days)
        project_filter: Optional glob pattern to filter projects
        exclude_filter: Optional glob pattern to exclude projects
        group_time: If True, count unique timeblocks across all projects

    Returns:
        Formatted timesheet string
    """
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        raise RuntimeError(f"Could not connect to database {db_path}: {e}")

    try:
        # Parse date/days argument
        since_date = datetime.now() - timedelta(days=7)

        if date_or_days:
            parsed = parse_date_arg(date_or_days)
            if parsed:
                since_date = parsed
            else:
                raise ValueError(f"Invalid argument '{date_or_days}'. Use a number of days (e.g., 7) or date in YYYYMMDD format (e.g., 20250101)")

        # Fetch messages since date
        messages = get_messages_since_date(conn, since_date)

        if not messages:
            return f"No messages found since {since_date.strftime('%Y-%m-%d')}."

        # Group into 15-minute chunks
        activity = group_by_15min_chunks(messages, project_filter, exclude_filter, group_time)

        if not activity:
            filter_msg = []
            if project_filter:
                filter_msg.append(f"filter '{project_filter}'")
            if exclude_filter:
                filter_msg.append(f"exclude '{exclude_filter}'")
            if filter_msg:
                return f"No messages found matching {' and '.join(filter_msg)}."
            else:
                return "No messages found."

        # Format and return timesheet
        return format_timesheet(activity, since_date, project_filter, exclude_filter, group_time)

    finally:
        conn.close()
