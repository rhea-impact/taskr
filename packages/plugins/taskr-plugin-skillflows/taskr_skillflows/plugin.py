"""
Skillflows Plugin for Taskr.

Provides tracked, discoverable workflows that AI agents can:
- Create and define
- Execute with tracking
- Search and discover
- Learn from execution history
"""

from pathlib import Path
from typing import TYPE_CHECKING, List

from taskr.plugins import TaskrPlugin, PluginInfo

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class SkillflowsPlugin(TaskrPlugin):
    """
    Skillflows plugin for tracked workflow definitions.

    Requires PostgreSQL for full-text search on workflow definitions.
    """

    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="skillflows",
            version="0.1.0",
            description="Tracked, discoverable workflows for AI agents",
            requires_postgres=True,  # Needs FTS for search
            author="Rhea Impact",
        )

    def register_tools(self, mcp: "FastMCP") -> None:
        """Register skillflow tools with the MCP server."""
        from taskr_skillflows import tools
        tools.register(mcp, self)

    def get_migrations(self) -> List[str]:
        """Return migration files for skillflows tables."""
        migrations_dir = Path(__file__).parent / "migrations"
        if migrations_dir.exists():
            return [str(f) for f in sorted(migrations_dir.glob("*.sql"))]
        return []
