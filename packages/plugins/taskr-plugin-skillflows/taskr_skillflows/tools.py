"""
Skillflow MCP tools for Taskr.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from taskr_skillflows.plugin import SkillflowsPlugin


def register(mcp: "FastMCP", plugin: "SkillflowsPlugin") -> None:
    """Register skillflow tools with the MCP server."""

    @mcp.tool()
    async def skillflow_create(
        name: str,
        title: str,
        description: Optional[str] = None,
        status: str = "draft",
        inputs: Optional[List[Dict[str, Any]]] = None,
        outputs: Optional[List[Dict[str, Any]]] = None,
        preconditions: Optional[List[Dict[str, Any]]] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
    ) -> dict:
        """
        Create a new skillflow workflow definition.

        Skillflows are tracked, discoverable workflows that AI agents can execute.

        Args:
            name: Unique kebab-case slug (e.g., 'deploy-new-service')
            title: Human-readable name
            description: Markdown description with gotchas and examples
            status: draft, active, or deprecated
            inputs: Input parameter definitions [{"name": str, "type": str, "required": bool}]
            outputs: Output definitions [{"name": str, "type": str}]
            preconditions: Requirements [{"check": str, "error_message": str}]
            steps: Workflow steps [{"order": int, "action": str, "description": str, "why": str}]
            tags: Tags for discovery

        Returns:
            Created skillflow with validation feedback
        """
        from taskr.db import get_adapter
        from taskr.config import get_config
        from taskr_skillflows.models import Skillflow

        adapter = get_adapter()
        config = get_config()

        skillflow = Skillflow(
            name=name,
            title=title,
            description=description,
            status=status,
            inputs=inputs or [],
            outputs=outputs or [],
            preconditions=preconditions or [],
            steps=steps or [],
            tags=tags or [],
            author=config.author,
        )

        # Validate steps have 'why' field
        quality_issues = []
        for i, step in enumerate(skillflow.steps):
            if not step.get("why"):
                quality_issues.append(f"Step {i+1} missing 'why' field explaining rationale")
            if not step.get("action"):
                quality_issues.append(f"Step {i+1} missing 'action' field")

        # Insert into database
        await adapter.execute(
            """
            INSERT INTO taskr.skillflows
                (id, name, title, description, status, version, inputs, outputs,
                 preconditions, steps, tags, author, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb[], $8::jsonb[],
                    $9::jsonb[], $10::jsonb[], $11, $12, $13, $14)
            """,
            skillflow.id, skillflow.name, skillflow.title, skillflow.description,
            skillflow.status, skillflow.version,
            [json.dumps(i) for i in skillflow.inputs],
            [json.dumps(o) for o in skillflow.outputs],
            [json.dumps(p) for p in skillflow.preconditions],
            [json.dumps(s) for s in skillflow.steps],
            skillflow.tags, skillflow.author,
            skillflow.created_at, skillflow.updated_at,
        )

        result = skillflow.to_dict()
        if quality_issues:
            result["quality_issues"] = quality_issues
            result["revision_required"] = True
            result["revision_prompt"] = "Consider adding 'why' explanations to each step"

        return result

    @mcp.tool()
    async def skillflow_get(name_or_id: str) -> dict:
        """
        Get a skillflow by name or ID.

        Args:
            name_or_id: Skillflow name (slug) or UUID

        Returns:
            Skillflow definition with execution metrics
        """
        from taskr.db import get_adapter
        from taskr_skillflows.models import Skillflow

        adapter = get_adapter()

        # Try by name first, then by ID
        row = await adapter.fetchrow(
            """
            SELECT s.*,
                   COUNT(e.id) as execution_count,
                   COALESCE(AVG(CASE WHEN e.status = 'completed' THEN 1.0 ELSE 0.0 END), 0) as success_rate
            FROM taskr.skillflows s
            LEFT JOIN taskr.skillflow_executions e ON s.id = e.skillflow_id
            WHERE (s.name = $1 OR s.id::text = $1) AND s.deleted_at IS NULL
            GROUP BY s.id
            """,
            name_or_id,
        )

        if not row:
            return {"error": f"Skillflow not found: {name_or_id}"}

        return Skillflow.from_dict(dict(row)).to_dict()

    @mcp.tool()
    async def skillflow_list(
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> dict:
        """
        List skillflows with optional filters.

        Args:
            status: Filter by status (draft, active, deprecated)
            tags: Filter by tags (matches any)
            limit: Maximum results

        Returns:
            List of skillflow summaries
        """
        from taskr.db import get_adapter
        from taskr_skillflows.models import Skillflow

        adapter = get_adapter()

        conditions = ["deleted_at IS NULL"]
        params = []

        if status:
            conditions.append(f"status = ${len(params)+1}")
            params.append(status)

        if tags:
            conditions.append(f"tags && ${len(params)+1}")
            params.append(tags)

        params.append(limit)
        where_clause = " AND ".join(conditions)

        rows = await adapter.fetch(
            f"""
            SELECT s.*,
                   COUNT(e.id) as execution_count,
                   COALESCE(AVG(CASE WHEN e.status = 'completed' THEN 1.0 ELSE 0.0 END), 0) as success_rate
            FROM taskr.skillflows s
            LEFT JOIN taskr.skillflow_executions e ON s.id = e.skillflow_id
            WHERE {where_clause}
            GROUP BY s.id
            ORDER BY s.created_at DESC
            LIMIT ${len(params)}
            """,
            *params,
        )

        skillflows = [Skillflow.from_dict(dict(row)) for row in rows]

        return {
            "skillflows": [
                {
                    "id": s.id,
                    "name": s.name,
                    "title": s.title,
                    "status": s.status,
                    "tags": s.tags,
                    "execution_count": s.execution_count,
                    "success_rate": s.success_rate,
                }
                for s in skillflows
            ],
            "count": len(skillflows),
        }

    @mcp.tool()
    async def skillflow_search(
        query: str,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """
        Search skillflows by name, title, description, and tags.

        Args:
            query: Search query
            status: Optional status filter
            limit: Maximum results

        Returns:
            Matching skillflows ranked by relevance
        """
        from taskr.db import get_adapter

        adapter = get_adapter()

        conditions = [
            "deleted_at IS NULL",
            "search_vector @@ plainto_tsquery('english', $1)",
        ]
        params = [query]

        if status:
            conditions.append(f"status = ${len(params)+1}")
            params.append(status)

        params.append(limit)
        where_clause = " AND ".join(conditions)

        rows = await adapter.fetch(
            f"""
            SELECT s.*,
                   ts_rank(search_vector, plainto_tsquery('english', $1)) as rank,
                   COUNT(e.id) as execution_count
            FROM taskr.skillflows s
            LEFT JOIN taskr.skillflow_executions e ON s.id = e.skillflow_id
            WHERE {where_clause}
            GROUP BY s.id
            ORDER BY rank DESC
            LIMIT ${len(params)}
            """,
            *params,
        )

        return {
            "skillflows": [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "title": row["title"],
                    "status": row["status"],
                    "tags": row["tags"],
                    "relevance": float(row.get("rank", 0)),
                }
                for row in rows
            ],
            "count": len(rows),
            "query": query,
        }

    @mcp.tool()
    async def skillflow_execute(
        name_or_id: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """
        Start executing a skillflow.

        Creates an execution record and returns the skillflow steps to follow.

        Args:
            name_or_id: Skillflow name or ID
            inputs: Input values for the skillflow

        Returns:
            Execution ID and steps to follow
        """
        from taskr.db import get_adapter
        from taskr.config import get_config
        from taskr_skillflows.models import Skillflow, SkillflowExecution

        adapter = get_adapter()
        config = get_config()

        # Get skillflow
        row = await adapter.fetchrow(
            """
            SELECT * FROM taskr.skillflows
            WHERE (name = $1 OR id::text = $1) AND deleted_at IS NULL
            """,
            name_or_id,
        )

        if not row:
            return {"error": f"Skillflow not found: {name_or_id}"}

        skillflow = Skillflow.from_dict(dict(row))

        # Create execution record
        execution = SkillflowExecution(
            skillflow_id=skillflow.id,
            skillflow_name=skillflow.name,
            agent_id=config.agent_id,
            status="running",
            inputs=inputs or {},
            started_at=datetime.utcnow(),
        )

        await adapter.execute(
            """
            INSERT INTO taskr.skillflow_executions
                (id, skillflow_id, skillflow_name, agent_id, status, inputs, started_at)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
            """,
            execution.id, execution.skillflow_id, execution.skillflow_name,
            execution.agent_id, execution.status, json.dumps(execution.inputs),
            execution.started_at,
        )

        return {
            "execution_id": execution.id,
            "skillflow": {
                "name": skillflow.name,
                "title": skillflow.title,
                "description": skillflow.description,
            },
            "inputs": execution.inputs,
            "steps": skillflow.steps,
            "preconditions": skillflow.preconditions,
            "message": f"Execute steps in order. Call skillflow_execution_complete when done.",
        }

    @mcp.tool()
    async def skillflow_execution_complete(
        execution_id: str,
        status: str = "completed",
        outputs: Optional[Dict[str, Any]] = None,
        step_results: Optional[List[Dict[str, Any]]] = None,
        error_message: Optional[str] = None,
    ) -> dict:
        """
        Mark a skillflow execution as complete.

        Args:
            execution_id: Execution ID from skillflow_execute
            status: Final status (completed, failed, cancelled)
            outputs: Output values
            step_results: Results from each step
            error_message: Error message if failed

        Returns:
            Execution summary with duration
        """
        from taskr.db import get_adapter

        adapter = get_adapter()
        now = datetime.utcnow()

        # Get execution to calculate duration
        row = await adapter.fetchrow(
            "SELECT * FROM taskr.skillflow_executions WHERE id = $1",
            execution_id,
        )

        if not row:
            return {"error": f"Execution not found: {execution_id}"}

        started_at = row["started_at"]
        duration_ms = None
        if started_at:
            if isinstance(started_at, str):
                started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            duration_ms = int((now - started_at).total_seconds() * 1000)

        await adapter.execute(
            """
            UPDATE taskr.skillflow_executions
            SET status = $1, outputs = $2::jsonb, step_results = $3::jsonb[],
                error_message = $4, completed_at = $5, duration_ms = $6
            WHERE id = $7
            """,
            status,
            json.dumps(outputs or {}),
            [json.dumps(r) for r in (step_results or [])],
            error_message, now, duration_ms, execution_id,
        )

        return {
            "execution_id": execution_id,
            "status": status,
            "duration_ms": duration_ms,
            "outputs": outputs,
            "error_message": error_message,
        }

    @mcp.tool()
    async def skillflow_executions_list(
        skillflow_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """
        List skillflow executions.

        Args:
            skillflow_name: Filter by skillflow name
            status: Filter by status
            limit: Maximum results

        Returns:
            List of execution summaries
        """
        from taskr.db import get_adapter

        adapter = get_adapter()

        conditions = ["deleted_at IS NULL"]
        params = []

        if skillflow_name:
            conditions.append(f"skillflow_name = ${len(params)+1}")
            params.append(skillflow_name)

        if status:
            conditions.append(f"status = ${len(params)+1}")
            params.append(status)

        params.append(limit)
        where_clause = " AND ".join(conditions)

        rows = await adapter.fetch(
            f"""
            SELECT * FROM taskr.skillflow_executions
            WHERE {where_clause}
            ORDER BY started_at DESC
            LIMIT ${len(params)}
            """,
            *params,
        )

        return {
            "executions": [
                {
                    "id": row["id"],
                    "skillflow_name": row["skillflow_name"],
                    "status": row["status"],
                    "agent_id": row["agent_id"],
                    "duration_ms": row["duration_ms"],
                    "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                }
                for row in rows
            ],
            "count": len(rows),
        }

    @mcp.tool()
    async def skillflow_update(
        name_or_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
    ) -> dict:
        """
        Update a skillflow definition.

        Increments version on content changes.

        Args:
            name_or_id: Skillflow name or ID
            title: New title
            description: New description
            status: New status
            steps: New steps (replaces existing)
            tags: New tags

        Returns:
            Updated skillflow
        """
        from taskr.db import get_adapter

        adapter = get_adapter()

        updates = ["updated_at = NOW()"]
        params = []

        if title:
            updates.append(f"title = ${len(params)+1}")
            params.append(title)

        if description:
            updates.append(f"description = ${len(params)+1}")
            params.append(description)

        if status:
            updates.append(f"status = ${len(params)+1}")
            params.append(status)

        if steps:
            updates.append(f"steps = ${len(params)+1}::jsonb[]")
            params.append([json.dumps(s) for s in steps])
            updates.append("version = version + 1")

        if tags:
            updates.append(f"tags = ${len(params)+1}")
            params.append(tags)

        params.append(name_or_id)
        set_clause = ", ".join(updates)

        await adapter.execute(
            f"""
            UPDATE taskr.skillflows
            SET {set_clause}
            WHERE (name = ${len(params)} OR id::text = ${len(params)}) AND deleted_at IS NULL
            """,
            *params,
        )

        # Return updated skillflow
        return await skillflow_get(name_or_id)
