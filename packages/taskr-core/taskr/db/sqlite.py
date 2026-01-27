"""
SQLite database adapter using aiosqlite.

Provides graceful degradation for features not available in SQLite:
- Full-text search: Falls back to LIKE wildcards
- JSONB: Uses JSON1 extension (limited operators)
- Arrays: Stored as JSON arrays
- Vector embeddings: Not supported
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Any

from taskr.db.interface import DatabaseAdapter

logger = logging.getLogger(__name__)

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False
    aiosqlite = None


class SQLiteAdapter(DatabaseAdapter):
    """
    SQLite adapter with graceful feature degradation.

    Uses aiosqlite for async database operations.
    Automatically creates the database file and parent directories.
    """

    def __init__(self, db_path: str = "~/.taskr/taskr.db"):
        """
        Initialize SQLite adapter.

        Args:
            db_path: Path to SQLite database file.
                    Supports ~ expansion for home directory.
        """
        if not HAS_AIOSQLITE:
            raise RuntimeError(
                "aiosqlite not installed. Run: pip install taskr-core"
            )

        self.db_path = Path(db_path).expanduser()
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Initialize database connection and create file if needed."""
        if self._conn is not None:
            return

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect (creates file if doesn't exist)
        self._conn = await aiosqlite.connect(str(self.db_path))

        # Enable foreign keys and JSON1 extension
        await self._conn.execute("PRAGMA foreign_keys = ON")

        # Use WAL mode for better concurrent access
        await self._conn.execute("PRAGMA journal_mode = WAL")

        # Row factory to return dicts
        self._conn.row_factory = aiosqlite.Row

        logger.info(f"SQLite database connected: {self.db_path}")

    async def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.info("SQLite connection closed")

    async def _get_conn(self) -> aiosqlite.Connection:
        """Get or create connection."""
        if self._conn is None:
            await self.connect()
        return self._conn

    async def execute(self, query: str, *args) -> str:
        """Execute query and return status."""
        conn = await self._get_conn()
        query = self.format_query(query)

        cursor = await conn.execute(query, args)
        await conn.commit()

        # Return a status string similar to PostgreSQL
        if query.strip().upper().startswith("INSERT"):
            return f"INSERT 0 {cursor.rowcount}"
        elif query.strip().upper().startswith("UPDATE"):
            return f"UPDATE {cursor.rowcount}"
        elif query.strip().upper().startswith("DELETE"):
            return f"DELETE {cursor.rowcount}"
        return "OK"

    async def fetch(self, query: str, *args) -> List[dict]:
        """Fetch rows as list of dicts."""
        conn = await self._get_conn()
        query = self.format_query(query)

        cursor = await conn.execute(query, args)
        rows = await cursor.fetchall()

        # Convert Row objects to dicts
        return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args) -> Optional[dict]:
        """Fetch single row as dict."""
        conn = await self._get_conn()
        query = self.format_query(query)

        cursor = await conn.execute(query, args)
        row = await cursor.fetchone()

        return dict(row) if row else None

    async def fetchval(self, query: str, *args) -> Any:
        """Fetch single value."""
        conn = await self._get_conn()
        query = self.format_query(query)

        cursor = await conn.execute(query, args)
        row = await cursor.fetchone()

        if row:
            # Return first column value
            return row[0]
        return None

    @property
    def supports_fts(self) -> bool:
        """SQLite doesn't support PostgreSQL-style FTS."""
        return False

    @property
    def supports_vector(self) -> bool:
        """SQLite doesn't support vector embeddings."""
        return False

    @property
    def supports_jsonb(self) -> bool:
        """SQLite has limited JSON support via JSON1 extension."""
        return False

    @property
    def supports_arrays(self) -> bool:
        """SQLite doesn't support native arrays (use JSON)."""
        return False

    @property
    def placeholder_style(self) -> str:
        """SQLite uses ? style placeholders."""
        return "qmark"

    async def search_text(
        self,
        table: str,
        query: str,
        columns: List[str],
        limit: int = 20,
        where_clause: Optional[str] = None,
    ) -> List[dict]:
        """
        Text search using LIKE wildcards.

        This is a graceful degradation from PostgreSQL's full-text search.
        Results are ordered by created_at (no relevance ranking).
        """
        # Build LIKE conditions for each column
        like_conditions = " OR ".join([f"{col} LIKE ?" for col in columns])
        like_pattern = f"%{query}%"
        params = [like_pattern] * len(columns)

        # Build WHERE clause
        where_parts = [f"({like_conditions})", "deleted_at IS NULL"]
        if where_clause:
            # Convert PostgreSQL placeholders in where_clause
            where_clause = self.format_query(where_clause)
            where_parts.append(f"({where_clause})")

        where_sql = " AND ".join(where_parts)

        sql = f"""
            SELECT *
            FROM {table}
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)

        return await self.fetch(sql, *params)


# Utility functions for SQLite-specific operations

def json_dumps(value: Any) -> str:
    """Serialize Python value to JSON string for SQLite storage."""
    return json.dumps(value)


def json_loads(value: str) -> Any:
    """Deserialize JSON string from SQLite to Python value."""
    if value is None:
        return None
    return json.loads(value)


def list_to_json(items: List[str]) -> str:
    """Convert Python list to JSON string for SQLite storage."""
    return json.dumps(items or [])


def json_to_list(value: str) -> List[str]:
    """Convert JSON string from SQLite to Python list."""
    if value is None:
        return []
    return json.loads(value)
