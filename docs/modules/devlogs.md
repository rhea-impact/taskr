# Devlogs Module

> Persistent AI memory across sessions

## Executive Summary

**The Problem**: Every time Claude starts a new session, it forgets:
- Why you chose PostgreSQL over MySQL
- How you fixed that weird timezone bug last month
- What patterns work in your codebase
- Lessons learned from failed approaches

You end up re-explaining context, re-discovering solutions, and watching AI make the same mistakes twice.

**The Solution**: Devlogs are persistent memory that Claude can search:
- Every decision, bugfix, and pattern gets recorded
- Full-text search finds relevant history in milliseconds
- Memory survives context windows, sessions, and restarts
- Your AI assistant gets smarter over time

**Why This Matters**: Teams spend 20-40% of engineering time on knowledge transfer and context-switching. Devlogs compress that to a single search query.

## Tools

| Tool | Description |
|------|-------------|
| `devlog_add` | Create a log entry |
| `devlog_list` | List entries with filters |
| `devlog_get` | Get full content |
| `devlog_search` | Full-text search |
| `devlog_update` | Update an entry |
| `devlog_delete` | Soft delete |

## Categories

| Category | When to Use |
|----------|------------|
| `feature` | New functionality added |
| `bugfix` | Bug identified and fixed |
| `decision` | Architectural choice made |
| `pattern` | Reusable pattern discovered |
| `research` | Investigation findings |
| `refactor` | Code restructuring |
| `config` | Configuration changes |
| `note` | General observations |

## Entry Properties

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `category` | enum | Type of entry |
| `title` | string | One-line summary |
| `content` | string | Full markdown content |
| `author` | string | Human author |
| `agent_id` | string | AI agent that created it |
| `service_name` | string | Related project/service |
| `tags` | array | Labels for filtering |
| `metadata` | object | Structured data |

## Usage Examples

### Record a decision

```python
devlog_add(
    category="decision",
    title="Use PostgreSQL for production, SQLite for local dev",
    content="""
# Context
We need a database that supports both team use and solo developers.

# Decision
- PostgreSQL for teams (full-text search, concurrent writes)
- SQLite for local (zero config, portable)

# Rationale
- SQLite can't handle multiple agents writing simultaneously
- PostgreSQL is overkill for a single developer
- Adapter pattern abstracts the difference
    """,
    service_name="taskr",
    tags=["database", "architecture"]
)
```

### Document a bugfix

```python
devlog_add(
    category="bugfix",
    title="Fixed timezone handling in session duration",
    content="""
# Bug
Session durations showed negative values when ended.

# Root Cause
`started_at` was stored as naive datetime, `ended_at` as ISO with timezone.
Subtraction failed due to mismatched types.

# Fix
Normalize both to UTC before calculation:
```python
if isinstance(started, str):
    started = datetime.fromisoformat(started.replace("Z", "+00:00"))
```

# Prevention
Added type checking in tests.
    """,
    service_name="taskr",
    tags=["datetime", "sessions"]
)
```

### Search for prior solutions

```python
devlog_search(query="timezone datetime UTC")
# Returns: entries ranked by relevance
```

### List recent decisions

```python
devlog_list(category="decision", limit=10)
```

## Search Behavior

| Database | Method | Features |
|----------|--------|----------|
| PostgreSQL | `tsvector/tsquery` | Ranked results, stemming, phrase matching |
| SQLite | `LIKE wildcards` | Basic substring matching |

PostgreSQL provides better search quality. SQLite still works for smaller projects.

## Best Practices

### 1. Log Decisions Immediately

Don't wait until the end of a session. Capture decisions as you make them:

```python
# Good: Document right after deciding
devlog_add(category="decision", title="Using httpx instead of requests", ...)

# Bad: Try to remember what you decided 2 hours later
```

### 2. Use Descriptive Titles

The title appears in search results. Make it scannable:

```
Bad:  "Fixed bug"
Good: "Fixed null pointer in OAuth callback handler"

Bad:  "Database decision"
Good: "Use connection pooling with min=5, max=20 for production"
```

### 3. Include Context

Future-you (or future-Claude) needs to understand **why**, not just **what**:

```markdown
# Context
What problem were you solving?

# Decision / Fix / Pattern
What did you do?

# Rationale
Why this approach over alternatives?

# Related
Links to issues, PRs, docs
```

### 4. Tag Consistently

Establish a tagging convention for your project:
- Service names: `taskr`, `auth-service`, `frontend`
- Domains: `database`, `api`, `security`
- Urgency: `hotfix`, `tech-debt`

### 5. Search Before Creating

Before implementing something new:

```python
devlog_search(query="authentication OAuth pattern")
```

You might find that past-you already solved this problem.

## The Learning Loop

```
┌─────────────┐
│   Problem   │
└──────┬──────┘
       ▼
┌─────────────┐     ┌─────────────┐
│   Search    │────▶│   Found?    │──yes──▶ Reuse pattern
│   devlogs   │     └─────────────┘
└─────────────┘            │
                          no
                           ▼
                    ┌─────────────┐
                    │   Solve     │
                    │   problem   │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │   Log to    │
                    │   devlog    │
                    └─────────────┘
```

Over time, the devlog becomes a knowledge base specific to your codebase.

## Coming Soon: Deep Sleep

For teams using taskr-worker (background processing), devlogs will automatically:
- Consolidate related entries
- Extract key patterns
- Trim stale information
- Build connections between entries

This is the foundation for AI that truly learns your codebase.

## Related Modules

- [Sessions](sessions.md) - Track when devlogs were created
- [Tasks](tasks.md) - Link devlogs to work items
- [Triage](triage.md) - Devlog search is part of the triage workflow
