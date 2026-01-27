"""
Taskr Core Library

AI-native task management with support for PostgreSQL and SQLite.
"""

__version__ = "0.1.0"

from taskr.config import TaskrConfig, load_config
from taskr.db import DatabaseAdapter, get_adapter

__all__ = [
    "load_config",
    "TaskrConfig",
    "get_adapter",
    "DatabaseAdapter",
]
