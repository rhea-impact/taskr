"""
Devlog Service for Taskr.

Development logs for AI agent memory and institutional knowledge.
"""

import builtins
import json
import logging
from datetime import datetime
from typing import Any

from taskr.db import get_adapter
from taskr.models.devlog import DEVLOG_CATEGORIES, Devlog

logger = logging.getLogger(__name__)


class DevlogService:
    """
    Service for managing development logs.

    Devlogs capture institutional knowledge:
    - Decisions and rationale
    - Bug fixes and root causes
    - Implementation patterns
    - Research findings
    """

    def __init__(self, adapter=None):
        """
        Initialize devlog service.

        Args:
            adapter: Optional DatabaseAdapter. If not provided, uses global adapter.
        """
        self._adapter = adapter

    @property
    def adapter(self):
        """Get the database adapter."""
        if self._adapter is None:
            self._adapter = get_adapter()
        return self._adapter

    def _table_name(self) -> str:
        """Get the full table name."""
        if self.adapter.supports_fts:  # PostgreSQL
            return "taskr.devlogs"
        return "devlogs"  # SQLite

    async def add(
        self,
        category: str,
        title: str,
        content: str,
        author: str | None = None,
        agent_id: str = "claude-code",
        service_name: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Devlog:
        """
        Create a new devlog entry.

        Args:
            category: Type of log (feature, bugfix, decision, etc.)
            title: Short summary (1 line)
            content: Full markdown content
            author: Human author
            agent_id: AI agent identifier
            service_name: Related service/project
            tags: List of tags for filtering
            metadata: Additional structured data

        Returns:
            Created Devlog object
        """
        if category not in DEVLOG_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. "
                f"Must be one of: {', '.join(DEVLOG_CATEGORIES)}"
            )

        devlog = Devlog(
            category=category,
            title=title,
            content=content,
            author=author,
            agent_id=agent_id,
            service_name=service_name,
            tags=tags or [],
            metadata=metadata or {},
        )

        table = self._table_name()
        tags_value = json.dumps(devlog.tags) if not self.adapter.supports_arrays else devlog.tags
        metadata_value = json.dumps(devlog.metadata)

        if self.adapter.placeholder_style == "dollar":
            await self.adapter.execute(
                f"""
                INSERT INTO {table}
                    (id, category, title, content, author, agent_id, service_name, tags, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11)
                """,
                devlog.id, devlog.category, devlog.title, devlog.content,
                devlog.author, devlog.agent_id, devlog.service_name,
                tags_value, metadata_value,
                devlog.created_at, devlog.updated_at,
            )
        else:
            await self.adapter.execute(
                f"""
                INSERT INTO {table}
                    (id, category, title, content, author, agent_id, service_name, tags, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                devlog.id, devlog.category, devlog.title, devlog.content,
                devlog.author, devlog.agent_id, devlog.service_name,
                tags_value, metadata_value,
                devlog.created_at.isoformat() if devlog.created_at else None,
                devlog.updated_at.isoformat() if devlog.updated_at else None,
            )

        logger.info(f"Created devlog: {devlog.id} [{devlog.category}] {devlog.title}")
        return devlog

    async def get(self, devlog_id: str) -> Devlog | None:
        """Get a devlog by ID."""
        table = self._table_name()
        query = self.adapter.format_query(
            f"SELECT * FROM {table} WHERE id = $1 AND deleted_at IS NULL"
        )
        row = await self.adapter.fetchrow(query, devlog_id)
        if row:
            return Devlog.from_dict(row)
        return None

    async def update(
        self,
        devlog_id: str,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Devlog | None:
        """
        Update a devlog entry.

        Args:
            devlog_id: Devlog ID
            title: New title
            content: New content
            category: New category
            tags: New tags (replaces existing)
            metadata: New metadata (replaces existing)

        Returns:
            Updated Devlog or None if not found
        """
        if category and category not in DEVLOG_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. "
                f"Must be one of: {', '.join(DEVLOG_CATEGORIES)}"
            )

        # Build dynamic update
        updates = []
        params = []

        if title is not None:
            updates.append("title")
            params.append(title)

        if content is not None:
            updates.append("content")
            params.append(content)

        if category is not None:
            updates.append("category")
            params.append(category)

        if tags is not None:
            updates.append("tags")
            params.append(json.dumps(tags) if not self.adapter.supports_arrays else tags)

        if metadata is not None:
            updates.append("metadata")
            params.append(json.dumps(metadata))

        if not updates:
            return await self.get(devlog_id)

        # Add updated_at
        updates.append("updated_at")
        now = datetime.utcnow()
        params.append(now.isoformat() if self.adapter.placeholder_style == "qmark" else now)

        table = self._table_name()
        params.append(devlog_id)

        if self.adapter.placeholder_style == "dollar":
            set_clause = ", ".join([f"{col} = ${i+1}" for i, col in enumerate(updates)])
            # Handle JSONB casting for metadata
            set_clause = set_clause.replace("metadata = $", "metadata = $") + "::jsonb" if "metadata" in updates else set_clause
            query = f"""
                UPDATE {table}
                SET {set_clause}
                WHERE id = ${len(params)} AND deleted_at IS NULL
            """
        else:
            set_clause = ", ".join([f"{col} = ?" for col in updates])
            query = f"""
                UPDATE {table}
                SET {set_clause}
                WHERE id = ? AND deleted_at IS NULL
            """

        await self.adapter.execute(query, *params)
        return await self.get(devlog_id)

    async def delete(self, devlog_id: str) -> bool:
        """Soft delete a devlog entry."""
        table = self._table_name()
        now = datetime.utcnow()

        if self.adapter.placeholder_style == "dollar":
            result = await self.adapter.execute(
                f"UPDATE {table} SET deleted_at = $1 WHERE id = $2 AND deleted_at IS NULL",
                now, devlog_id,
            )
        else:
            result = await self.adapter.execute(
                f"UPDATE {table} SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                now.isoformat(), devlog_id,
            )

        return "1" in result

    async def list(
        self,
        category: str | None = None,
        author: str | None = None,
        agent_id: str | None = None,
        service_name: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Devlog]:
        """
        List devlogs with optional filters.

        Args:
            category: Filter by category
            author: Filter by author
            agent_id: Filter by agent
            service_name: Filter by service
            tags: Filter by tags (any match)
            limit: Max results
            offset: Pagination offset

        Returns:
            List of Devlog objects
        """
        conditions = ["deleted_at IS NULL"]
        params = []

        if category:
            if category not in DEVLOG_CATEGORIES:
                raise ValueError(f"Invalid category '{category}'")
            conditions.append(f"category = ${len(params)+1}" if self.adapter.placeholder_style == "dollar" else "category = ?")
            params.append(category)

        if author:
            conditions.append(f"author = ${len(params)+1}" if self.adapter.placeholder_style == "dollar" else "author = ?")
            params.append(author)

        if agent_id:
            conditions.append(f"agent_id = ${len(params)+1}" if self.adapter.placeholder_style == "dollar" else "agent_id = ?")
            params.append(agent_id)

        if service_name:
            conditions.append(f"service_name = ${len(params)+1}" if self.adapter.placeholder_style == "dollar" else "service_name = ?")
            params.append(service_name)

        if tags and self.adapter.supports_arrays:
            # PostgreSQL array overlap
            conditions.append(f"tags && ${len(params)+1}")
            params.append(tags)
        elif tags:
            # SQLite: check if any tag is in the JSON array
            tag_conditions = []
            for tag in tags:
                tag_conditions.append(f"tags LIKE '%\"{tag}\"%'")
            if tag_conditions:
                conditions.append(f"({' OR '.join(tag_conditions)})")

        table = self._table_name()
        where_clause = " AND ".join(conditions)

        if self.adapter.placeholder_style == "dollar":
            query = f"""
                SELECT * FROM {table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${len(params)+1} OFFSET ${len(params)+2}
            """
        else:
            query = f"""
                SELECT * FROM {table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """

        params.extend([limit, offset])
        rows = await self.adapter.fetch(query, *params)
        return [Devlog.from_dict(row) for row in rows]

    async def search(
        self,
        query: str,
        category: str | None = None,
        service_name: str | None = None,
        limit: int = 20,
    ) -> builtins.list[Devlog]:
        """
        Full-text search across devlogs.

        On PostgreSQL: Uses tsvector/tsquery with ranking
        On SQLite: Falls back to LIKE wildcards

        Args:
            query: Search query
            category: Optional category filter
            service_name: Optional service filter
            limit: Max results

        Returns:
            List of Devlog objects ranked by relevance
        """
        table = self._table_name()

        # Build additional where clause
        where_parts = []
        if category:
            where_parts.append(f"category = '{category}'")
        if service_name:
            where_parts.append(f"service_name = '{service_name}'")

        where_clause = " AND ".join(where_parts) if where_parts else None

        rows = await self.adapter.search_text(
            table=table,
            query=query,
            columns=["title", "content"],
            limit=limit,
            where_clause=where_clause,
        )
        return [Devlog.from_dict(row) for row in rows]

    def get_categories(self) -> builtins.list[str]:
        """Get list of valid categories."""
        return list(DEVLOG_CATEGORIES)
