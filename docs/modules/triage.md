# Triage Module

> Workflow orchestration that tells Claude what to do next

## Executive Summary

**The Problem**: You say "work on my project" and Claude asks:
- "What should I work on?"
- "What's the priority?"
- "Where did we leave off?"
- "What tools should I use?"

Every session starts with 5 minutes of context-gathering before any real work happens.

**The Solution**: `taskr_triage` is a single tool that:
- Assesses current state (sessions, devlogs, GitHub)
- Generates a concrete workflow (which tools, in what order)
- Returns actionable next steps
- Eliminates decision paralysis

**Why This Matters**: "Use taskr triage to ______" is all you need to say. Triage handles the rest.

## The Tool

```python
taskr_triage(
    request="Clean up the project and start on the next feature",
    working_directory="/path/to/repo",
    org="rhea-impact",
    repo="taskr"
)
```

## What Triage Returns

### 1. Current State Assessment

```json
{
  "has_active_session": false,
  "recent_devlogs_count": 10,
  "inferred_repo": "rhea-impact/taskr"
}
```

### 2. Recommended Workflow

| Phase | Tool | Why |
|-------|------|-----|
| Session Setup | `taskr_session_start` | Get handoff notes |
| Understand Context | `devlog_search`, `what_changed` | See recent work |
| Check GitHub | `github_project_items`, GitHub MCP | Current issue state |
| Select Work | `taskr_claim_work` | Lock a work item |
| Do Work | (coding tools) | Actual implementation |
| Document | `devlog_add` | Record decisions |
| End Session | `taskr_session_end` | Leave handoff notes |

### 3. Actionable Prompt

Triage generates a complete prompt for subagent delegation:

```
You are helping Claude Code use taskr effectively.
1. Check GitHub state for rhea-impact/taskr
2. Reconcile devlogs with open issues
3. Select next priority work
4. Return actionable steps
```

## Usage Patterns

### Starting a Work Session

```
User: "use taskr triage to work on the auth refactor"
```

Claude calls triage, gets:
- Handoff notes from last session
- List of open issues
- Recommended next steps

### Project Cleanup

```
User: "use taskr triage to clean up"
```

Claude calls triage, then:
1. Lists open GitHub issues
2. Compares with recent devlogs
3. Closes issues that are done
4. Updates issues with progress
5. Creates devlog documenting cleanup

### Orientation After Break

```
User: "use taskr triage to catch up"
```

Claude calls triage, gets:
- What changed since last session
- Current blockers
- Priority items

## The 8-Phase Workflow

Triage recommends this workflow for most tasks:

```
1. session_start     → Get context from last session
2. devlog_search     → Find related prior work
3. what_changed      → See recent activity
4. GitHub check      → Current issue/PR state
5. claim_work        → Lock your work item
6. (do the work)     → Coding, testing, etc.
7. devlog_add        → Document what you did
8. session_end       → Leave notes for next time
```

Not every task needs all 8 phases. Triage adapts based on:
- Whether there's an active session
- How many devlogs exist
- The nature of the request

## Real-World Example

From the [case study](../research/taskr-triage-workflow-case-study.md):

**Request**: "Clean up rhea-impact/taskr"

**Time**: 1.5 minutes

**Actions**:
1. Started session, got handoff notes
2. Listed 8 GitHub issues
3. Cross-referenced with git log
4. Closed 1 issue (matched a commit)
5. Updated 2 issues with progress
6. Created devlog documenting work
7. Ended session with handoff notes

**Result**: Project cleaned up, ready for next session.

## When to Use Triage

| Scenario | Triage Helps? |
|----------|--------------|
| Starting a work session | ✅ Yes |
| Returning after a break | ✅ Yes |
| Project cleanup | ✅ Yes |
| Switching repositories | ✅ Yes |
| Quick single-file fix | ❌ Overkill |
| Simple question | ❌ Not needed |

## Triage Inputs

| Input | Purpose |
|-------|---------|
| `request` | What you want to accomplish |
| `working_directory` | Infers repo from path |
| `org` | GitHub organization |
| `repo` | GitHub repository |
| `recent_files` | Files you've been working on |

The more context you provide, the better the recommendations.

## Anti-Patterns

### ❌ Skipping Session Start

```python
# Bad: Jump straight to work
taskr_claim_work(...)

# Good: Start session first
taskr_session_start(...)
taskr_claim_work(...)
```

Without a session, there's no continuity.

### ❌ Not Creating Devlogs

```python
# Bad: Do work, end session
(work)
taskr_session_end(...)

# Good: Document decisions
(work)
devlog_add(category="decision", ...)
taskr_session_end(...)
```

Devlogs are how Claude learns.

### ❌ Empty Handoff Notes

```python
# Bad
taskr_session_end(session_id, summary="Done", handoff_notes="")

# Good
taskr_session_end(
    session_id,
    summary="Completed OAuth integration",
    handoff_notes="Priority: add refresh tokens. Blocked on #42."
)
```

Future sessions need context.

### ❌ Closing Issues Without Comments

```python
# Bad: Silent close
mcp__github__issue_write(state="closed")

# Good: Document what was done
mcp__github__add_issue_comment(body="Completed in commit abc123...")
mcp__github__issue_write(state="closed")
```

Audit trails matter.

## Triage vs. Manual Workflow

| Without Triage | With Triage |
|----------------|-------------|
| "What should I do?" | Triage tells you |
| "What tools do I need?" | Triage provides list |
| "What order?" | Triage specifies sequence |
| "Did I miss anything?" | Triage checks state |
| 5+ minutes context-gathering | Sub-minute orientation |

## Best Practices

### 1. Trust the Workflow

Triage is designed by analyzing hundreds of successful sessions. Follow its recommendations.

### 2. Provide Specific Requests

```
Bad:  "use taskr triage"
Good: "use taskr triage to fix the login bug and clean up stale issues"
```

### 3. Use Triage at Session Boundaries

- Start of session → triage
- After a break → triage
- Switching repos → triage

### 4. Let Triage Handle Orientation

Don't manually check GitHub, devlogs, and sessions. Triage does this systematically.

## Related Modules

- [Sessions](sessions.md) - Triage uses sessions for continuity
- [Devlogs](devlogs.md) - Triage searches devlogs for context
- [GitHub](github.md) - Triage checks GitHub state
- [Tasks](tasks.md) - Triage may create/update tasks
