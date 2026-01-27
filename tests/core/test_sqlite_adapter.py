"""
Tests for SQLite database adapter.
"""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
async def sqlite_adapter():
    """Create a temporary SQLite adapter for testing."""
    from taskr.db.sqlite import SQLiteAdapter

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        adapter = SQLiteAdapter(str(db_path))
        await adapter.connect()

        # Create test table
        await adapter.execute("""
            CREATE TABLE test_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER,
                tags TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')),
                deleted_at TEXT
            )
        """)

        yield adapter

        await adapter.close()


@pytest.mark.asyncio
async def test_sqlite_connect(sqlite_adapter):
    """Test SQLite connection."""
    result = await sqlite_adapter.fetchval("SELECT 1")
    assert result == 1


@pytest.mark.asyncio
async def test_sqlite_execute_insert(sqlite_adapter):
    """Test inserting data."""
    result = await sqlite_adapter.execute(
        "INSERT INTO test_items (id, name, value) VALUES (?, ?, ?)",
        "test-1", "Test Item", 42,
    )

    assert "INSERT" in result


@pytest.mark.asyncio
async def test_sqlite_fetch(sqlite_adapter):
    """Test fetching multiple rows."""
    # Insert test data
    await sqlite_adapter.execute(
        "INSERT INTO test_items (id, name, value) VALUES (?, ?, ?)",
        "item-1", "Item 1", 10,
    )
    await sqlite_adapter.execute(
        "INSERT INTO test_items (id, name, value) VALUES (?, ?, ?)",
        "item-2", "Item 2", 20,
    )

    rows = await sqlite_adapter.fetch("SELECT * FROM test_items ORDER BY name")

    assert len(rows) == 2
    assert rows[0]["name"] == "Item 1"
    assert rows[1]["name"] == "Item 2"


@pytest.mark.asyncio
async def test_sqlite_fetchrow(sqlite_adapter):
    """Test fetching single row."""
    await sqlite_adapter.execute(
        "INSERT INTO test_items (id, name, value) VALUES (?, ?, ?)",
        "single", "Single Item", 100,
    )

    row = await sqlite_adapter.fetchrow(
        "SELECT * FROM test_items WHERE id = ?", "single"
    )

    assert row is not None
    assert row["name"] == "Single Item"
    assert row["value"] == 100


@pytest.mark.asyncio
async def test_sqlite_fetchrow_not_found(sqlite_adapter):
    """Test fetchrow returns None when not found."""
    row = await sqlite_adapter.fetchrow(
        "SELECT * FROM test_items WHERE id = ?", "nonexistent"
    )

    assert row is None


@pytest.mark.asyncio
async def test_sqlite_search_text(sqlite_adapter):
    """Test text search with LIKE fallback."""
    # Insert test data
    await sqlite_adapter.execute(
        "INSERT INTO test_items (id, name, value) VALUES (?, ?, ?)",
        "auth-1", "Authentication handler", 1,
    )
    await sqlite_adapter.execute(
        "INSERT INTO test_items (id, name, value) VALUES (?, ?, ?)",
        "auth-2", "Authorization middleware", 2,
    )
    await sqlite_adapter.execute(
        "INSERT INTO test_items (id, name, value) VALUES (?, ?, ?)",
        "other", "Database connection", 3,
    )

    results = await sqlite_adapter.search_text(
        table="test_items",
        query="auth",
        columns=["name"],
        limit=10,
    )

    assert len(results) == 2
    assert all("auth" in r["name"].lower() for r in results)


@pytest.mark.asyncio
async def test_sqlite_features(sqlite_adapter):
    """Test feature detection."""
    assert sqlite_adapter.supports_fts is False
    assert sqlite_adapter.supports_vector is False
    assert sqlite_adapter.supports_jsonb is False
    assert sqlite_adapter.supports_arrays is False
    assert sqlite_adapter.placeholder_style == "qmark"


@pytest.mark.asyncio
async def test_sqlite_format_query(sqlite_adapter):
    """Test query placeholder conversion."""
    # PostgreSQL style
    pg_query = "SELECT * FROM items WHERE id = $1 AND name = $2"

    # Should convert to SQLite style
    sqlite_query = sqlite_adapter.format_query(pg_query)

    assert "$1" not in sqlite_query
    assert "$2" not in sqlite_query
    assert "?" in sqlite_query
