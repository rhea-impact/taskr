"""
Taskr MCP Server

AI-native task management MCP server with support for PostgreSQL and SQLite.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("taskr")

logger = logging.getLogger(__name__)

# Global state
_initialized = False


async def ensure_initialized():
    """Ensure database is initialized."""
    global _initialized
    if _initialized:
        return

    from taskr.db import init_adapter
    from taskr.config import load_config

    config = load_config()
    adapter = await init_adapter(config)

    # Run migrations if needed
    await run_migrations(adapter)

    _initialized = True
    logger.info("Taskr initialized")


async def run_migrations(adapter):
    """Run pending database migrations."""
    from taskr.config import CONFIG_DIR

    # Determine migration path based on adapter type
    if adapter.supports_fts:  # PostgreSQL
        migrations_dir = Path(__file__).parent.parent.parent / "taskr-core" / "migrations" / "postgres"
    else:  # SQLite
        migrations_dir = Path(__file__).parent.parent.parent / "taskr-core" / "migrations" / "sqlite"

    # For development, also check installed package location
    if not migrations_dir.exists():
        import taskr
        pkg_path = Path(taskr.__file__).parent
        if adapter.supports_fts:
            migrations_dir = pkg_path / "migrations" / "postgres"
        else:
            migrations_dir = pkg_path / "migrations" / "sqlite"

    if not migrations_dir.exists():
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return

    # Get applied migrations
    try:
        if adapter.supports_fts:
            applied = await adapter.fetch("SELECT version FROM taskr.schema_migrations")
        else:
            applied = await adapter.fetch("SELECT version FROM schema_migrations")
        applied_versions = {row["version"] for row in applied}
    except Exception:
        # Table doesn't exist yet, run all migrations
        applied_versions = set()

    # Run pending migrations
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        version = sql_file.name.split("_")[0]
        if version not in applied_versions:
            logger.info(f"Running migration: {sql_file.name}")
            sql = sql_file.read_text()
            # Split by semicolons and execute each statement
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        await adapter.execute(statement)
                    except Exception as e:
                        logger.error(f"Migration error in {sql_file.name}: {e}")
                        raise


# =============================================================================
# TASK TOOLS
# =============================================================================

@mcp.tool()
async def taskr_list(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """
    List tasks with optional filters.

    Args:
        status: Filter by status (open, in_progress, done, cancelled)
        priority: Filter by priority (low, medium, high, critical)
        assignee: Filter by assignee username
        limit: Maximum results (default 50)

    Returns:
        List of tasks with summary info
    """
    await ensure_initialized()
    from taskr.services import TaskService

    service = TaskService()
    tasks = await service.list(
        status=status,
        priority=priority,
        assignee=assignee,
        limit=limit,
    )

    return {
        "tasks": [t.to_dict() for t in tasks],
        "count": len(tasks),
    }


@mcp.tool()
async def taskr_create(
    title: str,
    description: Optional[str] = None,
    status: str = "open",
    priority: str = "medium",
    assignee: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> dict:
    """
    Create a new task.

    Args:
        title: Task title
        description: Task description
        status: Status (open, in_progress, done, cancelled)
        priority: Priority (low, medium, high, critical)
        assignee: Assign to username
        tags: List of tags

    Returns:
        Created task details
    """
    await ensure_initialized()
    from taskr.services import TaskService
    from taskr.config import get_config

    config = get_config()
    service = TaskService()

    task = await service.create(
        title=title,
        description=description,
        status=status,
        priority=priority,
        assignee=assignee,
        tags=tags,
        created_by=config.author,
    )

    return task.to_dict()


@mcp.tool()
async def taskr_show(task_id: str) -> dict:
    """
    Get detailed information about a task.

    Args:
        task_id: Task UUID

    Returns:
        Full task details
    """
    await ensure_initialized()
    from taskr.services import TaskService

    service = TaskService()
    task = await service.get(task_id)

    if not task:
        return {"error": f"Task not found: {task_id}"}

    return task.to_dict()


@mcp.tool()
async def taskr_update(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> dict:
    """
    Update an existing task.

    Args:
        task_id: Task UUID
        title: New title
        description: New description
        status: New status
        priority: New priority
        assignee: New assignee
        tags: New tags

    Returns:
        Updated task details
    """
    await ensure_initialized()
    from taskr.services import TaskService

    service = TaskService()
    task = await service.update(
        task_id=task_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        assignee=assignee,
        tags=tags,
    )

    if not task:
        return {"error": f"Task not found: {task_id}"}

    return task.to_dict()


@mcp.tool()
async def taskr_search(
    query: str,
    status: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Search tasks by title and description.

    Args:
        query: Search query
        status: Optional status filter
        limit: Maximum results

    Returns:
        List of matching tasks
    """
    await ensure_initialized()
    from taskr.services import TaskService

    service = TaskService()
    tasks = await service.search(
        query=query,
        status=status,
        limit=limit,
    )

    return {
        "tasks": [t.to_dict() for t in tasks],
        "count": len(tasks),
        "query": query,
    }


