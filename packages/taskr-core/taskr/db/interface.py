"""
Abstract database adapter interface.

Supports both PostgreSQL and SQLite with feature detection for graceful degradation.
"""

from abc import ABC, abstractmethod
from typing import Any


class DatabaseAdapter(ABC):
    """
    Abstract base class for database adapters.

    Implementations must support:
    - Basic CRUD operations (execute, fetch, fetchrow, fetchval)
    - Feature detection (supports_fts, supports_vector, supports_jsonb)
    - Text search with graceful degradation
    """

    @abstractmethod
    async def connect(self) -> None:
        """Initialize connection/pool."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection/pool."""
        pass

    @abstractmethod
    async def execute(self, query: str, *args) -> str:
        """
        Execute a query and return status.

        Args:
            query: SQL query with placeholders ($1, $2 for PG; ? for SQLite)
            *args: Query parameters

        Returns:
            Status string (e.g., "INSERT 0 1")
        """
        pass

    @abstractmethod
    async def fetch(self, query: str, *args) -> list[dict]:
        """
        Fetch multiple rows as list of dicts.

        Args:
            query: SQL SELECT query
            *args: Query parameters

        Returns:
            List of row dicts
        """
        pass

    @abstractmethod
    async def fetchrow(self, query: str, *args) -> dict | None:
        """
        Fetch single row as dict.

        Args:
            query: SQL SELECT query
            *args: Query parameters

        Returns:
            Row dict or None if no results
        """
        pass

    @abstractmethod
    async def fetchval(self, query: str, *args) -> Any:
        """
        Fetch single value.

        Args:
            query: SQL SELECT query returning one column
            *args: Query parameters

        Returns:
            The value or None
        """
        pass

    @property
    @abstractmethod
    def supports_fts(self) -> bool:
        """Does this adapter support full-text search (tsvector/tsquery)?"""
        pass

    @property
    @abstractmethod
    def supports_vector(self) -> bool:
        """Does this adapter support vector embeddings (pgvector)?"""
        pass

    @property
    @abstractmethod
    def supports_jsonb(self) -> bool:
        """Does this adapter support JSONB operators?"""
        pass

    @property
    @abstractmethod
    def supports_arrays(self) -> bool:
        """Does this adapter support native array columns?"""
        pass

    @property
    @abstractmethod
    def placeholder_style(self) -> str:
        """
        Return the placeholder style for this adapter.

        Returns:
            "dollar" for PostgreSQL ($1, $2, ...)
            "qmark" for SQLite (?, ?, ...)
        """
        pass

    @abstractmethod
    async def search_text(
        self,
        table: str,
        query: str,
        columns: list[str],
        limit: int = 20,
        where_clause: str | None = None,
    ) -> list[dict]:
        """
        Full-text search with graceful degradation.

        On PostgreSQL: Uses tsvector/tsquery with ranking
        On SQLite: Falls back to LIKE wildcards

        Args:
            table: Table name to search
            query: Search query string
            columns: Columns to search in
            limit: Maximum results
            where_clause: Additional WHERE conditions (without WHERE keyword)

        Returns:
            List of matching rows, ordered by relevance
        """
        pass

    def format_query(self, query: str) -> str:
        """
        Convert query placeholders to the adapter's style.

        Input uses $1, $2 style (PostgreSQL).
        For SQLite, converts to ? style.
        """
        if self.placeholder_style == "dollar":
            return query

        # Convert $1, $2, etc. to ? for SQLite
        import re
        return re.sub(r'\$\d+', '?', query)

    async def ensure_schema(self) -> None:
        """
        Create schema if needed (PostgreSQL only).
        Default implementation does nothing.
        """
        pass
