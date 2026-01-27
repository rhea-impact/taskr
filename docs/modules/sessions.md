# Sessions Module

> Multi-agent work coordination

## Executive Summary

**The Problem**: When multiple AI agents work on the same codebase:
- Two agents fix the same bug independently
- Work gets duplicated or conflicts
- Context is lost between sessions
- No one knows what happened yesterday

Even with a single agent, context resets between conversations. You re-explain the same background every time.

**The Solution**: Sessions provide:
- **Handoff notes** that persist between conversations
- **Work claiming** that prevents duplicate effort
- **Activity tracking** so you know who did what
- **Continuity** that survives context windows

**Why This Matters**: AI agents are stateless. Sessions give them state.

## Tools

| Tool | Description |
|------|-------------|
| `taskr_session_start` | Start a session with context |
| `taskr_session_end` | End with summary and handoff |
| `taskr_claim_work` | Atomically claim a work item |
| `taskr_release_work` | Release claimed work |
| `taskr_what_changed` | See activity since timestamp |

## Session Flow

```
┌─────────────────┐
│  session_start  │──────▶ Get handoff notes from last session
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   claim_work    │──────▶ Lock work item (prevents conflicts)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Do the work   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  release_work   │──────▶ Mark complete/blocked/deferred
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  session_end    │──────▶ Leave handoff notes for next session
└─────────────────┘
```

## Usage Examples

### Start a session

```python
result = taskr_session_start(
    agent_id="claude-code",
    context="Working on authentication refactor"
)

# Returns:
# {
#     "session_id": "abc-123",
#     "handoff_notes": "Priority: finish OAuth integration. Blocked on #42.",
#     "last_summary": "Completed database migration, started OAuth work"
# }
```

The handoff notes tell you exactly where to pick up.

### Claim work before starting

```python
result = taskr_claim_work(
    agent_id="claude-code",
    work_type="issue",
    work_id="15",
    repo="rhea-impact/taskr"
)

# If unclaimed:
# {"claimed": True, "message": "Successfully claimed issue rhea-impact/taskr#15"}

# If already claimed:
# {"claimed": False, "claimed_by": "other-agent", "message": "Work already claimed"}
```

### Release work when done

```python
taskr_release_work(
    agent_id="claude-code",
    work_type="issue",
    work_id="15",
    repo="rhea-impact/taskr",
    status="completed",
    notes="Fixed in PR #16"
)
```

### End session with handoff

```python
taskr_session_end(
    session_id="abc-123",
    summary="Completed OAuth integration, all tests passing",
    handoff_notes="Ready for review. Next: add refresh token support."
)
```

### Check what changed

```python
taskr_what_changed(
    since="2024-01-15T00:00:00Z",
    agent_id="claude-code"  # optional filter
)

# Returns recent activities and sessions
```

## Work Claiming

### Why Claim Work?

Without claiming:
```
Agent A: "I'll fix issue #15"
Agent B: "I'll fix issue #15"
Result: Two PRs for the same issue, wasted effort
```

With claiming:
```
Agent A: claim_work(issue #15) → Success
Agent B: claim_work(issue #15) → "Already claimed by Agent A"
Result: Agent B works on something else
```

### Work Types

| Type | Description |
|------|-------------|
| `issue` | GitHub issue |
| `pr` | Pull request |
| `qa` | QA/testing task |

### Release Statuses

| Status | Meaning |
|--------|---------|
| `completed` | Work finished successfully |
| `blocked` | Can't proceed, needs help |
| `deferred` | Postponed for later |

## Handoff Notes

Handoff notes are the key to session continuity. They answer:
- What was I working on?
- What's the current priority?
- What's blocked?
- What should happen next?

### Good Handoff Notes

```
Priority: Finish #42 (OAuth). Tests failing on token refresh.
Blocked: Waiting for API keys from ops team.
Next: Once unblocked, add refresh token support.
Context: Using httpx, not requests. Pattern in devlog "OAuth setup".
```

### Bad Handoff Notes

```
Did some stuff. More to do.
```

## Multi-Agent Patterns

### Sequential Handoff

```
Agent A (morning) ──handoff──▶ Agent B (afternoon)
                  notes
```

Each agent continues where the last left off.

### Parallel Work

```
Agent A: claim issue #10 → work → release
Agent B: claim issue #11 → work → release
```

No conflicts because work is claimed.

### Supervisor Pattern

```
Supervisor: Assigns work via claim_work
Worker A: Does claimed work, releases
Worker B: Does claimed work, releases
Supervisor: Reviews, reassigns as needed
```

## Activity Tracking

All claims and releases are logged:

```sql
SELECT * FROM agent_activity
WHERE repo = 'rhea-impact/taskr'
ORDER BY created_at DESC;
```

This provides an audit trail of who worked on what.

## Best Practices

### 1. Always Start/End Sessions

Even for quick fixes:

```python
session = taskr_session_start(agent_id="claude-code", context="Quick fix for typo")
# ... do work ...
taskr_session_end(session["session_id"], summary="Fixed typo in README", handoff_notes="None")
```

This maintains the activity log.

### 2. Claim Before Working

Don't start work without claiming. Even if you're the only agent, it creates a record:

```python
taskr_claim_work(...)  # First
# ... do work ...       # Then
taskr_release_work(...) # Finally
```

### 3. Release Promptly

Stale claims block other agents. Release work when:
- You finish it
- You get blocked
- You switch to something else

### 4. Write Specific Handoff Notes

The next session might be a different Claude instance. It knows nothing except what you write.

### 5. Check what_changed After Breaks

If you've been away:

```python
taskr_what_changed(since="2024-01-15T00:00:00Z")
```

See what other agents did while you were gone.

## Related Modules

- [Tasks](tasks.md) - Track work items across sessions
- [Devlogs](devlogs.md) - Record decisions made during sessions
- [Triage](triage.md) - Uses sessions for workflow continuity
