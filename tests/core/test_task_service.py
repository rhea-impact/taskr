"""
Tests for Task Service.
"""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
async def task_service_with_db():
    """Create a TaskService with a temporary SQLite database."""
    from taskr.db.sqlite import SQLiteAdapter
    from taskr.services.tasks import TaskService

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        adapter = SQLiteAdapter(str(db_path))
        await adapter.connect()

        # Create tasks table
        await adapter.execute("""
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'open',
                priority TEXT DEFAULT 'medium',
                assignee TEXT,
                tags TEXT DEFAULT '[]',
                created_by TEXT,
                due_at TEXT,
                completed_at TEXT,
                created_at TEXT,
                updated_at TEXT,
                deleted_at TEXT
            )
        """)

        service = TaskService(adapter=adapter)
        yield service

        await adapter.close()


class TestTaskServiceCreate:
    """Tests for TaskService.create()."""

    @pytest.mark.asyncio
    async def test_create_task_minimal(self, task_service_with_db):
        """Test creating a task with minimal data."""
        service = task_service_with_db

        task = await service.create(title="Test task")

        assert task.title == "Test task"
        assert task.status == "open"
        assert task.priority == "medium"
        assert task.id is not None

    @pytest.mark.asyncio
    async def test_create_task_full(self, task_service_with_db):
        """Test creating a task with all fields."""
        service = task_service_with_db

        task = await service.create(
            title="Full task",
            description="A detailed description",
            status="in_progress",
            priority="high",
            assignee="john",
            tags=["bug", "urgent"],
            created_by="jane",
        )

        assert task.title == "Full task"
        assert task.description == "A detailed description"
        assert task.status == "in_progress"
        assert task.priority == "high"
        assert task.assignee == "john"
        assert task.tags == ["bug", "urgent"]
        assert task.created_by == "jane"

    @pytest.mark.asyncio
    async def test_create_task_invalid_status(self, task_service_with_db):
        """Test that invalid status raises error."""
        service = task_service_with_db

        with pytest.raises(ValueError) as exc:
            await service.create(title="Test", status="invalid")

        assert "Invalid status" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_task_invalid_priority(self, task_service_with_db):
        """Test that invalid priority raises error."""
        service = task_service_with_db

        with pytest.raises(ValueError) as exc:
            await service.create(title="Test", priority="super-high")

        assert "Invalid priority" in str(exc.value)


class TestTaskServiceGet:
    """Tests for TaskService.get()."""

    @pytest.mark.asyncio
    async def test_get_existing_task(self, task_service_with_db):
        """Test getting an existing task."""
        service = task_service_with_db

        created = await service.create(title="Test task")
        fetched = await service.get(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == "Test task"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, task_service_with_db):
        """Test getting a task that doesn't exist."""
        service = task_service_with_db

        fetched = await service.get("nonexistent-id")

        assert fetched is None

    @pytest.mark.asyncio
    async def test_get_deleted_task_returns_none(self, task_service_with_db):
        """Test that soft-deleted tasks are not returned."""
        service = task_service_with_db

        created = await service.create(title="To delete")
        await service.delete(created.id)

        fetched = await service.get(created.id)
        assert fetched is None


class TestTaskServiceUpdate:
    """Tests for TaskService.update()."""

    @pytest.mark.asyncio
    async def test_update_title(self, task_service_with_db):
        """Test updating task title."""
        service = task_service_with_db

        created = await service.create(title="Original")
        updated = await service.update(created.id, title="Updated")

        assert updated.title == "Updated"

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, task_service_with_db):
        """Test updating multiple fields at once."""
        service = task_service_with_db

        created = await service.create(title="Test")
        updated = await service.update(
            created.id,
            title="New title",
            status="in_progress",
            priority="high",
            assignee="alice",
        )

        assert updated.title == "New title"
        assert updated.status == "in_progress"
        assert updated.priority == "high"
        assert updated.assignee == "alice"

    @pytest.mark.asyncio
    async def test_update_status_to_done_sets_completed_at(self, task_service_with_db):
        """Test that setting status to done sets completed_at."""
        service = task_service_with_db

        created = await service.create(title="Test")
        updated = await service.update(created.id, status="done")

        assert updated.status == "done"
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, task_service_with_db):
        """Test updating a nonexistent task returns None."""
        service = task_service_with_db

        updated = await service.update("nonexistent", title="New")

        assert updated is None

    @pytest.mark.asyncio
    async def test_update_invalid_status(self, task_service_with_db):
        """Test that invalid status raises error."""
        service = task_service_with_db

        created = await service.create(title="Test")

        with pytest.raises(ValueError):
            await service.update(created.id, status="invalid")


