"""
Devlog model for Taskr.

Devlogs are development log entries that serve as AI memory -
capturing decisions, patterns, bugfixes, and other knowledge.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4


# Valid devlog categories
DEVLOG_CATEGORIES = (
    "feature",     # New feature implementation
    "bugfix",      # Bug fix
    "deployment",  # Deployment notes
    "config",      # Configuration changes
    "incident",    # Incident report
    "refactor",    # Code refactoring
    "research",    # Research findings
    "decision",    # Architectural/design decision
    "migration",   # Data/schema migration
    "note",        # General note
)


@dataclass
class Devlog:
    """
    A development log entry.

    Devlogs capture institutional knowledge for AI agents:
    - Decisions and their rationale
    - Bug fixes and root causes
    - Implementation patterns
    - Research findings

    Attributes:
        id: Unique identifier (UUID)
        category: Type of entry (feature, bugfix, decision, etc.)
        title: Short summary (1 line)
        content: Full markdown content
        author: Human author
        agent_id: AI agent that created/modified the entry
        service_name: Related service/project
        tags: List of tags for filtering
        metadata: Additional structured data
        created_at: When created
        updated_at: When last modified
        deleted_at: Soft delete timestamp
    """

    title: str
    content: str
    category: str = "note"
    id: str = field(default_factory=lambda: str(uuid4()))
    author: Optional[str] = None
    agent_id: str = "claude-code"
    service_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = self.created_at

        # Validate category
        if self.category not in DEVLOG_CATEGORIES:
            raise ValueError(
                f"Invalid category '{self.category}'. "
                f"Must be one of: {', '.join(DEVLOG_CATEGORIES)}"
            )

    @property
    def is_deleted(self) -> bool:
        """Check if entry is soft-deleted."""
        return self.deleted_at is not None

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "agent_id": self.agent_id,
            "service_name": self.service_name,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Devlog":
        """Create Devlog from dictionary (e.g., database row)."""
        import json

        # Parse datetime fields
        for field_name in ("created_at", "updated_at", "deleted_at"):
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name].replace("Z", "+00:00"))

        # Handle tags (may be JSON string in SQLite)
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = json.loads(tags)

        # Handle metadata (may be JSON string in SQLite)
        metadata = data.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return cls(
            id=data.get("id"),
            category=data.get("category", "note"),
            title=data.get("title", ""),
            content=data.get("content", ""),
            author=data.get("author"),
            agent_id=data.get("agent_id", "claude-code"),
            service_name=data.get("service_name"),
            tags=tags,
            metadata=metadata,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            deleted_at=data.get("deleted_at"),
        )

    def summary(self, max_length: int = 100) -> str:
        """Get a short summary of the content."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length - 3] + "..."
