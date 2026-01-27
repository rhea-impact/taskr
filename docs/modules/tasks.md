# Tasks Module

> CRUD operations for work items

## Executive Summary

**The Problem**: You have work to track. You're currently using:
- A SaaS tool that charges per seat
- A spreadsheet that gets out of sync
- Issues scattered across repos with no central view
- Your memory (which fails at 3 AM)

**The Solution**: Taskr tasks are a lightweight tracking layer that:
- Stores work items in your database (SQLite or PostgreSQL)
- Integrates with Claude Code via MCP
- Links to GitHub issues for public visibility
- Costs nothing

**When to Use Tasks vs. GitHub Issues**:
- Use **GitHub Issues** for public-facing work (bug reports, feature requests)
- Use **Taskr Tasks** for internal tracking, personal todos, or cross-repo coordination

## Tools

| Tool | Description |
|------|-------------|
| `taskr_list` | List tasks with filters |
| `taskr_create` | Create a new task |
| `taskr_show` | Get task details |
| `taskr_update` | Update task fields |
| `taskr_search` | Full-text search |
| `taskr_assign` | Assign to a user |
| `taskr_close` | Mark as complete |

## Task Properties

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `title` | string | Short description |
| `description` | string | Detailed markdown content |
| `status` | enum | `open`, `in_progress`, `done`, `cancelled` |
| `priority` | enum | `low`, `medium`, `high`, `critical` |
| `assignee` | string | Username |
| `tags` | array | Labels for filtering |
| `created_by` | string | Who created it |
| `due_at` | datetime | Optional deadline |

## Usage Examples

### Create a task

```python
taskr_create(
    title="Implement user authentication",
    description="Add OAuth2 login flow with GitHub provider",
    priority="high",
    tags=["auth", "security"]
)
```

### List high-priority tasks

```python
taskr_list(priority="high", status="open")
```

### Search for related work

```python
taskr_search(query="authentication OAuth")
```

### Update task status

```python
taskr_update(task_id="abc123", status="in_progress")
```

### Close a completed task

```python
taskr_close(task_id="abc123")
```

## Status Flow

```
open → in_progress → done
  ↓
cancelled
```

- **open**: Not started
- **in_progress**: Someone is working on it
- **done**: Completed (sets `completed_at`)
- **cancelled**: Won't be done

## Best Practices

### 1. One Task Per Deliverable

Bad:
```
"Fix bugs and add tests and refactor database"
```

Good:
```
"Fix null pointer in login handler"
"Add unit tests for auth service"
"Refactor database connection pooling"
```

### 2. Use Priority Sparingly

Not everything is critical. Reserve `critical` for:
- Production outages
- Security vulnerabilities
- Blocking other teams

### 3. Close Tasks Promptly

A pile of done-but-not-closed tasks creates noise. Use `taskr_close` when work is verified.

### 4. Link to GitHub Issues

For public-facing work, create a GitHub issue and reference it in the task description:

```python
taskr_create(
    title="Fix login timeout",
    description="See rhea-impact/taskr#42 for user reports"
)
```

## Database Schema

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',
    priority TEXT DEFAULT 'medium',
    assignee TEXT,
    tags TEXT[], -- JSON array in SQLite
    created_by TEXT,
    due_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP -- soft delete
);
```

## Related Modules

- [Devlogs](devlogs.md) - Document decisions made while working on tasks
- [Sessions](sessions.md) - Track which agent is working on which task
- [GitHub](github.md) - Link tasks to GitHub issues and projects
