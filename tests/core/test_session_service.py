"""
Tests for Session Service.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta


@pytest.fixture
async def session_service_with_db():
    """Create a SessionService with a temporary SQLite database."""
    from taskr.db.sqlite import SQLiteAdapter
    from taskr.services.sessions import SessionService

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        adapter = SQLiteAdapter(str(db_path))
        await adapter.connect()

        # Create sessions table
        await adapter.execute("""
            CREATE TABLE agent_sessions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                context TEXT,
                summary TEXT,
                handoff_notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # Create activity table
        await adapter.execute("""
            CREATE TABLE agent_activity (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                session_id TEXT,
                activity_type TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                repo TEXT,
                notes TEXT,
                created_at TEXT
            )
        """)

        service = SessionService(adapter=adapter)
        yield service

        await adapter.close()


class TestSessionServiceStart:
    """Tests for SessionService.start()."""

    @pytest.mark.asyncio
    async def test_start_session(self, session_service_with_db):
        """Test starting a new session."""
        service = session_service_with_db

        result = await service.start(agent_id="test-agent")

        assert "session_id" in result
        assert result["agent_id"] == "test-agent"
        assert result["started_at"] is not None

    @pytest.mark.asyncio
    async def test_start_session_with_context(self, session_service_with_db):
        """Test starting a session with context."""
        service = session_service_with_db

        result = await service.start(
            agent_id="test-agent",
            context="Working on feature X",
        )

        assert result["context"] == "Working on feature X"

    @pytest.mark.asyncio
    async def test_start_session_returns_handoff_notes(self, session_service_with_db):
        """Test that start returns handoff notes from previous session."""
        service = session_service_with_db

        # Start and end a session with handoff notes
        session1 = await service.start(agent_id="test-agent")
        await service.end(
            session_id=session1["session_id"],
            summary="Did some work",
            handoff_notes="Remember to check the tests",
        )

        # Start new session
        session2 = await service.start(agent_id="test-agent")

        assert session2["handoff_notes"] == "Remember to check the tests"
        assert session2["last_summary"] == "Did some work"


class TestSessionServiceEnd:
    """Tests for SessionService.end()."""

    @pytest.mark.asyncio
    async def test_end_session(self, session_service_with_db):
        """Test ending a session."""
        service = session_service_with_db

        session = await service.start(agent_id="test-agent")
        result = await service.end(
            session_id=session["session_id"],
            summary="Completed the task",
        )

        assert result["session_id"] == session["session_id"]
        assert result["summary"] == "Completed the task"
        assert result["ended_at"] is not None

    @pytest.mark.asyncio
    async def test_end_session_with_handoff_notes(self, session_service_with_db):
        """Test ending a session with handoff notes."""
        service = session_service_with_db

        session = await service.start(agent_id="test-agent")
        result = await service.end(
            session_id=session["session_id"],
            summary="Completed the task",
            handoff_notes="Need to verify edge cases",
        )

        assert result["summary"] == "Completed the task"

    @pytest.mark.asyncio
    async def test_end_session_calculates_duration(self, session_service_with_db):
        """Test that duration is calculated."""
        service = session_service_with_db

        session = await service.start(agent_id="test-agent")
        result = await service.end(
            session_id=session["session_id"],
            summary="Quick task",
        )

        assert result["duration_seconds"] is not None
        assert result["duration_seconds"] >= 0


class TestSessionServiceClaimWork:
    """Tests for SessionService.claim_work()."""

    @pytest.mark.asyncio
    async def test_claim_work_success(self, session_service_with_db):
        """Test successfully claiming work."""
        service = session_service_with_db

        result = await service.claim_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
        )

        assert result["claimed"] is True
        assert "claim_id" in result

    @pytest.mark.asyncio
    async def test_claim_work_already_claimed(self, session_service_with_db):
        """Test claiming work that's already claimed."""
        service = session_service_with_db

        # First agent claims
        await service.claim_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
        )

        # Second agent tries to claim
        result = await service.claim_work(
            agent_id="agent-2",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
        )

        assert result["claimed"] is False
        assert result["claimed_by"] == "agent-1"

    @pytest.mark.asyncio
    async def test_claim_work_after_release(self, session_service_with_db):
        """Test claiming work after it's been released."""
        service = session_service_with_db

        # First agent claims and releases
        await service.claim_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
        )
        await service.release_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
            status="completed",
        )

        # Second agent can now claim
        result = await service.claim_work(
            agent_id="agent-2",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
        )

        assert result["claimed"] is True

    @pytest.mark.asyncio
    async def test_claim_different_work_items(self, session_service_with_db):
        """Test claiming different work items."""
        service = session_service_with_db

        result1 = await service.claim_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="1",
            repo="owner/repo",
        )
        result2 = await service.claim_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="2",
            repo="owner/repo",
        )

        assert result1["claimed"] is True
        assert result2["claimed"] is True


