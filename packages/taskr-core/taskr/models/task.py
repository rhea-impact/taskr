"""
Task model for Taskr.

Tasks are the core work items that can be created, assigned, and tracked.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import uuid4


@dataclass
class Task:
    """
    A task or work item.

    Attributes:
        id: Unique identifier (UUID)
        title: Task title/summary
        description: Detailed description
        status: Current status (open, in_progress, done, cancelled)
        priority: Priority level (low, medium, high, critical)
        assignee: Username of assigned person
        tags: List of tags for categorization
        created_by: Who created the task
        created_at: When the task was created
        updated_at: When last modified
        due_at: Optional due date
        completed_at: When the task was completed
        deleted_at: Soft delete timestamp
    """

    title: str
    id: str = field(default_factory=lambda: str(uuid4()))
    description: Optional[str] = None
    status: str = "open"  # open, in_progress, done, cancelled
    priority: str = "medium"  # low, medium, high, critical
    assignee: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = self.created_at

    @property
    def is_open(self) -> bool:
        """Check if task is still open."""
        return self.status in ("open", "in_progress")

    @property
    def is_complete(self) -> bool:
        """Check if task is done."""
        return self.status == "done"

    @property
    def is_deleted(self) -> bool:
        """Check if task is soft-deleted."""
        return self.deleted_at is not None

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assignee": self.assignee,
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create Task from dictionary (e.g., database row)."""
        # Parse datetime fields
        for field_name in ("created_at", "updated_at", "due_at", "completed_at", "deleted_at"):
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name].replace("Z", "+00:00"))

        # Handle tags (may be JSON string in SQLite)
        if isinstance(data.get("tags"), str):
            import json
            data["tags"] = json.loads(data["tags"])

        return cls(
            id=data.get("id"),
            title=data.get("title", ""),
            description=data.get("description"),
            status=data.get("status", "open"),
            priority=data.get("priority", "medium"),
            assignee=data.get("assignee"),
            tags=data.get("tags", []),
            created_by=data.get("created_by"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            due_at=data.get("due_at"),
            completed_at=data.get("completed_at"),
            deleted_at=data.get("deleted_at"),
        )


# Valid status values
TASK_STATUSES = ("open", "in_progress", "done", "cancelled")

# Valid priority values
TASK_PRIORITIES = ("low", "medium", "high", "critical")
