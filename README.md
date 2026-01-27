# Taskr

[![CI](https://github.com/rhea-impact/taskr/actions/workflows/ci.yml/badge.svg)](https://github.com/rhea-impact/taskr/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

AI-native task management for Claude Code and MCP-compatible agents.

## Features

- **Task Management** - Create, track, and search tasks with full CRUD operations
- **Development Logs** - Persistent AI memory across sessions (decisions, bugfixes, patterns)
- **Agent Sessions** - Coordinate multi-agent work with handoffs and work claiming
- **GitHub Integration** - Projects V2, issues, and PRs built-in (no plugin needed)
- **Dual Database Support** - PostgreSQL for teams, SQLite for local use
- **Plugin Architecture** - Extend with Skillflows, Supabase, and custom integrations

## Quick Start

### Local Setup (SQLite - Zero Config)

```bash
pip install taskr-mcp
taskr-mcp
```

Add to your Claude Code MCP config (`~/.claude/claude_code_config.json`):
```json
{
  "mcpServers": {
    "taskr": {
      "command": "taskr-mcp",
      "env": {
        "GITHUB_TOKEN": "your-github-token"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-github-token"
      }
    }
  }
}
```

> **Note:** Create a [GitHub Personal Access Token](https://github.com/settings/tokens) with `repo` and `project` scopes. Use the same token for both servers.
>
> **Why both?** Taskr handles project workflows (create projects, atomic issue+project linking). GitHub MCP handles standard operations (search, comment, read issues). Together they provide complete GitHub integration.

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

### GitHub Integration (Complements GitHub MCP)
These tools fill gaps in the GitHub MCP or provide leaner interfaces:
- `github_project_create` - Create GitHub Project V2 (GitHub MCP can't do this)
- `github_project_items` - List project items with minimal output (saves tokens)
- `github_create_issue_in_project` - Create issue AND add to project atomically
- `github_pr_create` - Create PR with smart issue linking (auto-adds to project)
- `github_project_add_item` - Add issue/PR to project
- `github_project_close` / `github_project_reopen` - Manage project lifecycle
- `github_get_issue_id` / `github_get_org_id` - Get node IDs for API calls

> **Note:** Use standard GitHub MCP tools (`mcp__github__*`) for reading issues, searching, commenting, etc. These taskr tools are specifically for project-centric workflows.

### Utility
- `taskr_triage` - Workflow guidance
- `taskr_health` - Database health check
- `taskr_migrate` - Run pending migrations

## Plugins

Install optional plugins for extended functionality:

```bash
# Workflow definitions
pip install taskr-plugin-skillflows

# Supabase deployments
pip install taskr-plugin-supabase
```

Enable in config:
```yaml
plugins:
  enabled:
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
