"""
Session Service for Taskr.

Agent session management with work claiming and handoff support.
"""

import logging
from datetime import datetime
from typing import Any

from taskr.db import get_adapter
from taskr.models.session import Activity, Session

logger = logging.getLogger(__name__)


class SessionService:
    """
    Service for managing agent sessions and work coordination.

    Enables:
    - Session tracking with handoff notes
    - Atomic work claiming to prevent duplicate effort
    - Activity logging
    """

    def __init__(self, adapter=None):
        """
        Initialize session service.

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

    def _sessions_table(self) -> str:
        """Get the sessions table name."""
        if self.adapter.supports_fts:  # PostgreSQL
            return "taskr.agent_sessions"
        return "agent_sessions"

    def _activity_table(self) -> str:
        """Get the activity table name."""
        if self.adapter.supports_fts:  # PostgreSQL
            return "taskr.agent_activity"
        return "agent_activity"

    async def start(
        self,
        agent_id: str,
        context: str | None = None,
    ) -> dict[str, Any]:
        """
        Start a new agent session.

        Returns context including:
        - Session ID
        - Recent devlogs (last 24 hours)
        - Handoff notes from previous session

        Args:
            agent_id: Unique identifier for the agent
            context: Optional purpose/context for this session

        Returns:
            Dict with session_id, handoff_notes, recent_devlogs
        """
        session = Session(agent_id=agent_id, context=context)

        # Get last session's handoff notes
        sessions_table = self._sessions_table()
        last_session = await self.adapter.fetchrow(
            self.adapter.format_query(f"""
                SELECT * FROM {sessions_table}
                WHERE agent_id = $1 AND ended_at IS NOT NULL
                ORDER BY ended_at DESC
                LIMIT 1
            """),
            agent_id,
        )

        handoff_notes = None
        last_summary = None
        if last_session:
            handoff_notes = last_session.get("handoff_notes")
            last_summary = last_session.get("summary")

        # Insert new session
        if self.adapter.placeholder_style == "dollar":
            await self.adapter.execute(
                f"""
                INSERT INTO {sessions_table}
                    (id, agent_id, started_at, context, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                session.id, session.agent_id, session.started_at,
                session.context, session.created_at, session.updated_at,
            )
        else:
            await self.adapter.execute(
                f"""
                INSERT INTO {sessions_table}
                    (id, agent_id, started_at, context, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                session.id, session.agent_id,
                session.started_at.isoformat() if session.started_at else None,
                session.context,
                session.created_at.isoformat() if session.created_at else None,
                session.updated_at.isoformat() if session.updated_at else None,
            )

        logger.info(f"Started session: {session.id} for agent {agent_id}")

        return {
            "session_id": session.id,
            "agent_id": agent_id,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "context": context,
            "handoff_notes": handoff_notes,
            "last_summary": last_summary,
        }

    async def end(
        self,
        session_id: str,
        summary: str,
        handoff_notes: str | None = None,
    ) -> dict[str, Any]:
        """
        End an agent session.

        Args:
            session_id: The session UUID
            summary: Summary of what was accomplished
            handoff_notes: Notes for the next session

        Returns:
            Dict with session end confirmation and duration
        """
        now = datetime.utcnow()
        sessions_table = self._sessions_table()

        # Update session
        if self.adapter.placeholder_style == "dollar":
            await self.adapter.execute(
                f"""
                UPDATE {sessions_table}
                SET ended_at = $1, summary = $2, handoff_notes = $3, updated_at = $4
                WHERE id = $5
                """,
                now, summary, handoff_notes, now, session_id,
            )
        else:
            await self.adapter.execute(
                f"""
                UPDATE {sessions_table}
                SET ended_at = ?, summary = ?, handoff_notes = ?, updated_at = ?
                WHERE id = ?
                """,
                now.isoformat(), summary, handoff_notes, now.isoformat(), session_id,
            )

        # Get session to calculate duration
        session = await self.adapter.fetchrow(
            self.adapter.format_query(
                f"SELECT * FROM {sessions_table} WHERE id = $1"
            ),
            session_id,
        )

        duration_seconds = None
        if session and session.get("started_at"):
            started = session["started_at"]
            if isinstance(started, str):
                started = datetime.fromisoformat(started.replace("Z", "+00:00"))
            duration_seconds = (now - started).total_seconds()

        logger.info(f"Ended session: {session_id}")

        return {
            "session_id": session_id,
            "ended_at": now.isoformat(),
            "summary": summary,
            "duration_seconds": duration_seconds,
        }

    async def claim_work(
        self,
        agent_id: str,
        work_type: str,
        work_id: str,
        repo: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Atomically claim work to prevent duplicate effort.

        Args:
            agent_id: Your agent identifier
            work_type: Type of work - 'issue', 'pr', or 'qa'
            work_id: GitHub issue number or work item ID
            repo: Repository in owner/repo format
            session_id: Optional session ID

        Returns:
            Dict with claim status and message
        """
        activity_table = self._activity_table()
        target_id = f"{repo}#{work_id}"

        # Check if already claimed (not released)
        existing = await self.adapter.fetchrow(
            self.adapter.format_query(f"""
                SELECT * FROM {activity_table}
                WHERE target_type = $1
                  AND target_id = $2
                  AND activity_type = 'claim_work'
                  AND NOT EXISTS (
                      SELECT 1 FROM {activity_table} r
                      WHERE r.target_type = {activity_table}.target_type
                        AND r.target_id = {activity_table}.target_id
                        AND r.activity_type = 'release_work'
                        AND r.created_at > {activity_table}.created_at
                  )
                ORDER BY created_at DESC
                LIMIT 1
            """),
            work_type, target_id,
        )

        if existing:
            return {
                "claimed": False,
                "message": f"Work already claimed by {existing.get('agent_id')}",
                "claimed_by": existing.get("agent_id"),
                "claimed_at": existing.get("created_at"),
            }

        # Claim the work
        activity = Activity(
            agent_id=agent_id,
            session_id=session_id,
            activity_type="claim_work",
            target_type=work_type,
            target_id=target_id,
            repo=repo,
        )

        if self.adapter.placeholder_style == "dollar":
            await self.adapter.execute(
                f"""
                INSERT INTO {activity_table}
                    (id, agent_id, session_id, activity_type, target_type, target_id, repo, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                activity.id, activity.agent_id, activity.session_id,
                activity.activity_type, activity.target_type, activity.target_id,
                activity.repo, activity.created_at,
            )
        else:
            await self.adapter.execute(
                f"""
                INSERT INTO {activity_table}
                    (id, agent_id, session_id, activity_type, target_type, target_id, repo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                activity.id, activity.agent_id, activity.session_id,
                activity.activity_type, activity.target_type, activity.target_id,
                activity.repo, activity.created_at.isoformat() if activity.created_at else None,
            )

        logger.info(f"Agent {agent_id} claimed work: {target_id}")

        return {
            "claimed": True,
            "message": f"Successfully claimed {work_type} {target_id}",
            "claim_id": activity.id,
        }

    async def release_work(
        self,
        agent_id: str,
        work_type: str,
        work_id: str,
        repo: str,
        status: str = "completed",
        notes: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Release claimed work.

        Args:
            agent_id: Your agent identifier
            work_type: Type of work
            work_id: Work item ID
            repo: Repository
            status: Final status (completed, blocked, deferred)
            notes: Optional notes about the work
            session_id: Optional session ID

        Returns:
            Dict with release confirmation
        """
        activity_table = self._activity_table()
        target_id = f"{repo}#{work_id}"

        activity = Activity(
            agent_id=agent_id,
            session_id=session_id,
            activity_type="release_work",
            target_type=work_type,
            target_id=target_id,
            repo=repo,
            notes=f"[{status}] {notes}" if notes else f"[{status}]",
        )

        if self.adapter.placeholder_style == "dollar":
            await self.adapter.execute(
                f"""
                INSERT INTO {activity_table}
                    (id, agent_id, session_id, activity_type, target_type, target_id, repo, notes, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                activity.id, activity.agent_id, activity.session_id,
                activity.activity_type, activity.target_type, activity.target_id,
                activity.repo, activity.notes, activity.created_at,
            )
        else:
            await self.adapter.execute(
                f"""
                INSERT INTO {activity_table}
                    (id, agent_id, session_id, activity_type, target_type, target_id, repo, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                activity.id, activity.agent_id, activity.session_id,
                activity.activity_type, activity.target_type, activity.target_id,
                activity.repo, activity.notes, activity.created_at.isoformat() if activity.created_at else None,
            )

        logger.info(f"Agent {agent_id} released work: {target_id} [{status}]")

        return {
            "released": True,
            "message": f"Released {work_type} {target_id}",
            "status": status,
        }

    async def what_changed(
        self,
        since: datetime,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get changes since a timestamp.

        Useful for catching up on missed work.

        Args:
            since: Get changes after this timestamp
            agent_id: Optional filter by agent

        Returns:
            Dict with activities and sessions since timestamp
        """
        activity_table = self._activity_table()
        sessions_table = self._sessions_table()

        # Get activities
        if agent_id:
            if self.adapter.placeholder_style == "dollar":
                activities = await self.adapter.fetch(
                    f"""
                    SELECT * FROM {activity_table}
                    WHERE created_at > $1 AND agent_id = $2
                    ORDER BY created_at DESC
                    """,
                    since, agent_id,
                )
            else:
                activities = await self.adapter.fetch(
                    f"""
                    SELECT * FROM {activity_table}
                    WHERE created_at > ? AND agent_id = ?
                    ORDER BY created_at DESC
                    """,
                    since.isoformat(), agent_id,
                )
        else:
            if self.adapter.placeholder_style == "dollar":
                activities = await self.adapter.fetch(
                    f"""
                    SELECT * FROM {activity_table}
                    WHERE created_at > $1
                    ORDER BY created_at DESC
                    """,
                    since,
                )
            else:
                activities = await self.adapter.fetch(
                    f"""
                    SELECT * FROM {activity_table}
                    WHERE created_at > ?
                    ORDER BY created_at DESC
                    """,
                    since.isoformat(),
                )

        # Get sessions
        if self.adapter.placeholder_style == "dollar":
            sessions = await self.adapter.fetch(
                f"""
                SELECT * FROM {sessions_table}
                WHERE created_at > $1 OR ended_at > $1
                ORDER BY created_at DESC
                """,
                since,
            )
        else:
            sessions = await self.adapter.fetch(
                f"""
                SELECT * FROM {sessions_table}
                WHERE created_at > ? OR ended_at > ?
                ORDER BY created_at DESC
                """,
                since.isoformat(), since.isoformat(),
            )

        return {
            "since": since.isoformat(),
            "activities": [dict(a) for a in activities],
            "sessions": [dict(s) for s in sessions],
            "activity_count": len(activities),
            "session_count": len(sessions),
        }

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        sessions_table = self._sessions_table()
        row = await self.adapter.fetchrow(
            self.adapter.format_query(
                f"SELECT * FROM {sessions_table} WHERE id = $1"
            ),
            session_id,
        )
        if row:
            return Session.from_dict(row)
        return None

    async def list_sessions(
        self,
        agent_id: str | None = None,
        active_only: bool = False,
        limit: int = 20,
    ) -> list[Session]:
        """List sessions with optional filters."""
        sessions_table = self._sessions_table()
        conditions = []
        params = []

        if agent_id:
            conditions.append(f"agent_id = ${len(params)+1}" if self.adapter.placeholder_style == "dollar" else "agent_id = ?")
            params.append(agent_id)

        if active_only:
            conditions.append("ended_at IS NULL")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        if self.adapter.placeholder_style == "dollar":
            query = f"""
                SELECT * FROM {sessions_table}
                WHERE {where_clause}
                ORDER BY started_at DESC
                LIMIT ${len(params)+1}
            """
        else:
            query = f"""
                SELECT * FROM {sessions_table}
                WHERE {where_clause}
                ORDER BY started_at DESC
                LIMIT ?
            """

        params.append(limit)
        rows = await self.adapter.fetch(query, *params)
        return [Session.from_dict(row) for row in rows]
