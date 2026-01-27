# Taskr Documentation

> AI-native task management for Claude Code and MCP-compatible agents

## Why Taskr?

**You're paying too much for project management.**

Jira, Asana, Linear—they all charge per seat, add complexity, and fragment your workflow. Your code lives in GitHub, but your tasks live somewhere else. AI agents can't see both at once.

**Taskr fixes this.** It's free, open-source, and puts tasks where they belong: right next to your code in GitHub. Claude Code can see issues, PRs, and projects in the same context window. No more copy-pasting, no more tab-switching, no more synchronization problems.

## Modules

| Module | What It Does | Why You Want It |
|--------|--------------|-----------------|
| [Tasks](modules/tasks.md) | CRUD for work items | Track what needs doing |
| [Devlogs](modules/devlogs.md) | AI memory system | Claude remembers across sessions |
| [Sessions](modules/sessions.md) | Work coordination | Multiple agents, no conflicts |
| [GitHub](modules/github.md) | Projects V2 integration | The missing GitHub MCP tools |
| [Triage](modules/triage.md) | Workflow orchestration | "What should I do next?" |

## Quick Start

```bash
pip install taskr-mcp
taskr-mcp
```

Add to Claude Code config (`~/.claude/claude_code_config.json`):

```json
{
  "mcpServers": {
    "taskr": {
      "command": "taskr-mcp",
      "env": {
        "GITHUB_TOKEN": "your-github-token"
      }
    }
  }
}
```

Then just say: **"use taskr triage to ______"**

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code                              │
├─────────────────────────────────────────────────────────────┤
│                     Taskr MCP Server                         │
├──────────────┬──────────────┬──────────────┬────────────────┤
│    Tasks     │   Devlogs    │   Sessions   │     GitHub     │
├──────────────┴──────────────┴──────────────┴────────────────┤
│              Database (PostgreSQL or SQLite)                 │
└─────────────────────────────────────────────────────────────┘
```

## Database Options

| Option | Best For | Setup |
|--------|----------|-------|
| **SQLite** | Solo developers | Zero config (default) |
| **PostgreSQL** | Teams, shared state | Set `TASKR_DATABASE_URL` |

SQLite works out of the box. PostgreSQL adds full-text search with ranking.

## What Makes Taskr Different

### 1. Code and Tasks Together

GitHub becomes your single source of truth. Issues describe the work, code implements it, devlogs explain decisions. AI sees everything.

### 2. AI Memory That Persists

Devlogs survive context windows, sessions, and agent restarts. Claude can search 6 months of decisions in milliseconds.

### 3. Multi-Agent Coordination

Work claiming prevents two agents from fixing the same bug. Sessions track who's doing what. Handoff notes enable continuity.

### 4. Workflow Guidance

`taskr_triage` tells Claude what to do next. No prompt engineering required—just "use taskr triage" and go.

## Further Reading

- [Tasks Module](modules/tasks.md) - Work item tracking
- [Devlogs Module](modules/devlogs.md) - AI memory system
- [Sessions Module](modules/sessions.md) - Agent coordination
- [GitHub Module](modules/github.md) - Projects V2 integration
- [Triage Module](modules/triage.md) - Workflow orchestration
- [Research: Triage Case Study](research/taskr-triage-workflow-case-study.md) - Real-world example
