"""
Plugin discovery and loading for Taskr MCP server.

Plugins are discovered via Python entry points in the 'taskr.plugins' group.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

from taskr.plugins import TaskrPlugin

logger = logging.getLogger(__name__)


def discover_plugins() -> list[TaskrPlugin]:
    """
    Discover installed plugins via entry points.

    Plugins register themselves in pyproject.toml:

        [project.entry-points."taskr.plugins"]
        my_plugin = "my_package.plugin:MyPlugin"

    Returns:
        List of TaskrPlugin instances
    """
    plugins = []

    try:
        # Python 3.10+ has importlib.metadata in stdlib
        from importlib.metadata import entry_points
    except ImportError:
        # Fallback for older Python
        from importlib_metadata import entry_points

    # Get entry points for taskr.plugins group
    try:
        # Python 3.10+ API
        eps = entry_points(group="taskr.plugins")
    except TypeError:
        # Python 3.9 API
        eps = entry_points().get("taskr.plugins", [])

    for ep in eps:
        try:
            plugin_class = ep.load()
            plugin = plugin_class()

            if not isinstance(plugin, TaskrPlugin):
                logger.warning(
                    f"Plugin {ep.name} does not implement TaskrPlugin interface, skipping"
                )
                continue

            plugins.append(plugin)
            logger.debug(f"Discovered plugin: {plugin.info.name} v{plugin.info.version}")

        except Exception as e:
            logger.warning(f"Failed to load plugin {ep.name}: {e}")

    return plugins


def load_plugins(mcp: "FastMCP") -> list[TaskrPlugin]:
    """
    Load and register enabled plugins.

    Checks plugin requirements (e.g., requires_postgres) against
    current database configuration.

    Args:
        mcp: FastMCP server instance

    Returns:
        List of loaded plugins
    """
    from taskr.config import get_config
    from taskr.db import get_adapter

    config = get_config()
    adapter = get_adapter()
    enabled_plugins = config.plugins.enabled

    if not enabled_plugins:
        logger.info("No plugins enabled")
        return []

    plugins = discover_plugins()
    loaded = []

    for plugin in plugins:
        # Check if plugin is enabled
        if plugin.info.name not in enabled_plugins:
            logger.debug(f"Plugin {plugin.info.name} not enabled, skipping")
            continue

        # Check database requirements
        if plugin.info.requires_postgres and not adapter.supports_fts:
            logger.warning(
                f"Plugin {plugin.info.name} requires PostgreSQL. "
                f"Skipping because SQLite is configured."
            )
            continue

        try:
            # Register tools
            plugin.register_tools(mcp)

            # Call startup hook
            plugin.on_startup()

            loaded.append(plugin)
            logger.info(
                f"Loaded plugin: {plugin.info.name} v{plugin.info.version}"
            )

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin.info.name}: {e}")

    return loaded


async def run_plugin_migrations(plugins: list[TaskrPlugin]) -> None:
    """
    Run migrations for loaded plugins.

    Args:
        plugins: List of loaded plugins
    """
    from pathlib import Path

    from taskr.db import get_adapter

    adapter = get_adapter()

    for plugin in plugins:
        migrations = plugin.get_migrations()

        for migration_path in migrations:
            path = Path(migration_path)

            if not path.exists():
                logger.warning(
                    f"Plugin {plugin.info.name} migration not found: {migration_path}"
                )
                continue

            try:
                sql = path.read_text()

                # Execute migration
                for statement in sql.split(";"):
                    statement = statement.strip()
                    if statement and not statement.startswith("--"):
                        await adapter.execute(statement)

                logger.info(
                    f"Applied plugin migration: {plugin.info.name}/{path.name}"
                )

            except Exception as e:
                logger.error(
                    f"Plugin {plugin.info.name} migration failed ({path.name}): {e}"
                )
                raise


def shutdown_plugins(plugins: list[TaskrPlugin]) -> None:
    """
    Call shutdown hooks for loaded plugins.

    Args:
        plugins: List of loaded plugins
    """
    for plugin in plugins:
        try:
            plugin.on_shutdown()
            logger.debug(f"Shutdown plugin: {plugin.info.name}")
        except Exception as e:
            logger.error(f"Plugin {plugin.info.name} shutdown error: {e}")