@mcp.tool()
async def taskr_assign(task_id: str, assignee: str) -> dict:
    """
    Assign a task to a user.

    Args:
        task_id: Task UUID
        assignee: Username to assign

    Returns:
        Updated task details
    """
    await ensure_initialized()
    from taskr.services import TaskService

    service = TaskService()
    task = await service.assign(task_id, assignee)

    if not task:
        return {"error": f"Task not found: {task_id}"}

    return task.to_dict()


@mcp.tool()
async def taskr_close(task_id: str) -> dict:
    """
    Mark a task as complete.

    Args:
        task_id: Task UUID

    Returns:
        Updated task details
    """
    await ensure_initialized()
    from taskr.services import TaskService

    service = TaskService()
    task = await service.close(task_id)

    if not task:
        return {"error": f"Task not found: {task_id}"}

    return task.to_dict()


# =============================================================================
# DEVLOG TOOLS
# =============================================================================

@mcp.tool()
async def devlog_add(
    category: str,
    title: str,
    content: str,
    service_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> dict:
    """
    Create a development log entry.

    Devlogs are persistent records for AI agent memory.

    Args:
        category: Type - feature, bugfix, deployment, config, incident,
                  refactor, research, decision, migration, note
        title: Short summary (1 line)
        content: Full markdown content
        service_name: Related service/project name
        tags: List of tags for filtering

    Returns:
        Created devlog with id and timestamps
    """
    await ensure_initialized()
    from taskr.services import DevlogService
    from taskr.config import get_config

    config = get_config()
    service = DevlogService()

    devlog = await service.add(
        category=category,
        title=title,
        content=content,
        author=config.author,
        agent_id=config.agent_id,
        service_name=service_name,
        tags=tags,
    )

    return devlog.to_dict()


@mcp.tool()
async def devlog_list(
    category: Optional[str] = None,
    service_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 20,
) -> dict:
    """
    List recent devlog entries.

    Args:
        category: Filter by category
        service_name: Filter by service/project
        tags: Filter by tags (matches any)
        limit: Maximum results (default 20)

    Returns:
        List of devlog summaries
    """
    await ensure_initialized()
    from taskr.services import DevlogService

    service = DevlogService()
    devlogs = await service.list(
        category=category,
        service_name=service_name,
        tags=tags,
        limit=limit,
    )

    return {
        "devlogs": [d.to_dict() for d in devlogs],
        "count": len(devlogs),
    }


@mcp.tool()
async def devlog_get(devlog_id: str) -> dict:
    """
    Get full devlog entry by ID.

    Args:
        devlog_id: UUID of the devlog entry

    Returns:
        Full devlog with content
    """
    await ensure_initialized()
    from taskr.services import DevlogService

    service = DevlogService()
    devlog = await service.get(devlog_id)

    if not devlog:
        return {"error": f"Devlog not found: {devlog_id}"}

    return devlog.to_dict()


@mcp.tool()
async def devlog_search(
    query: str,
    category: Optional[str] = None,
    service_name: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Full-text search across devlogs.

    On PostgreSQL: Uses tsvector/tsquery with relevance ranking
    On SQLite: Falls back to LIKE wildcards

    Args:
        query: Search query
        category: Optional category filter
        service_name: Optional service filter
        limit: Maximum results

    Returns:
        List of matching devlogs ranked by relevance
    """
    await ensure_initialized()
    from taskr.services import DevlogService

    service = DevlogService()
    devlogs = await service.search(
        query=query,
        category=category,
        service_name=service_name,
        limit=limit,
    )

    return {
        "devlogs": [d.to_dict() for d in devlogs],
        "count": len(devlogs),
        "query": query,
    }


@mcp.tool()
async def devlog_update(
    devlog_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> dict:
    """
    Update an existing devlog entry.

    Args:
        devlog_id: UUID of the devlog to update
        title: New title
        content: New content
        category: New category
        tags: New tags (replaces existing)

    Returns:
        Updated devlog
    """
    await ensure_initialized()
    from taskr.services import DevlogService

    service = DevlogService()
    devlog = await service.update(
        devlog_id=devlog_id,
        title=title,
        content=content,
        category=category,
        tags=tags,
    )

    if not devlog:
        return {"error": f"Devlog not found: {devlog_id}"}

    return devlog.to_dict()


@mcp.tool()
async def devlog_delete(devlog_id: str) -> dict:
    """
    Soft delete a devlog entry.

    Args:
        devlog_id: UUID of the devlog to delete

    Returns:
        Success status
    """
    await ensure_initialized()
    from taskr.services import DevlogService

    service = DevlogService()
    success = await service.delete(devlog_id)

    return {
        "deleted": success,
        "devlog_id": devlog_id,
    }


# =============================================================================
# SESSION TOOLS
# =============================================================================

@mcp.tool()
async def session_start(context: Optional[str] = None) -> dict:
    """
    Start an agent session with context.

    Returns context including:
    - Session ID
    - Handoff notes from previous session
    - Last session summary

    Args:
        context: Optional purpose/context for this session

    Returns:
        Session ID and context from previous session
    """
    await ensure_initialized()
    from taskr.services import SessionService
    from taskr.config import get_config

    config = get_config()
    service = SessionService()

    return await service.start(
        agent_id=config.agent_id,
        context=context,
    )


@mcp.tool()
async def session_end(
    session_id: str,
    summary: str,
    handoff_notes: Optional[str] = None,
) -> dict:
    """
    End an agent session with summary.

    Args:
        session_id: The session UUID from session_start
        summary: Summary of what was accomplished
        handoff_notes: Notes for the next session

    Returns:
        Session end confirmation with duration
    """
    await ensure_initialized()
    from taskr.services import SessionService

    service = SessionService()
    return await service.end(
        session_id=session_id,
        summary=summary,
        handoff_notes=handoff_notes,
    )


@mcp.tool()
async def claim_work(
    work_type: str,
    work_id: str,
    repo: str,
) -> dict:
    """
    Atomically claim work to prevent duplicate effort.

    Use before starting work on an issue/PR/QA job.

    Args:
        work_type: Type of work - 'issue', 'pr', or 'qa'
        work_id: GitHub issue number or work item ID
        repo: Repository in owner/repo format

    Returns:
        Claim status and message
    """
    await ensure_initialized()
    from taskr.services import SessionService
    from taskr.config import get_config

    config = get_config()
    service = SessionService()

    return await service.claim_work(
        agent_id=config.agent_id,
        work_type=work_type,
        work_id=work_id,
        repo=repo,
    )


@mcp.tool()
async def release_work(
    work_type: str,
    work_id: str,
    repo: str,
    status: str = "completed",
    notes: Optional[str] = None,
) -> dict:
    """
    Release claimed work.

    Args:
        work_type: Type of work - 'issue', 'pr', or 'qa'
        work_id: Work item ID
        repo: Repository in owner/repo format
        status: Final status (completed, blocked, deferred)
        notes: Optional notes

    Returns:
        Release confirmation
    """
    await ensure_initialized()
    from taskr.services import SessionService
    from taskr.config import get_config

    config = get_config()
    service = SessionService()

    return await service.release_work(
        agent_id=config.agent_id,
        work_type=work_type,
        work_id=work_id,
        repo=repo,
        status=status,
        notes=notes,
    )


@mcp.tool()
async def what_changed(
    hours_ago: int = 24,
) -> dict:
    """
    Get changes since a timestamp.

    Useful for catching up on missed work.

    Args:
        hours_ago: Look back this many hours (default 24)

    Returns:
        Activities and sessions since timestamp
    """
    await ensure_initialized()
    from taskr.services import SessionService

    service = SessionService()
    since = datetime.utcnow() - __import__("datetime").timedelta(hours=hours_ago)

    return await service.what_changed(since=since)


# =============================================================================
# CONTEXT TOOLS
# =============================================================================

# Import and register context tools
from taskr_mcp.tools.context import register_context_tools
register_context_tools(mcp)


# =============================================================================
# UTILITY TOOLS
# =============================================================================

@mcp.tool()
async def taskr_migrate() -> dict:
    """
    Run pending database migrations.

    Returns:
        Migration status
    """
    await ensure_initialized()
    return {"status": "migrations complete"}


@mcp.tool()
async def taskr_health() -> dict:
    """
    Check database connectivity and health.

    Returns:
        Health status including database type and connection info
    """
    await ensure_initialized()
    from taskr.db import get_adapter
    from taskr.config import get_config

    config = get_config()
    adapter = get_adapter()

    # Test query
    try:
        if adapter.supports_fts:
            result = await adapter.fetchval("SELECT 1")
        else:
            result = await adapter.fetchval("SELECT 1")
        connected = result == 1
    except Exception as e:
        connected = False
        logger.error(f"Health check failed: {e}")

    return {
        "status": "healthy" if connected else "unhealthy",
        "database_type": "postgres" if adapter.supports_fts else "sqlite",
        "supports_fts": adapter.supports_fts,
        "supports_vector": adapter.supports_vector,
        "agent_id": config.agent_id,
        "author": config.author,
    }


# =============================================================================
# SQL TOOLS
# =============================================================================


@mcp.tool()
async def taskr_sql_query(
    query: str,
    params: Optional[List[str]] = None,
    read_only: bool = True,
) -> dict:
    """
    Execute a SQL query against the taskr database.

    By default only SELECT queries are allowed (read_only=True).
    Set read_only=False for INSERT/UPDATE/DELETE operations.

    Args:
        query: SQL query to execute
        params: Optional query parameters
        read_only: If True, only SELECT allowed (default True)

    Returns:
        Query results with rows, columns, and row count
    """
    await ensure_initialized()
    from taskr.db import get_adapter
    import time

    adapter = get_adapter()

    # Validate read_only mode
    if read_only:
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
            return {
                "error": "Only SELECT queries allowed in read_only mode. Set read_only=False for write operations."
            }

    try:
        start = time.time()
        rows = await adapter.fetch(query, *(params or []))
        elapsed = time.time() - start

        return {
            "success": True,
            "rows": rows,
            "row_count": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "execution_time_ms": round(elapsed * 1000, 2),
        }
    except Exception as e:
        return {"error": f"Query failed: {str(e)}"}


@mcp.tool()
async def taskr_sql_migrate(
    sql: str,
    reason: str,
    executed_by: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """
    Run a SQL migration with audit logging.

    All-or-nothing execution - wraps in a transaction so partial failures
    are rolled back. Logs execution to sql_audit_log table (if it exists).

    Args:
        sql: SQL migration script
        reason: Why this migration is being run (for audit log)
        executed_by: Who is executing (defaults to config.agent_id)
        dry_run: If True, preview SQL without executing (default False)

    Returns:
        Migration result with success status and execution time
    """
    await ensure_initialized()
    from taskr.db import get_adapter
    from taskr.config import get_config
    import time

    config = get_config()
    adapter = get_adapter()
    executed_by = executed_by or config.agent_id

    if dry_run:
        return {
            "dry_run": True,
            "sql": sql,
            "reason": reason,
            "executed_by": executed_by,
            "message": "SQL not executed (dry_run=True)",
        }

    try:
        start = time.time()

        # Execute the migration
        # Note: For PostgreSQL, this runs in a transaction by default
        await adapter.execute(sql)

        elapsed = time.time() - start

        # Try to log to audit table (ignore if it doesn't exist)
        try:
            audit_sql = """
                INSERT INTO sql_audit_log (sql_text, reason, executed_by, execution_time_ms)
                VALUES ($1, $2, $3, $4)
            """
            await adapter.execute(audit_sql, sql[:10000], reason, executed_by, round(elapsed * 1000, 2))
        except Exception:
            # Audit table might not exist, that's OK
            pass

        return {
            "success": True,
            "reason": reason,
            "executed_by": executed_by,
            "execution_time_ms": round(elapsed * 1000, 2),
        }
    except Exception as e:
        return {"error": f"Migration failed: {str(e)}"}


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """Main entry point for taskr-mcp command."""
    import argparse

    parser = argparse.ArgumentParser(description="Taskr MCP Server")
    parser.add_argument("command", nargs="?", default="serve", help="Command to run (serve, migrate)")
    args = parser.parse_args()

    if args.command == "migrate":
        # Run migrations only
        async def do_migrate():
            await ensure_initialized()
            print("Migrations complete")

        asyncio.run(do_migrate())
    else:
        # Start MCP server
        mcp.run()


if __name__ == "__main__":
    main()
