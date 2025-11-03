# Claude Code Timesheets

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Pull timesheet data from your [Claude Code](https://claude.com/claude-code) session history. Easily track billable hours across projects with activity grouping and weekly summaries.

## Features

- **Accurate Time Tracking** - Groups messages into 15-minute activity blocks
- **Weekly Summaries** - Automatic weekly totals for easy billing and reporting
- **Project Filtering** - Filter and exclude projects using glob patterns
- **Flexible Date Ranges** - View by days ago or specific date ranges

## Output Example

```
================================================================================
CLAUDE CODE TIMESHEET
================================================================================
Since October 01, 2025 | Filter: *client-project*

WEEKLY SUMMARY
--------------------------------------------------------------------------------
  Oct 27 - Nov 02, 2025                                         19.75 hrs
  Oct 20 - Oct 26, 2025                                         21.50 hrs
  Oct 13 - Oct 19, 2025                                          5.25 hrs
  Oct 06 - Oct 12, 2025                                         11.00 hrs


DAILY BREAKDOWN
--------------------------------------------------------------------------------

Friday, Nov 01, 2025

  client-project/api                                                 3.50 hrs
  client-project/frontend                                            1.25 hrs
  ----------------------------------------------------------------- ---------
  Daily Total                                                        4.75 hrs

Thursday, Oct 31, 2025

  client-project/api                                                 5.00 hrs
  ----------------------------------------------------------------- ---------
  Daily Total                                                        5.00 hrs

[...]

================================================================================
  TOTAL HOURS                                                       57.50 hrs
================================================================================
```

## Quick Start

```bash
pipx run cctimesheet
```

### Or Install Permanently

```bash
pipx install cctimesheet
# Or with pip
pip install cctimesheet
```

## Usage Examples

The `cctimesheet` command automatically parses your Claude Code messages and generates a timesheet in one step.

### Basic Timesheets

```bash
# Last 7 days (default)
pipx run cctimesheet

# Last 14 days
pipx run cctimesheet 14

# Since October 1, 2025
pipx run cctimesheet 20251001
```

### Project/Client Filtering

```bash
# Only acme projects (directory filtering)
# -p is include (project filter), -e is exclude
# -g to group time, no double counting hours
pipx run cctimesheet -p "*acme*" -e "*unrelated-project-name*" -g
```

### Options

```bash

pipx run cctimesheet \
  # Use persistent database for faster subsequent runs
  --db ~/timesheets/october.db --keep-db \
  # Parse from custom claude code projects location
  --projects-dir /path/to/projects
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

## Maintenance

### How the Database Works

By default, `cctimesheet` creates a temporary database each time you run it. The database is automatically cleaned up after generating the timesheet. This means:
- ✅ No manual database management required
- ✅ Always uses the latest Claude Code data
- ✅ No leftover files to clean up

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

**Q: How are weekly summaries calculated?**
A: Weeks start on Monday and end on Sunday. The timesheet groups all activity within each week and displays the total hours for that week range. This makes it easy to see weekly billing totals at a glance.

**Q: What does the `--group-time` flag do?**
A: By default, if you work on multiple projects during the same 15-minute block, each project counts that block separately. With `--group-time` (`-g`), unique timeblocks are counted only once across all filtered projects, preventing double-counting when multitasking.  This is useful when you're **working for the same client across multiple directories**

**Q: Can I use this for invoicing?**
A: Yes! The output provides verifiable timestamps and session IDs for audit purposes. Consider adding your own verification process.

**Q: Does this modify my Claude Code data?**
A: No. The tool only reads JSONL files. All data is temporarily stored (or in a separate database if --db is used).

**Q: What if I have multiple Claude Code installations?**
A: Use `--projects-dir` to specify the location of your `.claude/projects` directory.

## Development

```bash
# Clone the repository
git clone https://github.com/pdenya/cctimesheet.git
cd cctimesheet

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .

# Run the command
cctimesheet --help
```

### Publishing to PyPI

```bash
# Install build and twine
pip install build twine

# Build the package
python3 -m build

# Upload to PyPI (requires API token)
twine upload dist/*
```

## Contributing

Contributions welcome! Please feel free to submit a Pull Request to [github.com/pdenya/cctimesheet](https://github.com/pdenya/cctimesheet).

## License

MIT License
