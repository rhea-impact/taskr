"""
Plugin interface for Taskr.

Plugins implement this interface to extend Taskr with additional tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


@dataclass
class PluginInfo:
    """
    Plugin metadata.

    Attributes:
        name: Unique plugin name (used in config)
        version: Semantic version string
        description: Human-readable description
        requires_postgres: True if plugin needs PostgreSQL-only features
        author: Plugin author
    """
    name: str
    version: str
    description: str
    requires_postgres: bool = False
    author: Optional[str] = None


class TaskrPlugin(ABC):
    """
    Base class for Taskr plugins.

    Plugins provide:
    - Additional MCP tools
    - Database migrations (optional)
    - Startup/shutdown hooks (optional)

    Example:
        class MyPlugin(TaskrPlugin):
            @property
            def info(self) -> PluginInfo:
                return PluginInfo(
                    name="my-plugin",
                    version="1.0.0",
                    description="My custom plugin",
                )

            def register_tools(self, mcp: FastMCP) -> None:
                @mcp.tool()
                async def my_tool() -> dict:
                    return {"message": "Hello from plugin!"}
    """

    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """
        Return plugin metadata.

        Returns:
            PluginInfo with name, version, description
        """
        pass

    @abstractmethod
    def register_tools(self, mcp: "FastMCP") -> None:
        """
        Register MCP tools with the server.

        Args:
            mcp: FastMCP server instance to register tools with
        """
        pass

    def get_migrations(self) -> List[str]:
        """
        Return list of migration file paths.

        Override to provide plugin-specific database migrations.
        Migrations should be in SQL format.

        Returns:
            List of absolute paths to migration files
        """
        return []

    def on_startup(self) -> None:
        """
        Called when plugin is loaded.

        Override to perform initialization.
        """
        pass

    def on_shutdown(self) -> None:
        """
        Called when server shuts down.

        Override to perform cleanup.
        """
        pass

    def get_config(self, key: str, default=None):
        """
        Get plugin-specific configuration.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value
        """
        from taskr.config import get_config
        config = get_config()
        plugin_settings = config.plugins.settings.get(self.info.name, {})
        return plugin_settings.get(key, default)
