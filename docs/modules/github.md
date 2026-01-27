# GitHub Module

> Projects V2 integration that GitHub MCP doesn't provide

## Executive Summary

**The Problem**: GitHub has an official MCP server. But it can't:
- Create Projects V2
- List project items
- Add issues to projects
- Close or reopen projects

Why? Projects V2 are **organization-level**, not repo-level. The GitHub MCP focuses on repo operations.

**The Solution**: Taskr fills the gap with 10 GitHub tools that handle Projects V2 CRUD. Combined with GitHub MCP, you get complete GitHub coverage.

**Why This Matters**: GitHub Projects is free and built into your code workflow. With Taskr, Claude can manage your entire project board without leaving the conversation.

## Architecture

```
┌─────────────────────────────────────────────┐
│                Claude Code                   │
├─────────────────────┬───────────────────────┤
│   GitHub MCP        │      Taskr MCP        │
│   (Repo-level)      │   (Org/Project-level) │
├─────────────────────┼───────────────────────┤
│ • Issues (CRUD)     │ • Projects V2 (CRUD)  │
│ • PRs (CRUD)        │ • Issue→Project link  │
│ • Commits           │ • PR→Project link     │
│ • Search            │ • Project items       │
│ • Comments          │                       │
└─────────────────────┴───────────────────────┘
```

Use **both** servers together for complete GitHub integration.

## Tools

| Tool | Description |
|------|-------------|
| `github_project_create` | Create a new Project V2 |
| `github_project_items` | List items in a project |
| `github_project_add_item` | Add issue/PR to project |
| `github_project_close` | Archive a project |
| `github_project_reopen` | Restore an archived project |
| `github_create_issue_in_project` | Create issue AND link to project |
| `github_pr_create` | Create PR with issue linking |
| `github_get_issue_id` | Get node ID for an issue |
| `github_get_org_id` | Get node ID for org/user |

## Setup

Taskr needs a GitHub token with these scopes:
- `repo` - Access repositories
- `project` - Access Projects V2

```bash
export GITHUB_TOKEN="ghp_..."
```

Or in `~/.taskr/config.yaml`:

```yaml
github:
  token_env: GITHUB_TOKEN
```

## Usage Examples

### Create a project

```python
github_project_create(
    title="Q1 Roadmap",
    org="rhea-impact"
)
# Returns: {"id": "PVT_...", "number": 3, "url": "https://..."}
```

### List project items

```python
github_project_items(
    org="rhea-impact",
    project_number=1,
    minimal=True  # Reduces output size
)
# Returns: list of issues/PRs with status
```

### Create issue and add to project

```python
github_create_issue_in_project(
    owner="rhea-impact",
    repo="taskr",
    title="Add refresh token support",
    body="## Description\nImplement OAuth refresh tokens...",
    labels=["enhancement", "auth"],
    project_number=1
)
# Creates issue AND links to project atomically
```

### Add existing issue to project

```python
github_project_add_item(
    org="rhea-impact",
    project_number=1,
    content_id="I_kwDOK..."  # Issue node ID
)
```

### Create PR with issue linking

```python
github_pr_create(
    owner="rhea-impact",
    repo="taskr",
    title="feat: Add refresh token support",
    body="Closes #42",
    head="feature/refresh-tokens",
    base="main",
    project_number=1  # Auto-adds to project
)
```

## GitHub MCP Complement

Taskr is designed to work **alongside** GitHub MCP, not replace it.

### Use GitHub MCP for:

```python
# Reading issues
mcp__github__list_issues(owner="rhea-impact", repo="taskr", state="open")

# Searching
mcp__github__search_issues(query="auth bug repo:rhea-impact/taskr")

# Comments
mcp__github__add_issue_comment(owner="rhea-impact", repo="taskr", issue_number=42, body="Fixed in PR #43")

# Closing issues
mcp__github__issue_write(method="update", owner="rhea-impact", repo="taskr", issue_number=42, state="closed")
```

### Use Taskr for:

```python
# Project management
github_project_create(title="Sprint 5", org="rhea-impact")
github_project_items(org="rhea-impact", project_number=1)

# Issue + Project linking
github_create_issue_in_project(owner="...", repo="...", project_number=1, ...)
```

## Node IDs

GitHub's GraphQL API uses node IDs (like `I_kwDOK...`) instead of numbers. Taskr provides helpers:

```python
# Get issue node ID
github_get_issue_id(owner="rhea-impact", repo="taskr", issue_number=42)
# Returns: {"issue_id": "I_kwDOK..."}

# Get org/user node ID
github_get_org_id(login="rhea-impact")
# Returns: {"id": "O_kgDOB...", "type": "organization"}
```

## Projects V2 vs. Classic Projects

Taskr only supports **Projects V2** (the current GitHub Projects):

| Feature | Projects V2 | Classic (deprecated) |
|---------|-------------|---------------------|
| Scope | Organization-level | Repository-level |
| Views | Table, Board, Roadmap | Board only |
| Custom fields | Yes | Limited |
| Automation | Built-in workflows | Limited |
| API | GraphQL | REST |

GitHub is deprecating Classic Projects. Use Projects V2.

## Best Practices

### 1. One Project Per Initiative

Don't dump everything into one project:

```
Bad:  "All Issues" (1000+ items)
Good: "Q1 Auth Refactor" (20 items)
```

### 2. Use Statuses

Projects V2 has built-in status tracking:
- **Todo** - Not started
- **In Progress** - Being worked on
- **Done** - Completed

Claude can filter by status when listing items.

### 3. Link Issues to PRs

Use "Closes #N" in PR descriptions:

```python
github_pr_create(
    ...
    body="Closes #42\n\nImplements refresh token support"
)
```

GitHub auto-closes the issue when the PR merges.

### 4. Keep Projects Tidy

Archive completed projects:

```python
github_project_close(org="rhea-impact", project_number=1)
```

Reopen if needed:

```python
github_project_reopen(org="rhea-impact", project_number=1)
```

## Installation with GitHub MCP

Your Claude Code config should have both:

```json
{
  "mcpServers": {
    "taskr": {
      "command": "taskr-mcp",
      "env": {
        "GITHUB_TOKEN": "ghp_..."
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
      }
    }
  }
}
```

Use the same token for both (needs `repo` + `project` scopes).

## Related Modules

- [Tasks](tasks.md) - Internal task tracking (links to GitHub issues)
- [Sessions](sessions.md) - Claim GitHub issues to prevent conflicts
- [Triage](triage.md) - Reconciles devlogs with GitHub issues
