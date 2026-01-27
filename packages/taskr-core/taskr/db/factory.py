"""
Database adapter factory.

Creates the appropriate adapter based on configuration.
"""

import logging

from taskr.db.interface import DatabaseAdapter

logger = logging.getLogger(__name__)

# Global adapter instance (singleton pattern)
_adapter: DatabaseAdapter | None = None


def get_adapter(config=None) -> DatabaseAdapter:
    """
    Get or create the database adapter based on configuration.

    Uses singleton pattern - returns same adapter instance on subsequent calls.

    Args:
        config: Optional TaskrConfig. If not provided, loads from default location.

    Returns:
        DatabaseAdapter instance (PostgresAdapter or SQLiteAdapter)

    Raises:
        ValueError: If database configuration is invalid
    """
    global _adapter

    if _adapter is not None:
        return _adapter

    # Load config if not provided
    if config is None:
        from taskr.config import load_config
        config = load_config()

    db_type = config.database.type.lower()

    if db_type == "postgres" or db_type == "postgresql":
        from taskr.db.postgres import PostgresAdapter

        url = config.database.postgres_url
        if not url:
            raise ValueError(
                "PostgreSQL URL not configured. "
                "Set database.postgres.url in config or TASKR_DATABASE_URL env var."
            )

        _adapter = PostgresAdapter(url)
        logger.info("Using PostgreSQL adapter")

    elif db_type == "sqlite":
        from taskr.db.sqlite import SQLiteAdapter

        path = config.database.sqlite_path
        _adapter = SQLiteAdapter(path)
        logger.info(f"Using SQLite adapter: {path}")

    else:
        raise ValueError(
            f"Unknown database type: {db_type}. "
            "Use 'postgres' or 'sqlite'."
        )

    return _adapter


async def init_adapter(config=None) -> DatabaseAdapter:
    """
    Initialize the database adapter and connect.

    Convenience function that gets the adapter and calls connect().

    Args:
        config: Optional TaskrConfig

    Returns:
        Connected DatabaseAdapter instance
    """
    adapter = get_adapter(config)
    await adapter.connect()
    return adapter


async def close_adapter() -> None:
    """Close the global adapter connection."""
    global _adapter

    if _adapter is not None:
        await _adapter.close()
        _adapter = None


def reset_adapter() -> None:
    """
    Reset the global adapter instance.

    Useful for testing or when configuration changes.
    """
    global _adapter
    _adapter = None
