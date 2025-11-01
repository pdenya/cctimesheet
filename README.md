# Claude Code Timesheets

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Generate professional timesheets from your [Claude Code](https://claude.com/claude-code) session history. Automatically track billable hours across projects with intelligent activity grouping.

## Features

- 📊 **Accurate Time Tracking** - Groups messages into 15-minute activity blocks
- 🔍 **Project Filtering** - Filter timesheets by project using glob patterns
- 📅 **Flexible Date Ranges** - View by days ago or specific date ranges
- 💾 **SQLite Storage** - Fast, local database with indexed queries
- 🎯 **Zero Dependencies** - Pure Python 3 standard library
- 🚀 **Simple CLI** - Intuitive command-line interface with comprehensive help

## Quick Start

### Installation

```bash
git clone https://github.com/pdenya/cctimesheet.git
cd cctimesheet
chmod +x parse_claude_messages.py generate_timesheet.py
```

No additional dependencies required - uses Python 3 standard library only.

### First-Time Setup

Import your Claude Code conversation history:

```bash
python3 parse_claude_messages.py
```

This scans `~/.claude/projects/` and imports all message timestamps into `claude_messages.db`.

## Usage Examples

### Basic Timesheets

```bash
# Last 7 days (default)
python3 generate_timesheet.py

# Last 14 days
python3 generate_timesheet.py 14

# Since October 1, 2025
python3 generate_timesheet.py 20251001
```

### Project Filtering

```bash
# All wallfacer projects (last 7 days)
python3 generate_timesheet.py -p "*wallfacer*"

# Pitchfriendly project since Oct 1
python3 generate_timesheet.py 20251001 -p "*pitch*"

# Backend projects (last 30 days)
python3 generate_timesheet.py 30 --project-filter "*backend"
```

### Advanced Options

```bash
# Use custom database
python3 generate_timesheet.py --db ~/timesheets/october.db

# Import from custom location
python3 parse_claude_messages.py --projects-dir /path/to/projects

# View help
python3 generate_timesheet.py --help
python3 parse_claude_messages.py --help
```

## How It Works

### Time Calculation Method

Claude Code Timesheets uses **15-minute activity blocks** to calculate billable hours:

- Messages are grouped into 15-minute intervals
- Multiple messages in the same interval count as one block (0.25 hours)
- Gaps with no activity are automatically excluded (breaks, idle time)

**Example:**
```
14:42 - User message
14:43 - Assistant response  } → 1 block at 14:30-14:45
14:44 - User follow-up
14:50 - Assistant response  } → 1 block at 14:45-15:00

Total: 2 blocks × 0.25 hours = 0.5 billable hours
```

This method provides accurate tracking of actual work time while filtering out breaks, lunch hours, and other idle periods.

### Data Source

Claude Code stores conversation history as JSONL files in `~/.claude/projects/`. Each project directory contains session files with:
- Message timestamps (ISO 8601 format)
- Session IDs
- Message types (user, assistant, system)
- Message UUIDs

The parser extracts these timestamps and indexes them in SQLite for fast querying.

## Output Example

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

## Maintenance

### Updating Your Data

To refresh the database with new Claude Code sessions:

```bash
rm claude_messages.db
python3 parse_claude_messages.py
```

The import process typically takes a few seconds for hundreds of sessions.

### Database Schema

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    project_name TEXT NOT NULL,
    message_type TEXT,
    uuid TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast queries
CREATE INDEX idx_session_id ON messages(session_id);
CREATE INDEX idx_timestamp ON messages(timestamp);
CREATE INDEX idx_project_name ON messages(project_name);
```

## Requirements

- **Python**: 3.8 or higher
- **Operating System**: macOS, Linux, or Windows
- **Claude Code**: Installed with conversation history in `~/.claude/projects/`

## FAQ

**Q: Why 15-minute blocks instead of exact time?**
A: 15-minute blocks provide a standard billing increment and naturally filter out idle time while remaining accurate for professional timesheets.

**Q: Can I use this for invoicing?**
A: Yes! The output provides verifiable timestamps and session IDs for audit purposes. Consider adding your own verification process.

**Q: Does this modify my Claude Code data?**
A: No. The tool only reads JSONL files. All data is stored separately in `claude_messages.db`.

**Q: What if I have multiple Claude Code installations?**
A: Use `--projects-dir` to specify the location of your `.claude/projects` directory.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request to [github.com/pdenya/cctimesheet](https://github.com/pdenya/cctimesheet).

## License

MIT License
