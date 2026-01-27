"""
Skillflow data models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class SkillflowInput:
    """Input parameter definition for a skillflow."""
    name: str
    type: str  # string, number, boolean, array, object
    required: bool = True
    description: str = ""
    default: Any = None


@dataclass
class SkillflowOutput:
    """Output definition for a skillflow."""
    name: str
    type: str
    description: str = ""


@dataclass
class SkillflowStep:
    """A step in a skillflow workflow."""
    order: int
    action: str  # Tool name or description
    description: str
    why: str  # Rationale for this step
    inputs: dict[str, Any] = field(default_factory=dict)
    on_error: str = "fail"  # fail, skip, retry


@dataclass
class Skillflow:
    """
    A tracked, discoverable workflow definition.

    Skillflows capture reusable patterns that agents can execute.
    """
    name: str  # Unique kebab-case slug
    title: str
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str | None = None
    status: str = "draft"  # draft, active, deprecated
    version: int = 1
    inputs: list[dict[str, Any]] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    preconditions: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    author: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    # Computed metrics (from view)
    execution_count: int = 0
    success_rate: float = 0.0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "version": self.version,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "preconditions": self.preconditions,
            "steps": self.steps,
            "tags": self.tags,
            "author": self.author,
            "execution_count": self.execution_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Skillflow":
        import json

        for field_name in ("created_at", "updated_at", "deleted_at"):
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name].replace("Z", "+00:00"))

        # Handle JSON fields
        for field_name in ("inputs", "outputs", "preconditions", "steps", "tags"):
            if isinstance(data.get(field_name), str):
                data[field_name] = json.loads(data[field_name])

        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            status=data.get("status", "draft"),
            version=data.get("version", 1),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            preconditions=data.get("preconditions", []),
            steps=data.get("steps", []),
            tags=data.get("tags", []),
            author=data.get("author"),
            execution_count=data.get("execution_count", 0),
            success_rate=float(data.get("success_rate", 0)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            deleted_at=data.get("deleted_at"),
        )


@dataclass
class SkillflowExecution:
    """Record of a skillflow execution."""
    skillflow_id: str
    skillflow_name: str
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str | None = None
    status: str = "pending"  # pending, running, completed, failed, cancelled
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    step_results: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error_message: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "skillflow_id": self.skillflow_id,
            "skillflow_name": self.skillflow_name,
            "agent_id": self.agent_id,
            "status": self.status,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "step_results": self.step_results,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillflowExecution":
        import json

        for field_name in ("started_at", "completed_at"):
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name].replace("Z", "+00:00"))

        for field_name in ("inputs", "outputs", "step_results"):
            if isinstance(data.get(field_name), str):
                data[field_name] = json.loads(data[field_name])

        return cls(
            id=data.get("id"),
            skillflow_id=data.get("skillflow_id", ""),
            skillflow_name=data.get("skillflow_name", ""),
            agent_id=data.get("agent_id"),
            status=data.get("status", "pending"),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            step_results=data.get("step_results", []),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            duration_ms=data.get("duration_ms"),
            error_message=data.get("error_message"),
        )
