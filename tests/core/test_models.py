"""
Tests for taskr data models.
"""

import pytest
from datetime import datetime


class TestTaskModel:
    """Tests for Task model."""

    def test_task_creation(self):
        """Test creating a task with defaults."""
        from taskr.models.task import Task

        task = Task(title="Test task")

        assert task.title == "Test task"
        assert task.status == "open"
        assert task.priority == "medium"
        assert task.id is not None
        assert task.created_at is not None

    def test_task_is_open(self):
        """Test is_open property."""
        from taskr.models.task import Task

        task = Task(title="Test", status="open")
        assert task.is_open is True

        task.status = "in_progress"
        assert task.is_open is True

        task.status = "done"
        assert task.is_open is False

    def test_task_to_dict(self):
        """Test serialization to dict."""
        from taskr.models.task import Task

        task = Task(
            title="Test",
            description="Description",
            tags=["bug", "urgent"],
        )

        result = task.to_dict()

        assert result["title"] == "Test"
        assert result["description"] == "Description"
        assert result["tags"] == ["bug", "urgent"]
        assert "id" in result
        assert "created_at" in result

    def test_task_from_dict(self):
        """Test deserialization from dict."""
        from taskr.models.task import Task

        data = {
            "id": "test-id",
            "title": "Test",
            "status": "done",
            "tags": '["tag1", "tag2"]',  # JSON string (SQLite)
            "created_at": "2024-01-01T00:00:00",
        }

        task = Task.from_dict(data)

        assert task.id == "test-id"
        assert task.title == "Test"
        assert task.status == "done"
        assert task.tags == ["tag1", "tag2"]


class TestDevlogModel:
    """Tests for Devlog model."""

    def test_devlog_creation(self):
        """Test creating a devlog."""
        from taskr.models.devlog import Devlog

        devlog = Devlog(
            category="decision",
            title="Test decision",
            content="We decided to use X because Y.",
        )

        assert devlog.category == "decision"
        assert devlog.title == "Test decision"
        assert devlog.agent_id == "claude-code"

    def test_devlog_invalid_category(self):
        """Test that invalid category raises error."""
        from taskr.models.devlog import Devlog

        with pytest.raises(ValueError) as exc:
            Devlog(category="invalid", title="Test", content="Content")

        assert "Invalid category" in str(exc.value)

    def test_devlog_summary(self):
        """Test summary generation."""
        from taskr.models.devlog import Devlog

        devlog = Devlog(
            category="note",
            title="Test",
            content="A" * 200,
        )

        summary = devlog.summary(50)
        assert len(summary) == 50
        assert summary.endswith("...")


class TestSessionModel:
    """Tests for Session model."""

    def test_session_creation(self):
        """Test creating a session."""
        from taskr.models.session import Session

        session = Session(agent_id="test-agent")

        assert session.agent_id == "test-agent"
        assert session.is_active is True
        assert session.started_at is not None

    def test_session_duration(self):
        """Test duration calculation."""
        from taskr.models.session import Session
        from datetime import timedelta

        start = datetime.utcnow() - timedelta(hours=1)
        end = datetime.utcnow()

        session = Session(
            agent_id="test",
            started_at=start,
            ended_at=end,
        )

        duration = session.duration_seconds
        assert duration is not None
        assert 3500 < duration < 3700  # ~1 hour
