"""
Tests for Devlog Service.
"""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
async def devlog_service_with_db():
    """Create a DevlogService with a temporary SQLite database."""
    from taskr.db.sqlite import SQLiteAdapter
    from taskr.services.devlogs import DevlogService

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        adapter = SQLiteAdapter(str(db_path))
        await adapter.connect()

        # Create devlogs table
        await adapter.execute("""
            CREATE TABLE devlogs (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author TEXT,
                agent_id TEXT DEFAULT 'claude-code',
                service_name TEXT,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT,
                deleted_at TEXT
            )
        """)

        service = DevlogService(adapter=adapter)
        yield service

        await adapter.close()


class TestDevlogServiceAdd:
    """Tests for DevlogService.add()."""

    @pytest.mark.asyncio
    async def test_add_devlog_minimal(self, devlog_service_with_db):
        """Test adding a devlog with minimal data."""
        service = devlog_service_with_db

        devlog = await service.add(
            category="note",
            title="Test note",
            content="This is a test note.",
        )

        assert devlog.category == "note"
        assert devlog.title == "Test note"
        assert devlog.content == "This is a test note."
        assert devlog.id is not None

    @pytest.mark.asyncio
    async def test_add_devlog_full(self, devlog_service_with_db):
        """Test adding a devlog with all fields."""
        service = devlog_service_with_db

        devlog = await service.add(
            category="decision",
            title="Architecture decision",
            content="We chose PostgreSQL because...",
            author="alice",
            agent_id="custom-agent",
            service_name="backend-api",
            tags=["architecture", "database"],
            metadata={"confidence": "high"},
        )

        assert devlog.category == "decision"
        assert devlog.title == "Architecture decision"
        assert devlog.author == "alice"
        assert devlog.agent_id == "custom-agent"
        assert devlog.service_name == "backend-api"
        assert devlog.tags == ["architecture", "database"]
        assert devlog.metadata == {"confidence": "high"}

    @pytest.mark.asyncio
    async def test_add_devlog_invalid_category(self, devlog_service_with_db):
        """Test that invalid category raises error."""
        service = devlog_service_with_db

        with pytest.raises(ValueError) as exc:
            await service.add(
                category="invalid_category",
                title="Test",
                content="Content",
            )

        assert "Invalid category" in str(exc.value)

    @pytest.mark.asyncio
    async def test_add_devlog_all_valid_categories(self, devlog_service_with_db):
        """Test that all valid categories work."""
        service = devlog_service_with_db
        valid_categories = [
            "feature", "bugfix", "deployment", "config", "incident",
            "refactor", "research", "decision", "migration", "note"
        ]

        for category in valid_categories:
            devlog = await service.add(
                category=category,
                title=f"Test {category}",
                content=f"Content for {category}",
            )
            assert devlog.category == category


