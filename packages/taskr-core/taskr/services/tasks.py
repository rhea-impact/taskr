"""
Task Service for Taskr.

CRUD operations for tasks with support for both PostgreSQL and SQLite.
"""

import builtins
import json
import logging
from datetime import datetime

from taskr.db import get_adapter
from taskr.models.task import TASK_PRIORITIES, TASK_STATUSES, Task

logger = logging.getLogger(__name__)


class TaskService:
    """
    Service for managing tasks.

    Provides CRUD operations that work across PostgreSQL and SQLite.
    """

    def __init__(self, adapter=None):
        """
        Initialize task service.

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
            return "taskr.tasks"
        return "tasks"  # SQLite

    async def create(
        self,
        title: str,
        description: str | None = None,
        status: str = "open",
        priority: str = "medium",
        assignee: str | None = None,
        tags: list[str] | None = None,
        created_by: str | None = None,
        due_at: datetime | None = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            title: Task title
            description: Task description
            status: Status (open, in_progress, done, cancelled)
            priority: Priority (low, medium, high, critical)
            assignee: Assigned user
            tags: List of tags
            created_by: Who created the task
            due_at: Optional due date

        Returns:
            Created Task object
        """
        if status not in TASK_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(TASK_STATUSES)}")
        if priority not in TASK_PRIORITIES:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(TASK_PRIORITIES)}")

        task = Task(
            title=title,
            description=description,
            status=status,
            priority=priority,
            assignee=assignee,
            tags=tags or [],
            created_by=created_by,
            due_at=due_at,
        )

        table = self._table_name()
        tags_value = json.dumps(task.tags) if not self.adapter.supports_arrays else task.tags

        if self.adapter.placeholder_style == "dollar":
            await self.adapter.execute(
                f"""
                INSERT INTO {table}
                    (id, title, description, status, priority, assignee, tags, created_by, due_at, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                task.id, task.title, task.description, task.status, task.priority,
                task.assignee, tags_value, task.created_by,
                task.due_at, task.created_at, task.updated_at,
            )
        else:
            await self.adapter.execute(
                f"""
                INSERT INTO {table}
                    (id, title, description, status, priority, assignee, tags, created_by, due_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                task.id, task.title, task.description, task.status, task.priority,
                task.assignee, tags_value, task.created_by,
                task.due_at.isoformat() if task.due_at else None,
                task.created_at.isoformat() if task.created_at else None,
                task.updated_at.isoformat() if task.updated_at else None,
            )

        logger.info(f"Created task: {task.id} - {task.title}")
        return task

    async def get(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        table = self._table_name()
        query = self.adapter.format_query(
            f"SELECT * FROM {table} WHERE id = $1 AND deleted_at IS NULL"
        )
        row = await self.adapter.fetchrow(query, task_id)
        if row:
            return Task.from_dict(row)
        return None

    async def update(
        self,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        tags: list[str] | None = None,
        due_at: datetime | None = None,
    ) -> Task | None:
        """
        Update a task.

        Args:
            task_id: Task ID
            title: New title
            description: New description
            status: New status
            priority: New priority
            assignee: New assignee
            tags: New tags
            due_at: New due date

        Returns:
            Updated Task or None if not found
        """
        if status and status not in TASK_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(TASK_STATUSES)}")
        if priority and priority not in TASK_PRIORITIES:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(TASK_PRIORITIES)}")

        # Build dynamic update
        updates = []
        params = []

        if title is not None:
            updates.append("title")
            params.append(title)

        if description is not None:
            updates.append("description")
            params.append(description)

        if status is not None:
            updates.append("status")
            params.append(status)
            # Set completed_at if status is done
            if status == "done":
                updates.append("completed_at")
                params.append(datetime.utcnow().isoformat() if self.adapter.placeholder_style == "qmark" else datetime.utcnow())

        if priority is not None:
            updates.append("priority")
            params.append(priority)

        if assignee is not None:
            updates.append("assignee")
            params.append(assignee)

        if tags is not None:
            updates.append("tags")
            params.append(json.dumps(tags) if not self.adapter.supports_arrays else tags)

        if due_at is not None:
            updates.append("due_at")
            params.append(due_at.isoformat() if self.adapter.placeholder_style == "qmark" else due_at)

        if not updates:
            return await self.get(task_id)

        # Add updated_at
        updates.append("updated_at")
        now = datetime.utcnow()
        params.append(now.isoformat() if self.adapter.placeholder_style == "qmark" else now)

        table = self._table_name()
        params.append(task_id)

        if self.adapter.placeholder_style == "dollar":
            set_clause = ", ".join([f"{col} = ${i+1}" for i, col in enumerate(updates)])
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
        return await self.get(task_id)

    async def delete(self, task_id: str) -> bool:
        """Soft delete a task."""
        table = self._table_name()
        now = datetime.utcnow()

        if self.adapter.placeholder_style == "dollar":
            result = await self.adapter.execute(
                f"UPDATE {table} SET deleted_at = $1 WHERE id = $2 AND deleted_at IS NULL",
                now, task_id,
            )
        else:
            result = await self.adapter.execute(
                f"UPDATE {table} SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                now.isoformat(), task_id,
            )

        return "1" in result  # Check if a row was updated

    async def list(
        self,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        created_by: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """
        List tasks with optional filters.

        Args:
            status: Filter by status
            priority: Filter by priority
            assignee: Filter by assignee
            created_by: Filter by creator
            limit: Max results
            offset: Pagination offset

        Returns:
            List of Task objects
        """
        conditions = ["deleted_at IS NULL"]
        params = []

        if status:
            conditions.append(f"status = ${len(params)+1}" if self.adapter.placeholder_style == "dollar" else "status = ?")
            params.append(status)

        if priority:
            conditions.append(f"priority = ${len(params)+1}" if self.adapter.placeholder_style == "dollar" else "priority = ?")
            params.append(priority)

        if assignee:
            conditions.append(f"assignee = ${len(params)+1}" if self.adapter.placeholder_style == "dollar" else "assignee = ?")
            params.append(assignee)

        if created_by:
            conditions.append(f"created_by = ${len(params)+1}" if self.adapter.placeholder_style == "dollar" else "created_by = ?")
            params.append(created_by)

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
        return [Task.from_dict(row) for row in rows]

    async def search(
        self,
        query: str,
        status: str | None = None,
        limit: int = 20,
    ) -> builtins.list[Task]:
        """
        Search tasks by title and description.

        Args:
            query: Search query
            status: Optional status filter
            limit: Max results

        Returns:
            List of matching Task objects
        """
        table = self._table_name()
        where_clause = None
        if status:
            where_clause = f"status = '{status}'"

        rows = await self.adapter.search_text(
            table=table,
            query=query,
            columns=["title", "description"],
            limit=limit,
            where_clause=where_clause,
        )
        return [Task.from_dict(row) for row in rows]

    async def assign(self, task_id: str, assignee: str) -> Task | None:
        """Assign a task to a user."""
        return await self.update(task_id, assignee=assignee)

    async def close(self, task_id: str) -> Task | None:
        """Mark a task as done."""
        return await self.update(task_id, status="done")
