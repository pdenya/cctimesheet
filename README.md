# Claude Code Timesheets

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Generate professional timesheets from your [Claude Code](https://claude.com/claude-code) session history. Automatically track billable hours across projects with intelligent activity grouping.

**One command does it all**: `cctimesheet` automatically parses your Claude Code messages and generates a timesheet—no manual database setup required.

## Features

- 📊 **Accurate Time Tracking** - Groups messages into 15-minute activity blocks
- 🔍 **Project Filtering** - Filter timesheets by project using glob patterns
- 📅 **Flexible Date Ranges** - View by days ago or specific date ranges
- 💾 **Smart Database** - Automatic temporary database creation and cleanup
- 🎯 **Zero Dependencies** - Pure Python 3 standard library
- 🚀 **Simple CLI** - Single command workflow with comprehensive help

## Quick Start

### Installation with pipx (Recommended)

```bash
# Install directly from GitHub
pipx install git+https://github.com/pdenya/cctimesheet.git

# Or install from local clone
git clone https://github.com/pdenya/cctimesheet.git
cd cctimesheet
pipx install .
```

No additional dependencies required - uses Python 3 standard library only.

### Alternative: Install with pip

```bash
pip install git+https://github.com/pdenya/cctimesheet.git
```

## Usage Examples

The `cctimesheet` command automatically parses your Claude Code messages and generates a timesheet in one step.

### Basic Timesheets

```bash
# Last 7 days (default)
cctimesheet

# Last 14 days
cctimesheet 14

# Since October 1, 2025
cctimesheet 20251001
```

### Project Filtering

```bash
# All acme projects (last 7 days)
cctimesheet -p "*acme*"

# Specific client project since Oct 1
cctimesheet 20251001 -p "*client*"

# Backend projects (last 30 days)
cctimesheet 30 --project-filter "*backend"
```

### Advanced Options

```bash
# Group time by unique timeblocks (don't double-count same block across projects)
cctimesheet -p "*client*" -g

# Combine filters with grouped time
cctimesheet 30 -p "*api*" -e "*test*" --group-time

# Use persistent database for faster subsequent runs
cctimesheet --db ~/timesheets/october.db --keep-db

# Parse from custom location
cctimesheet --projects-dir /path/to/projects

# View help
cctimesheet --help
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
CLAUDE CODE TIMESHEET - SINCE OCTOBER 01, 2025 - FILTER: *acme*
================================================================================

Friday, October 31, 2025
--------------------------------------------------------------------------------
  Users/pdenya/Code/acme/monorepo                                4.75 hrs
  Users/pdenya/Code/acme/api                                     0.75 hrs

  Daily Total:                                                   5.50 hrs

...

================================================================================
  TOTAL HOURS:                                                  28.75 hrs
================================================================================
```

## Maintenance

### How the Database Works

By default, `cctimesheet` creates a temporary database each time you run it. The database is automatically cleaned up after generating the timesheet. This means:
- ✅ No manual database management required
- ✅ Always uses the latest Claude Code data
- ✅ No leftover files to clean up

### Using a Persistent Database (Optional)

For faster repeated queries, you can use a persistent database:

```bash
# First run creates the database
cctimesheet --db my_timesheet.db --keep-db

# Subsequent runs are faster (reuses existing data)
cctimesheet --db my_timesheet.db

# To refresh with new sessions, delete and recreate
rm my_timesheet.db
cctimesheet --db my_timesheet.db --keep-db
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

**Q: What does the `--group-time` flag do?**
A: By default, if you work on multiple projects during the same 15-minute block, each project counts that block separately. With `--group-time` (`-g`), unique timeblocks are counted only once across all filtered projects, preventing double-counting when multitasking.

**Q: Can I use this for invoicing?**
A: Yes! The output provides verifiable timestamps and session IDs for audit purposes. Consider adding your own verification process.

**Q: Does this modify my Claude Code data?**
A: No. The tool only reads JSONL files. All data is temporarily stored (or in a separate database if --db is used).

**Q: What if I have multiple Claude Code installations?**
A: Use `--projects-dir` to specify the location of your `.claude/projects` directory.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request to [github.com/pdenya/cctimesheet](https://github.com/pdenya/cctimesheet).

## License

MIT License
