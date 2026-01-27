"""
Taskr Core Library

AI-native task management with support for PostgreSQL and SQLite.
"""

__version__ = "0.1.0"

from taskr.config import load_config, TaskrConfig
from taskr.db import get_adapter, DatabaseAdapter

__all__ = [
    "load_config",
    "TaskrConfig",
    "get_adapter",
    "DatabaseAdapter",
]
