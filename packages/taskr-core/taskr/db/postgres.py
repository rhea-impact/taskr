"""
PostgreSQL database adapter using asyncpg.

Supports full PostgreSQL features including:
- Full-text search (tsvector/tsquery)
- JSONB operators
- Native arrays
- pgvector (if extension installed)
"""

import asyncio
import logging
from typing import Optional, List, Any

from taskr.db.interface import DatabaseAdapter

logger = logging.getLogger(__name__)

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
    asyncpg = None


class PostgresAdapter(DatabaseAdapter):
    """
    PostgreSQL adapter with full feature support.

    Uses asyncpg for async database operations with connection pooling.
    """

    def __init__(self, connection_url: str):
        """
        Initialize PostgreSQL adapter.

        Args:
            connection_url: PostgreSQL connection URL
                           (e.g., postgresql://user:pass@host:5432/dbname)
        """
        if not HAS_ASYNCPG:
            raise RuntimeError(
                "asyncpg not installed. Run: pip install taskr-core[postgres]"
            )

        self.url = connection_url
        self._pool: Optional[asyncpg.Pool] = None
        self._pool_loop: Optional[asyncio.AbstractEventLoop] = None
        self._has_pgvector: Optional[bool] = None

    async def connect(self) -> None:
        """Initialize connection pool."""
        current_loop = asyncio.get_running_loop()

        # If pool exists but was created on a different event loop, close it
        if self._pool is not None and self._pool_loop is not current_loop:
            try:
                self._pool.terminate()
            except Exception as e:
                logger.warning(f"Failed to terminate old pool: {e}")
            self._pool = None
            self._pool_loop = None

        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.url,
                min_size=1,
                max_size=5,
                statement_cache_size=0,  # Required for pgbouncer compatibility
            )
            self._pool_loop = current_loop
            logger.info("PostgreSQL connection pool initialized")

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool is not None:
            try:
                await self._pool.close()
            except Exception as e:
                logger.warning(f"Graceful pool close failed, terminating: {e}")
                self._pool.terminate()
            self._pool = None
            self._pool_loop = None
            logger.info("PostgreSQL connection pool closed")

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create connection pool."""
        if self._pool is None:
            await self.connect()
        return self._pool

    async def execute(self, query: str, *args) -> str:
        """Execute query and return status."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> List[dict]:
        """Fetch rows as list of dicts."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args) -> Optional[dict]:
        """Fetch single row as dict."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetchval(self, query: str, *args) -> Any:
        """Fetch single value."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    @property
    def supports_fts(self) -> bool:
        """PostgreSQL supports full-text search."""
        return True

    @property
    def supports_vector(self) -> bool:
        """Check if pgvector extension is available."""
        # Cache the result after first check
        if self._has_pgvector is None:
            # Will be checked on first use
            return False
        return self._has_pgvector

    async def check_pgvector(self) -> bool:
        """Check if pgvector extension is installed."""
        if self._has_pgvector is None:
            try:
                result = await self.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
                self._has_pgvector = bool(result)
            except Exception:
                self._has_pgvector = False
        return self._has_pgvector

    @property
    def supports_jsonb(self) -> bool:
        """PostgreSQL supports JSONB operators."""
        return True

    @property
    def supports_arrays(self) -> bool:
        """PostgreSQL supports native arrays."""
        return True

    @property
    def placeholder_style(self) -> str:
        """PostgreSQL uses $1, $2 style placeholders."""
        return "dollar"

    async def search_text(
        self,
        table: str,
        query: str,
        columns: List[str],
        limit: int = 20,
        where_clause: Optional[str] = None,
    ) -> List[dict]:
        """
        Full-text search using PostgreSQL tsvector/tsquery.

        Assumes table has a 'search_vector' column of type TSVECTOR.
        Falls back to ILIKE if search_vector doesn't exist.
        """
        # Build base WHERE clause
        where_parts = ["deleted_at IS NULL"]
        if where_clause:
            where_parts.append(f"({where_clause})")

        # Try FTS first (requires search_vector column)
        try:
            fts_where = " AND ".join(where_parts + ["search_vector @@ plainto_tsquery('english', $1)"])
            sql = f"""
                SELECT *, ts_rank(search_vector, plainto_tsquery('english', $1)) as _rank
                FROM {table}
                WHERE {fts_where}
                ORDER BY _rank DESC
                LIMIT $2
            """
            return await self.fetch(sql, query, limit)
        except Exception as e:
            logger.debug(f"FTS failed, falling back to ILIKE: {e}")

        # Fallback to ILIKE search
        like_conditions = " OR ".join([f"{col} ILIKE $1" for col in columns])
        where_parts.append(f"({like_conditions})")
        ilike_where = " AND ".join(where_parts)

        sql = f"""
            SELECT *
            FROM {table}
            WHERE {ilike_where}
            ORDER BY created_at DESC
            LIMIT $2
        """
        return await self.fetch(sql, f"%{query}%", limit)

    async def ensure_schema(self) -> None:
        """Create taskr schema if it doesn't exist."""
        await self.execute("CREATE SCHEMA IF NOT EXISTS taskr")
        logger.info("Ensured taskr schema exists")
