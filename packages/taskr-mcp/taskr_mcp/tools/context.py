"""
Context and discovery tools for Taskr.

Tools that help agents understand how to use taskr and find relevant context.
"""


def register_context_tools(mcp):
    """Register context discovery tools."""

    @mcp.tool()
    async def taskr_triage() -> dict:
        """
        Workflow coach - guides you on using taskr properly.

        Call this when starting work to get guidance on:
        - Whether to start a session
        - How to claim work
        - When to create devlogs
        - Best practices for agent coordination

        Returns:
            Guidance on taskr workflow
        """
        return {
            "guidance": """
## Taskr Workflow Guide

### Starting Work
1. **Start a session**: `session_start(context="what you're working on")`
2. **Check for handoff notes**: Review any notes from previous sessions
3. **Claim work**: `claim_work(work_type="issue", work_id="123", repo="owner/repo")`

### During Work
- **Search devlogs**: Before implementing, check `devlog_search(query="topic")` for prior patterns
- **Create devlogs**: Document decisions, patterns, and gotchas as you work
- **Use categories**: feature, bugfix, decision, research, incident, etc.

### Finishing Work
1. **Release work**: `release_work(...)` with status (completed, blocked, deferred)
2. **End session**: `session_end(session_id, summary="what you did", handoff_notes="for next session")`

### Best Practices
- Always search devlogs before implementing non-trivial features
- Create a devlog for any decision that might confuse future agents
- Use handoff_notes to communicate with your future self
- Claim work before starting to prevent duplicate effort
""",
            "quick_commands": {
                "start_work": "session_start(context='...')",
                "check_patterns": "devlog_search(query='...')",
                "claim_issue": "claim_work(work_type='issue', work_id='...', repo='...')",
                "log_decision": "devlog_add(category='decision', title='...', content='...')",
                "end_session": "session_end(session_id='...', summary='...', handoff_notes='...')",
            },
        }
