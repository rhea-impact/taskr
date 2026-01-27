"""
Supabase MCP tools for Taskr.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from taskr_supabase.plugin import SupabasePlugin


def register(mcp: "FastMCP", plugin: "SupabasePlugin") -> None:
    """Register Supabase tools with the MCP server."""

    @mcp.tool()
    async def supabase_deploy(
        function_name: str,
        function_path: str,
        verify_jwt: bool = True,
        import_map: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """
        Deploy a Supabase Edge Function.

        Args:
            function_name: Name of the function (e.g., 'hello-world')
            function_path: Path to the function directory
            verify_jwt: Whether to verify JWT tokens (default True)
            import_map: Optional path to import_map.json
            dry_run: If True, validate without deploying

        Returns:
            Deployment status and URL
        """
        from pathlib import Path

        import httpx

        from taskr.db import get_adapter

        project_ref = plugin.get_project_ref()
        access_token = plugin.get_access_token()

        # Read function code
        func_dir = Path(function_path)
        index_file = func_dir / "index.ts"

        if not index_file.exists():
            return {"error": f"Function not found: {index_file}"}

        function_code = index_file.read_text()

        if dry_run:
            return {
                "dry_run": True,
                "function_name": function_name,
                "code_length": len(function_code),
                "verify_jwt": verify_jwt,
            }

        # Deploy via Management API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.supabase.com/v1/projects/{project_ref}/functions/{function_name}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "body": function_code,
                    "verify_jwt": verify_jwt,
                },
                timeout=60.0,
            )

            if response.status_code not in (200, 201):
                return {
                    "error": f"Deployment failed: {response.status_code}",
                    "detail": response.text,
                }

            _response_data = response.json()  # noqa: F841 - validate JSON response

        # Log deployment to database
        adapter = get_adapter()
        await adapter.execute(
            """
            INSERT INTO taskr.deployment_log
                (function_name, project_ref, status, deployed_at, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            function_name, project_ref, "deployed", datetime.utcnow(),
            json.dumps({"verify_jwt": verify_jwt, "code_length": len(function_code)}),
        )

        return {
            "deployed": True,
            "function_name": function_name,
            "project_ref": project_ref,
            "url": f"https://{project_ref}.supabase.co/functions/v1/{function_name}",
            "verify_jwt": verify_jwt,
        }

    @mcp.tool()
    async def supabase_deploy_history(
        function_name: str | None = None,
        limit: int = 20,
    ) -> dict:
        """
        List Edge Function deployment history.

        Args:
            function_name: Filter by function name
            limit: Maximum results

        Returns:
            List of deployments
        """
        from taskr.db import get_adapter

        adapter = get_adapter()

        if function_name:
            rows = await adapter.fetch(
                """
                SELECT * FROM taskr.deployment_log
                WHERE function_name = $1
                ORDER BY deployed_at DESC
                LIMIT $2
                """,
                function_name, limit,
            )
        else:
            rows = await adapter.fetch(
                """
                SELECT * FROM taskr.deployment_log
                ORDER BY deployed_at DESC
                LIMIT $1
                """,
                limit,
            )

        return {
            "deployments": [
                {
                    "function_name": row["function_name"],
                    "project_ref": row["project_ref"],
                    "status": row["status"],
                    "deployed_at": row["deployed_at"].isoformat() if row["deployed_at"] else None,
                    "metadata": row.get("metadata"),
                }
                for row in rows
            ],
            "count": len(rows),
        }

    @mcp.tool()
    async def supabase_sql_query(
        query: str,
        read_only: bool = True,
    ) -> dict:
        """
        Execute a SQL query against Supabase PostgreSQL.

        Args:
            query: SQL query to execute
            read_only: If True, only allow SELECT queries (default True)

        Returns:
            Query results
        """
        from taskr.db import get_adapter

        # Validate read_only
        if read_only:
            query_upper = query.strip().upper()
            if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
                return {
                    "error": "Only SELECT queries allowed in read_only mode. Set read_only=False for mutations.",
                }

        adapter = get_adapter()

        try:
            if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("WITH"):
                rows = await adapter.fetch(query)
                return {
                    "rows": [dict(row) for row in rows],
                    "row_count": len(rows),
                }
            else:
                result = await adapter.execute(query)
                return {
                    "status": result,
                    "success": True,
                }
        except Exception as e:
            return {
                "error": str(e),
                "query": query[:100] + "..." if len(query) > 100 else query,
            }

    @mcp.tool()
    async def supabase_migrations_list() -> dict:
        """
        List applied database migrations.

        Returns:
            List of migrations and their status
        """
        from taskr.db import get_adapter

        adapter = get_adapter()

        rows = await adapter.fetch(
            """
            SELECT * FROM taskr.schema_migrations
            ORDER BY version
            """
        )

        return {
            "migrations": [
                {
                    "version": row["version"],
                    "applied_at": row["applied_at"].isoformat() if row.get("applied_at") else None,
                }
                for row in rows
            ],
            "count": len(rows),
        }
