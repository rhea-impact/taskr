"""
Integration tests for taskr.

Tests that verify components work together without mocking.
"""

import pytest
import tempfile
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
        assert 'taskr_create' in tool_names
        assert 'taskr_list' in tool_names

        # GitHub tools
        assert 'github_auth_check' in tool_names
        assert 'github_project_create' in tool_names

    def test_server_tool_count(self):
        """Test server has reasonable number of tools."""
        from taskr_mcp.server import create_server

        mcp = create_server()
        tool_count = len(mcp._tools)

        assert tool_count >= 15, f'Expected at least 15 tools, got {tool_count}'


class TestSQLiteAdapter:
    """Test SQLite adapter basics."""

    @pytest.mark.asyncio
    async def test_adapter_connects(self):
        """Test SQLite adapter connects and creates database."""
        from taskr.db.sqlite import SQLiteAdapter

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'test.db'
            adapter = SQLiteAdapter(str(db_path))

            await adapter.connect()
            assert db_path.exists()

            # Test basic query
            result = await adapter.fetchval("SELECT 1")
            assert result == 1

            await adapter.close()

    @pytest.mark.asyncio
    async def test_adapter_crud(self):
        """Test basic CRUD operations."""
        from taskr.db.sqlite import SQLiteAdapter

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'test.db'
            adapter = SQLiteAdapter(str(db_path))
            await adapter.connect()

            # Create table
            await adapter.execute("""
                CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)
            """)

            # Insert
            await adapter.execute("INSERT INTO test (name) VALUES (?)", "hello")

            # Select
            rows = await adapter.fetch("SELECT * FROM test")
            assert len(rows) == 1
            assert rows[0]['name'] == 'hello'

            await adapter.close()


class TestGitHubIntegration:
    """Test GitHub integration."""

    def test_auth_status_structure(self):
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


class TestConfig:
    """Test configuration loading."""

    def test_config_defaults(self):
        """Test config loads with defaults."""
        from taskr.config import TaskrConfig

        config = TaskrConfig()

        assert config.database.type == 'sqlite'
        assert config.identity.agent_id == 'claude-code'

    def test_config_path(self):
        """Test database path is set."""
        from taskr.config import TaskrConfig

        config = TaskrConfig()
        assert config.database.sqlite_path is not None
