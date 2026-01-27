"""
Session and Activity models for Taskr.

Sessions track AI agent work periods with handoff support.
Activities log specific actions within sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class Session:
    """
    An agent session tracking a period of work.

    Sessions enable:
    - Tracking agent work periods
    - Handoff notes between sessions
    - Context for resuming work

    Attributes:
        id: Unique identifier (UUID)
        agent_id: Identifier for the AI agent
        started_at: When the session started
        ended_at: When the session ended (None if active)
        summary: Summary of work accomplished
        handoff_notes: Notes for the next session
        context: Optional context/purpose for this session
        created_at: When created
        updated_at: When last modified
    """

    agent_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    summary: Optional[str] = None
    handoff_notes: Optional[str] = None
    context: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        now = datetime.utcnow()
        if self.started_at is None:
            self.started_at = now
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        return self.ended_at is None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get session duration in seconds."""
        if not self.started_at:
            return None
        end = self.ended_at or datetime.utcnow()
        return (end - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "summary": self.summary,
            "handoff_notes": self.handoff_notes,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create Session from dictionary (e.g., database row)."""
        # Parse datetime fields
        for field_name in ("started_at", "ended_at", "created_at", "updated_at"):
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name].replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            agent_id=data.get("agent_id", "unknown"),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            summary=data.get("summary"),
            handoff_notes=data.get("handoff_notes"),
            context=data.get("context"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


# Valid activity types
ACTIVITY_TYPES = (
    "claim_work",     # Claimed a work item
    "release_work",   # Released a work item
    "create_task",    # Created a task
    "update_task",    # Updated a task
    "complete_task",  # Completed a task
    "create_devlog",  # Created a devlog
    "other",          # Other activity
)

# Valid target types for activities
TARGET_TYPES = (
    "task",
    "issue",
    "pr",
    "devlog",
    "qa",
    "other",
)


@dataclass
class Activity:
    """
    An activity log entry within a session.

    Activities track specific actions like claiming work,
    creating tasks, or writing devlogs.

    Attributes:
        id: Unique identifier (UUID)
        agent_id: Agent that performed the activity
        session_id: Associated session (optional)
        activity_type: Type of activity
        target_type: Type of target (task, issue, pr, devlog)
        target_id: ID of the target
        repo: Repository (for issue/PR activities)
        notes: Optional notes about the activity
        created_at: When the activity occurred
    """

    agent_id: str
    activity_type: str
    id: str = field(default_factory=lambda: str(uuid4()))
    session_id: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    repo: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "activity_type": self.activity_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "repo": self.repo,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Activity":
        """Create Activity from dictionary (e.g., database row)."""
        # Parse datetime fields
        if data.get("created_at") and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            agent_id=data.get("agent_id", "unknown"),
            session_id=data.get("session_id"),
            activity_type=data.get("activity_type", "other"),
            target_type=data.get("target_type"),
            target_id=data.get("target_id"),
            repo=data.get("repo"),
            notes=data.get("notes"),
            created_at=data.get("created_at"),
        )
