# Taskr

[![CI](https://github.com/rhea-impact/taskr/actions/workflows/ci.yml/badge.svg)](https://github.com/rhea-impact/taskr/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

AI-native task management for Claude Code and MCP-compatible agents.

## Features

- **Task Management** - Create, track, and search tasks with full CRUD operations
- **Development Logs** - Persistent AI memory across sessions (decisions, bugfixes, patterns)
- **Agent Sessions** - Coordinate multi-agent work with handoffs and work claiming
- **Dual Database Support** - PostgreSQL for teams, SQLite for local use
- **Plugin Architecture** - Extend with GitHub, Skillflows, Supabase integrations

## Quick Start

### Local Setup (SQLite - Zero Config)

```bash
pip install taskr-mcp
taskr-mcp
```

Add to your Claude Code MCP config:
```json
{
  "mcpServers": {
    "taskr": {
      "command": "taskr-mcp"
    }
  }
}
```

### Team Setup (PostgreSQL)

```bash
pip install taskr-mcp

# Configure database
export TASKR_DATABASE_URL="postgresql://user:pass@host:5432/taskr"

# Run migrations
taskr-mcp migrate

# Start server
taskr-mcp
```

## Configuration

Create `~/.taskr/config.yaml`:

```yaml
database:
  type: sqlite  # or "postgres"
  sqlite:
    path: ~/.taskr/taskr.db
  postgres:
    url_env: TASKR_DATABASE_URL

identity:
  author: your-name
  agent_id: claude-code

plugins:
  enabled:
    - github
```

## Core Tools

### Task Management
- `taskr_list` - List tasks with filters
- `taskr_create` - Create new task
- `taskr_show` - Show task details
- `taskr_update` - Update task
- `taskr_search` - Search tasks
- `taskr_assign` - Assign to user
- `taskr_close` - Mark complete

### Development Logs (AI Memory)
- `devlog_add` - Create log entry
- `devlog_list` - List entries
- `devlog_search` - Full-text search
- `devlog_get` - Get full content

### Agent Sessions
- `session_start` - Start session with context
- `session_end` - End with handoff notes
- `claim_work` - Atomically claim work item
- `release_work` - Release claimed work
- `what_changed` - See recent changes

### SQL Tools
- `taskr_sql_query` - Execute ad-hoc SQL queries
- `taskr_sql_explain` - Analyze query performance
- `taskr_sql_migrate` - Run SQL with audit logging

### Utility
- `taskr_triage` - Workflow guidance
- `taskr_health` - Database health check
- `taskr_migrate` - Run pending migrations

## Plugins

Install optional plugins for extended functionality:

```bash
# GitHub Projects V2 integration
pip install taskr-plugin-github

# Workflow definitions
pip install taskr-plugin-skillflows
```

Enable in config:
```yaml
plugins:
  enabled:
    - github
    - skillflows
```

## Development

```bash
# Clone
git clone https://github.com/rhea-impact/taskr.git
cd taskr

# Install in dev mode
pip install -e packages/taskr-core
pip install -e packages/taskr-mcp

# Run tests
pytest tests/
```

## License

MIT License - see [LICENSE](LICENSE)