class TestDevlogServiceGet:
    """Tests for DevlogService.get()."""

    @pytest.mark.asyncio
    async def test_get_existing_devlog(self, devlog_service_with_db):
        """Test getting an existing devlog."""
        service = devlog_service_with_db

        created = await service.add(
            category="note",
            title="Test",
            content="Content",
        )
        fetched = await service.get(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_devlog(self, devlog_service_with_db):
        """Test getting a devlog that doesn't exist."""
        service = devlog_service_with_db

        fetched = await service.get("nonexistent-id")

        assert fetched is None

    @pytest.mark.asyncio
    async def test_get_deleted_devlog_returns_none(self, devlog_service_with_db):
        """Test that soft-deleted devlogs are not returned."""
        service = devlog_service_with_db

        created = await service.add(
            category="note",
            title="To delete",
            content="Content",
        )
        await service.delete(created.id)

        fetched = await service.get(created.id)
        assert fetched is None


class TestDevlogServiceUpdate:
    """Tests for DevlogService.update()."""

    @pytest.mark.asyncio
    async def test_update_title(self, devlog_service_with_db):
        """Test updating devlog title."""
        service = devlog_service_with_db

        created = await service.add(
            category="note",
            title="Original",
            content="Content",
        )
        updated = await service.update(created.id, title="Updated")

        assert updated.title == "Updated"

    @pytest.mark.asyncio
    async def test_update_content(self, devlog_service_with_db):
        """Test updating devlog content."""
        service = devlog_service_with_db

        created = await service.add(
            category="note",
            title="Test",
            content="Original content",
        )
        updated = await service.update(created.id, content="Updated content")

        assert updated.content == "Updated content"

    @pytest.mark.asyncio
    async def test_update_category(self, devlog_service_with_db):
        """Test updating devlog category."""
        service = devlog_service_with_db

        created = await service.add(
            category="note",
            title="Test",
            content="Content",
        )
        updated = await service.update(created.id, category="decision")

        assert updated.category == "decision"

    @pytest.mark.asyncio
    async def test_update_tags(self, devlog_service_with_db):
        """Test updating devlog tags."""
        service = devlog_service_with_db

        created = await service.add(
            category="note",
            title="Test",
            content="Content",
            tags=["old-tag"],
        )
        updated = await service.update(created.id, tags=["new-tag", "another-tag"])

        assert updated.tags == ["new-tag", "another-tag"]

    @pytest.mark.asyncio
    async def test_update_invalid_category(self, devlog_service_with_db):
        """Test that invalid category raises error."""
        service = devlog_service_with_db

        created = await service.add(
            category="note",
            title="Test",
            content="Content",
        )

        with pytest.raises(ValueError):
            await service.update(created.id, category="invalid")


class TestDevlogServiceList:
    """Tests for DevlogService.list()."""

    @pytest.mark.asyncio
    async def test_list_empty(self, devlog_service_with_db):
        """Test listing when no devlogs exist."""
        service = devlog_service_with_db

        devlogs = await service.list()

        assert devlogs == []

    @pytest.mark.asyncio
    async def test_list_returns_devlogs(self, devlog_service_with_db):
        """Test listing devlogs."""
        service = devlog_service_with_db

        await service.add(category="note", title="Note 1", content="Content 1")
        await service.add(category="note", title="Note 2", content="Content 2")

        devlogs = await service.list()

        assert len(devlogs) == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_category(self, devlog_service_with_db):
        """Test filtering by category."""
        service = devlog_service_with_db

        await service.add(category="note", title="Note", content="Content")
        await service.add(category="decision", title="Decision", content="Content")
        await service.add(category="bugfix", title="Bugfix", content="Content")

        notes = await service.list(category="note")
        decisions = await service.list(category="decision")

        assert len(notes) == 1
        assert notes[0].title == "Note"
        assert len(decisions) == 1
        assert decisions[0].title == "Decision"

    @pytest.mark.asyncio
    async def test_list_filter_by_service_name(self, devlog_service_with_db):
        """Test filtering by service name."""
        service = devlog_service_with_db

        await service.add(
            category="note",
            title="API note",
            content="Content",
            service_name="backend-api",
        )
        await service.add(
            category="note",
            title="Frontend note",
            content="Content",
            service_name="frontend",
        )

        api_logs = await service.list(service_name="backend-api")

        assert len(api_logs) == 1
        assert api_logs[0].title == "API note"

    @pytest.mark.asyncio
    async def test_list_filter_by_author(self, devlog_service_with_db):
        """Test filtering by author."""
        service = devlog_service_with_db

        await service.add(
            category="note",
            title="Alice note",
            content="Content",
            author="alice",
        )
        await service.add(
            category="note",
            title="Bob note",
            content="Content",
            author="bob",
        )

        alice_logs = await service.list(author="alice")

        assert len(alice_logs) == 1
        assert alice_logs[0].title == "Alice note"

    @pytest.mark.asyncio
    async def test_list_respects_limit(self, devlog_service_with_db):
        """Test that limit is respected."""
        service = devlog_service_with_db

        for i in range(10):
            await service.add(category="note", title=f"Note {i}", content=f"Content {i}")

        devlogs = await service.list(limit=3)

        assert len(devlogs) == 3

    @pytest.mark.asyncio
    async def test_list_excludes_deleted(self, devlog_service_with_db):
        """Test that deleted devlogs are excluded."""
        service = devlog_service_with_db

        created = await service.add(category="note", title="To delete", content="Content")
        await service.add(category="note", title="To keep", content="Content")
        await service.delete(created.id)

        devlogs = await service.list()

        assert len(devlogs) == 1
        assert devlogs[0].title == "To keep"


class TestDevlogServiceSearch:
    """Tests for DevlogService.search()."""

    @pytest.mark.asyncio
    async def test_search_by_title(self, devlog_service_with_db):
        """Test searching by title."""
        service = devlog_service_with_db

        await service.add(
            category="decision",
            title="Database selection decision",
            content="We chose PostgreSQL",
        )
        await service.add(
            category="note",
            title="Meeting notes",
            content="Discussed timelines",
        )

        results = await service.search("database")

        assert len(results) == 1
        assert results[0].title == "Database selection decision"

    @pytest.mark.asyncio
    async def test_search_by_content(self, devlog_service_with_db):
        """Test searching by content."""
        service = devlog_service_with_db

        await service.add(
            category="bugfix",
            title="Fix login bug",
            content="The authentication token was expiring too early",
        )
        await service.add(
            category="note",
            title="General note",
            content="Nothing important here",
        )

        results = await service.search("authentication")

        assert len(results) == 1
        assert results[0].title == "Fix login bug"

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, devlog_service_with_db):
        """Test search with category filter."""
        service = devlog_service_with_db

        await service.add(
            category="decision",
            title="Auth decision",
            content="Use JWT tokens",
        )
        await service.add(
            category="bugfix",
            title="Auth bugfix",
            content="Fixed token refresh",
        )

        results = await service.search("auth", category="decision")

        assert len(results) == 1
        assert results[0].title == "Auth decision"


class TestDevlogServiceDelete:
    """Tests for DevlogService.delete()."""

    @pytest.mark.asyncio
    async def test_delete_existing_devlog(self, devlog_service_with_db):
        """Test soft deleting a devlog."""
        service = devlog_service_with_db

        created = await service.add(category="note", title="To delete", content="Content")
        result = await service.delete(created.id)

        assert result is True

        fetched = await service.get(created.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_devlog(self, devlog_service_with_db):
        """Test deleting a nonexistent devlog."""
        service = devlog_service_with_db

        result = await service.delete("nonexistent")

        assert result is False


class TestDevlogServiceHelpers:
    """Tests for DevlogService helper methods."""

    @pytest.mark.asyncio
    async def test_get_categories(self, devlog_service_with_db):
        """Test getting valid categories."""
        service = devlog_service_with_db

        categories = service.get_categories()

        assert "feature" in categories
        assert "bugfix" in categories
        assert "decision" in categories
        assert "note" in categories
        assert len(categories) == 10
