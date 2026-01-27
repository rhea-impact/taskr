"""
Context and discovery tools for Taskr.

Tools that help agents understand how to use taskr and find relevant context.
"""

from typing import Optional, List


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

    @mcp.tool()
    async def taskr_tools_for(intent: str) -> dict:
        """
        Discover taskr tools by describing what you want to accomplish.

        Args:
            intent: Describe what you want to do (e.g., "track a bug fix",
                   "find previous implementations", "coordinate with other agents")

        Returns:
            Recommended tools and example usage
        """
        intent_lower = intent.lower()

        recommendations = []

        # Task management
        if any(word in intent_lower for word in ["task", "todo", "work item", "create", "assign"]):
            recommendations.append({
                "category": "Task Management",
                "tools": ["taskr_create", "taskr_list", "taskr_assign", "taskr_close"],
                "example": "taskr_create(title='Fix login bug', priority='high', tags=['bug'])",
            })

        # Searching/finding
        if any(word in intent_lower for word in ["find", "search", "look", "previous", "pattern", "how"]):
            recommendations.append({
                "category": "Knowledge Search",
                "tools": ["devlog_search", "taskr_search", "taskr_why_decision"],
                "example": "devlog_search(query='authentication pattern', service_name='api')",
            })

        # Documenting
        if any(word in intent_lower for word in ["document", "record", "log", "note", "decision"]):
            recommendations.append({
                "category": "Documentation",
                "tools": ["devlog_add", "devlog_update"],
                "example": "devlog_add(category='decision', title='Chose JWT over sessions', content='...')",
            })

        # Coordination
        if any(word in intent_lower for word in ["coordinate", "claim", "agent", "session", "handoff"]):
            recommendations.append({
                "category": "Agent Coordination",
                "tools": ["session_start", "session_end", "claim_work", "release_work"],
                "example": "claim_work(work_type='issue', work_id='123', repo='owner/repo')",
            })

        # Bug/incident
        if any(word in intent_lower for word in ["bug", "fix", "incident", "error", "issue"]):
            recommendations.append({
                "category": "Bug Tracking",
                "tools": ["devlog_add", "taskr_related_issues"],
                "example": "devlog_add(category='bugfix', title='Fixed null pointer in auth', content='...')",
            })

        # Default if no matches
        if not recommendations:
            recommendations.append({
                "category": "Getting Started",
                "tools": ["taskr_triage", "taskr_health", "devlog_list"],
                "example": "taskr_triage() - Get workflow guidance",
            })

        return {
            "intent": intent,
            "recommendations": recommendations,
        }

    @mcp.tool()
    async def taskr_why_decision(
        query: str,
        service_name: Optional[str] = None,
        limit: int = 5,
    ) -> dict:
        """
        Find rationale behind past decisions.

        Search for decision devlogs that explain why something was done a certain way.

        Args:
            query: What decision are you looking for? (e.g., "database choice", "auth method")
            service_name: Optional service filter
            limit: Maximum results

        Returns:
            Relevant decision devlogs with rationale
        """
        from taskr.services import DevlogService

        service = DevlogService()

        # Search specifically in decision category
        devlogs = await service.search(
            query=query,
            category="decision",
            service_name=service_name,
            limit=limit,
        )

        # Also search in research category as backup
        if len(devlogs) < limit:
            research = await service.search(
                query=query,
                category="research",
                service_name=service_name,
                limit=limit - len(devlogs),
            )
            devlogs.extend(research)

        return {
            "query": query,
            "decisions": [
                {
                    "id": d.id,
                    "title": d.title,
                    "category": d.category,
                    "summary": d.summary(200),
                    "service_name": d.service_name,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in devlogs
            ],
            "count": len(devlogs),
            "tip": "Use devlog_get(devlog_id) to read full content",
        }

    @mcp.tool()
    async def taskr_related_issues(
        file_path: Optional[str] = None,
        error_message: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 10,
    ) -> dict:
        """
        Find related bugs, devlogs, and context before modifying code.

        Call this before making changes to understand prior issues.

        Args:
            file_path: File you're about to modify
            error_message: Error you're trying to fix
            keywords: Additional search keywords
            limit: Maximum results

        Returns:
            Related devlogs and context
        """
        from taskr.services import DevlogService

        service = DevlogService()
        results = []

        # Build search query from inputs
        search_terms = []
        if file_path:
            # Extract filename and key parts
            parts = file_path.replace("/", " ").replace("_", " ").replace(".", " ").split()
            search_terms.extend([p for p in parts if len(p) > 2])
        if error_message:
            # Extract key words from error
            words = error_message.split()[:10]  # First 10 words
            search_terms.extend([w for w in words if len(w) > 3])
        if keywords:
            search_terms.extend(keywords)

        if not search_terms:
            return {
                "error": "Provide at least one of: file_path, error_message, or keywords",
            }

        query = " ".join(search_terms[:5])  # Limit query length

        # Search bugfix devlogs
        bugfixes = await service.search(
            query=query,
            category="bugfix",
            limit=limit // 2,
        )
        results.extend(bugfixes)

        # Search incident devlogs
        incidents = await service.search(
            query=query,
            category="incident",
            limit=limit // 2,
        )
        results.extend(incidents)

        # Deduplicate
        seen_ids = set()
        unique_results = []
        for d in results:
            if d.id not in seen_ids:
                seen_ids.add(d.id)
                unique_results.append(d)

        return {
            "query": query,
            "related": [
                {
                    "id": d.id,
                    "category": d.category,
                    "title": d.title,
                    "summary": d.summary(150),
                    "tags": d.tags,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in unique_results[:limit]
            ],
            "count": len(unique_results),
            "search_terms": search_terms[:5],
        }