class TestTaskServiceList:
    """Tests for TaskService.list()."""

    @pytest.mark.asyncio
    async def test_list_empty(self, task_service_with_db):
        """Test listing when no tasks exist."""
        service = task_service_with_db

        tasks = await service.list()

        assert tasks == []

    @pytest.mark.asyncio
    async def test_list_returns_tasks(self, task_service_with_db):
        """Test listing tasks."""
        service = task_service_with_db

        await service.create(title="Task 1")
        await service.create(title="Task 2")
        await service.create(title="Task 3")

        tasks = await service.list()

        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, task_service_with_db):
        """Test filtering by status."""
        service = task_service_with_db

        await service.create(title="Open task", status="open")
        await service.create(title="Done task", status="done")

        open_tasks = await service.list(status="open")
        done_tasks = await service.list(status="done")

        assert len(open_tasks) == 1
        assert open_tasks[0].title == "Open task"
        assert len(done_tasks) == 1
        assert done_tasks[0].title == "Done task"

    @pytest.mark.asyncio
    async def test_list_filter_by_priority(self, task_service_with_db):
        """Test filtering by priority."""
        service = task_service_with_db

        await service.create(title="Low", priority="low")
        await service.create(title="High", priority="high")

        high_tasks = await service.list(priority="high")

        assert len(high_tasks) == 1
        assert high_tasks[0].title == "High"

    @pytest.mark.asyncio
    async def test_list_filter_by_assignee(self, task_service_with_db):
        """Test filtering by assignee."""
        service = task_service_with_db

        await service.create(title="Alice task", assignee="alice")
        await service.create(title="Bob task", assignee="bob")

        alice_tasks = await service.list(assignee="alice")

        assert len(alice_tasks) == 1
        assert alice_tasks[0].title == "Alice task"

    @pytest.mark.asyncio
    async def test_list_respects_limit(self, task_service_with_db):
        """Test that limit is respected."""
        service = task_service_with_db

        for i in range(10):
            await service.create(title=f"Task {i}")

        tasks = await service.list(limit=3)

        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_list_excludes_deleted(self, task_service_with_db):
        """Test that deleted tasks are excluded."""
        service = task_service_with_db

        created = await service.create(title="To delete")
        await service.create(title="To keep")
        await service.delete(created.id)

        tasks = await service.list()

        assert len(tasks) == 1
        assert tasks[0].title == "To keep"


class TestTaskServiceSearch:
    """Tests for TaskService.search()."""

    @pytest.mark.asyncio
    async def test_search_by_title(self, task_service_with_db):
        """Test searching by title."""
        service = task_service_with_db

        await service.create(title="Authentication bug")
        await service.create(title="Database migration")
        await service.create(title="Auth token refresh")

        results = await service.search("auth")

        assert len(results) == 2
        titles = [r.title for r in results]
        assert "Authentication bug" in titles
        assert "Auth token refresh" in titles

    @pytest.mark.asyncio
    async def test_search_by_description(self, task_service_with_db):
        """Test searching by description."""
        service = task_service_with_db

        await service.create(title="Task 1", description="Fix the login flow")
        await service.create(title="Task 2", description="Update database schema")

        results = await service.search("login")

        assert len(results) == 1
        assert results[0].title == "Task 1"

    @pytest.mark.asyncio
    async def test_search_no_results(self, task_service_with_db):
        """Test search with no matches."""
        service = task_service_with_db

        await service.create(title="Some task")

        results = await service.search("nonexistent")

        assert results == []


class TestTaskServiceDelete:
    """Tests for TaskService.delete()."""

    @pytest.mark.asyncio
    async def test_delete_existing_task(self, task_service_with_db):
        """Test soft deleting a task."""
        service = task_service_with_db

        created = await service.create(title="To delete")
        result = await service.delete(created.id)

        assert result is True

        # Should not be retrievable
        fetched = await service.get(created.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self, task_service_with_db):
        """Test deleting a nonexistent task."""
        service = task_service_with_db

        result = await service.delete("nonexistent")

        assert result is False


class TestTaskServiceHelpers:
    """Tests for TaskService helper methods."""

    @pytest.mark.asyncio
    async def test_assign(self, task_service_with_db):
        """Test assigning a task."""
        service = task_service_with_db

        created = await service.create(title="Unassigned")
        updated = await service.assign(created.id, "alice")

        assert updated.assignee == "alice"

    @pytest.mark.asyncio
    async def test_close(self, task_service_with_db):
        """Test closing a task."""
        service = task_service_with_db

        created = await service.create(title="Open task")
        updated = await service.close(created.id)

        assert updated.status == "done"
        assert updated.completed_at is not None