class TestSessionServiceReleaseWork:
    """Tests for SessionService.release_work()."""

    @pytest.mark.asyncio
    async def test_release_work(self, session_service_with_db):
        """Test releasing claimed work."""
        service = session_service_with_db

        await service.claim_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
        )

        result = await service.release_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
            status="completed",
        )

        assert result["released"] is True
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_release_work_with_notes(self, session_service_with_db):
        """Test releasing work with notes."""
        service = session_service_with_db

        await service.claim_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
        )

        result = await service.release_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
            status="blocked",
            notes="Waiting on dependency",
        )

        assert result["released"] is True
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_release_work_different_statuses(self, session_service_with_db):
        """Test releasing work with different statuses."""
        service = session_service_with_db

        for status in ["completed", "blocked", "deferred"]:
            await service.claim_work(
                agent_id="agent-1",
                work_type="issue",
                work_id=status,
                repo="owner/repo",
            )
            result = await service.release_work(
                agent_id="agent-1",
                work_type="issue",
                work_id=status,
                repo="owner/repo",
                status=status,
            )
            assert result["status"] == status


class TestSessionServiceWhatChanged:
    """Tests for SessionService.what_changed()."""

    @pytest.mark.asyncio
    async def test_what_changed_empty(self, session_service_with_db):
        """Test what_changed when nothing has changed."""
        service = session_service_with_db

        result = await service.what_changed(since=datetime.utcnow() - timedelta(hours=1))

        assert result["activity_count"] == 0
        assert result["session_count"] == 0

    @pytest.mark.asyncio
    async def test_what_changed_with_activities(self, session_service_with_db):
        """Test what_changed returns recent activities."""
        service = session_service_with_db

        # Create some activity
        await service.claim_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="123",
            repo="owner/repo",
        )

        result = await service.what_changed(since=datetime.utcnow() - timedelta(hours=1))

        assert result["activity_count"] >= 1
        assert len(result["activities"]) >= 1

    @pytest.mark.asyncio
    async def test_what_changed_with_sessions(self, session_service_with_db):
        """Test what_changed returns recent sessions."""
        service = session_service_with_db

        await service.start(agent_id="test-agent")

        result = await service.what_changed(since=datetime.utcnow() - timedelta(hours=1))

        assert result["session_count"] >= 1

    @pytest.mark.asyncio
    async def test_what_changed_filter_by_agent(self, session_service_with_db):
        """Test what_changed filters by agent."""
        service = session_service_with_db

        await service.claim_work(
            agent_id="agent-1",
            work_type="issue",
            work_id="1",
            repo="owner/repo",
        )
        await service.claim_work(
            agent_id="agent-2",
            work_type="issue",
            work_id="2",
            repo="owner/repo",
        )

        result = await service.what_changed(
            since=datetime.utcnow() - timedelta(hours=1),
            agent_id="agent-1",
        )

        assert result["activity_count"] == 1
        assert result["activities"][0]["agent_id"] == "agent-1"


class TestSessionServiceGetSession:
    """Tests for SessionService.get_session()."""

    @pytest.mark.asyncio
    async def test_get_session(self, session_service_with_db):
        """Test getting a session by ID."""
        service = session_service_with_db

        started = await service.start(agent_id="test-agent")
        session = await service.get_session(started["session_id"])

        assert session is not None
        assert session.agent_id == "test-agent"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_service_with_db):
        """Test getting a nonexistent session."""
        service = session_service_with_db

        session = await service.get_session("nonexistent")

        assert session is None


class TestSessionServiceListSessions:
    """Tests for SessionService.list_sessions()."""

    @pytest.mark.asyncio
    async def test_list_sessions(self, session_service_with_db):
        """Test listing sessions."""
        service = session_service_with_db

        await service.start(agent_id="agent-1")
        await service.start(agent_id="agent-2")

        sessions = await service.list_sessions()

        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_list_sessions_filter_by_agent(self, session_service_with_db):
        """Test filtering sessions by agent."""
        service = session_service_with_db

        await service.start(agent_id="agent-1")
        await service.start(agent_id="agent-1")
        await service.start(agent_id="agent-2")

        sessions = await service.list_sessions(agent_id="agent-1")

        assert len(sessions) == 2
        assert all(s.agent_id == "agent-1" for s in sessions)

    @pytest.mark.asyncio
    async def test_list_sessions_active_only(self, session_service_with_db):
        """Test filtering for active sessions only."""
        service = session_service_with_db

        session1 = await service.start(agent_id="agent-1")
        await service.start(agent_id="agent-2")

        # End one session
        await service.end(session1["session_id"], summary="Done")

        active = await service.list_sessions(active_only=True)

        assert len(active) == 1
        assert active[0].ended_at is None

    @pytest.mark.asyncio
    async def test_list_sessions_respects_limit(self, session_service_with_db):
        """Test that limit is respected."""
        service = session_service_with_db

        for i in range(10):
            await service.start(agent_id=f"agent-{i}")

        sessions = await service.list_sessions(limit=5)

        assert len(sessions) == 5
