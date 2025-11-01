# Claude Code Timesheets

Generate timesheets from your Claude Code session history. This tool parses JSONL conversation logs and produces billable hour reports grouped by project and day.

## Overview

Claude Code stores conversation history in JSONL files at `~/.claude/projects/`. This toolset:
1. Imports message timestamps into a SQLite database
2. Generates timesheets grouped by 15-minute activity blocks
3. Filters by date range and project

## Installation

No external dependencies required - uses Python 3 standard library only.

```bash
git clone <your-repo>
cd cctimesheets
chmod +x parse_claude_messages.py generate_timesheet.py
```

## Usage

### 1. Import Messages

First, parse all JSONL files and populate the database:

```bash
# Import all messages from ~/.claude/projects
python3 parse_claude_messages.py

# Or test with a single file
python3 parse_claude_messages.py ~/.claude/projects/[project]/[session-id].jsonl
```

This creates `claude_messages.db` with all message timestamps.

### 2. Generate Timesheets

```bash
# Last 7 days (default)
python3 generate_timesheet.py

# Last N days
python3 generate_timesheet.py 14

# Since specific date (YYYYMMDD format)
python3 generate_timesheet.py 20251001

# Filter by project (supports wildcards)
python3 generate_timesheet.py --project-filter "*wallfacer*"

# Combine date and filter
python3 generate_timesheet.py 20251001 --project-filter "*pitch*"
```

## How It Works

### Time Calculation

Messages are grouped into **15-minute blocks**. Multiple messages within the same 15-minute window count as one block (0.25 hours).

**Example:**
- Messages at 14:42, 14:43, 14:44, 14:50 → 2 blocks (14:45-15:00 and 15:00-15:15) = 0.5 hours
- Gap from 16:00 to 18:00 with no messages → Not counted

This provides a realistic estimate of active work time, filtering out breaks and idle periods.

### Project Names

Directory names are cleaned for readability:
- `-Users-pdenya-Code-wallfacer-monorepo` → `Users/pdenya/Code/wallfacer/monorepo`
- Dashes converted to slashes

### Database Schema

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    project_name TEXT NOT NULL,
    message_type TEXT,
    uuid TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

## Example Output

```
================================================================================
CLAUDE CODE TIMESHEET - SINCE OCTOBER 01, 2025 - FILTER: *wallfacer*
================================================================================

Friday, October 31, 2025
--------------------------------------------------------------------------------
  Users/pdenya/Code/wallfacer/monorepo                           4.75 hrs
  Users/pdenya/Code/wallfacer/droplet                            0.75 hrs

  Daily Total:                                                   5.50 hrs

...

================================================================================
  TOTAL HOURS:                                                  28.75 hrs
================================================================================
```

## Re-importing Data

To refresh the database with new messages:

```bash
# Clear and reimport all
rm claude_messages.db
python3 parse_claude_messages.py
```

## Files

- `parse_claude_messages.py` - Import JSONL files into SQLite
- `generate_timesheet.py` - Generate formatted timesheet reports
- `claude_messages.db` - SQLite database (generated)
- `README.md` - This file

## Notes

- Only messages with both `timestamp` and `sessionId` fields are imported
- Message types include: `user`, `assistant`, `system`, etc.
- All timestamps are stored in ISO 8601 format (UTC)
- Project filtering is case-insensitive and supports glob patterns (`*`, `?`)

## License

MIT
