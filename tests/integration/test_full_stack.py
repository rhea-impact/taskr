"""
Integration tests for taskr MCP server.

These tests verify the full stack works together:
- MCP server starts and registers tools
- Tools can be called and return valid results
- Database operations work end-to-end
"""

import pytest
import tempfile
import asyncio
from pathlib import Path

# Check if MCP is available
try:
    from mcp.server.fastmcp import FastMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP module not installed")
class TestMCPServerStartup:
    """Test that the MCP server starts correctly."""

    def test_server_creates(self):
        """Test server creation."""
        from taskr_mcp.server import create_server

        mcp = create_server()
        assert mcp is not None

    def test_server_has_tools(self):
        """Test server registers expected tools."""
        from taskr_mcp.server import create_server

        mcp = create_server()
        tool_names = list(mcp._tools.keys())

        # Core tools
        assert 'taskr_health' in tool_names
        assert 'devlog_add' in tool_names
        assert 'devlog_list' in tool_names
        assert 'devlog_search' in tool_names
        assert 'taskr_create' in tool_names
        assert 'taskr_list' in tool_names

        # GitHub tools
        assert 'github_auth_check' in tool_names
        assert 'github_project_create' in tool_names
        assert 'github_project_items' in tool_names

    def test_server_tool_count(self):
        """Test server has reasonable number of tools."""
        from taskr_mcp.server import create_server

        mcp = create_server()
        tool_count = len(mcp._tools)

        # Should have at least 15 tools
        assert tool_count >= 15, f'Expected at least 15 tools, got {tool_count}'
        print(f'Server has {tool_count} tools registered')


class TestDatabaseIntegration:
    """Test database operations work end-to-end."""

    @pytest.mark.asyncio
    async def test_sqlite_adapter_connects(self):
        """Test SQLite adapter connects and creates database."""
        from taskr.db.sqlite import SQLiteAdapter

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'test.db'
            adapter = SQLiteAdapter(str(db_path))

            # Connect should create the file
            await adapter.connect()

            assert db_path.exists(), 'Database file should be created'

            await adapter.close()

    @pytest.mark.asyncio
    async def test_sqlite_adapter_execute(self):
        """Test SQLite adapter can execute queries."""
        from taskr.db.sqlite import SQLiteAdapter

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'test.db'
            adapter = SQLiteAdapter(str(db_path))
            await adapter.connect()

            # Create a simple table
            await adapter.execute("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
            """)

            # Insert data
            await adapter.execute("INSERT INTO test_table (name) VALUES (?)", "test")

            # Query data
            rows = await adapter.fetch("SELECT * FROM test_table")
            assert len(rows) == 1
            assert rows[0]['name'] == 'test'

            await adapter.close()

    @pytest.mark.asyncio
    async def test_devlog_service_crud(self):
        """Test devlog service create/read operations."""
        from taskr.db.sqlite import SQLiteAdapter
        from taskr.services.devlogs import DevlogService

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'test.db'
            adapter = SQLiteAdapter(str(db_path))
            await adapter.connect()

            # Run migrations to create tables
            await adapter.execute("""
                CREATE TABLE IF NOT EXISTS devlogs (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    tags TEXT,
                    author TEXT,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            service = DevlogService(adapter)

            # Create a devlog
            devlog_id = await service.add(
                category='note',
                title='Integration Test',
                content='Testing the devlog service',
                author='test-runner'
            )

            assert devlog_id is not None

            # List devlogs
            devlogs = await service.list(limit=10)
            assert len(devlogs) >= 1

            # Find our devlog
            found = any(d.get('title') == 'Integration Test' for d in devlogs)
            assert found, 'Created devlog should be in list'

            await adapter.close()

    @pytest.mark.asyncio
    async def test_task_service_crud(self):
        """Test task service create/read operations."""
        from taskr.db.sqlite import SQLiteAdapter
        from taskr.services.tasks import TaskService

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'test.db'
            adapter = SQLiteAdapter(str(db_path))
            await adapter.connect()

            # Run migrations to create tables
            await adapter.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'open',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    assignee TEXT,
                    tags TEXT DEFAULT '[]',
                    created_by TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    deleted_at TEXT
                )
            """)

            service = TaskService(adapter)

            # Create a task
            task = await service.create(
                title='Integration Test Task',
                description='Testing task creation',
                priority='high'
            )

            assert task is not None
            assert task.get('title') == 'Integration Test Task'

            # List tasks
            tasks = await service.list()
            assert len(tasks) >= 1

            await adapter.close()

    @pytest.mark.asyncio
    async def test_session_service_crud(self):
        """Test session service create/read operations."""
        from taskr.db.sqlite import SQLiteAdapter
        from taskr.services.sessions import SessionService

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'test.db'
            adapter = SQLiteAdapter(str(db_path))
            await adapter.connect()

            # Run migrations to create tables
            await adapter.execute("""
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    agent_id TEXT NOT NULL,
                    started_at TEXT DEFAULT (datetime('now')),
                    ended_at TEXT,
                    summary TEXT,
                    handoff_notes TEXT,
                    context TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)

            service = SessionService(adapter)

            # Start a session
            session = await service.start(
                agent_id='test-agent',
                context='Integration test session'
            )

            assert session is not None
            assert session.get('agent_id') == 'test-agent'

            # End the session
            session_id = session.get('id')
            ended = await service.end(
                session_id=session_id,
                handoff_notes='Test completed'
            )

            assert ended is not None

            await adapter.close()


class TestGitHubIntegration:
    """Test GitHub integration."""

    def test_auth_check_returns_status(self):
        """Test github_auth_status returns valid structure."""
        from taskr_mcp.tools.github import github_auth_status

        result = github_auth_status()

        assert 'authenticated' in result
        assert 'method' in result
        assert 'message' in result
        assert isinstance(result['authenticated'], bool)

    def test_gh_available_returns_bool(self):
        """Test gh_available returns boolean."""
        from taskr_mcp.tools.github import gh_available

        result = gh_available()
        assert isinstance(result, bool)


class TestConfigIntegration:
    """Test configuration loading."""

    def test_config_loads_defaults(self):
        """Test config loads with sensible defaults."""
        from taskr.config import TaskrConfig

        config = TaskrConfig()

        assert config.database.type == 'sqlite'
        assert config.identity.agent_id == 'claude-code'

    def test_config_database_path_expands(self):
        """Test database path expands home directory."""
        from taskr.config import TaskrConfig

        config = TaskrConfig()

        # Default path should contain home expansion marker
        assert '~' in config.database.sqlite_path or str(Path.home()) in config.database.sqlite_path
