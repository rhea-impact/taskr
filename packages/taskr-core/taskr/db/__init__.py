"""
Database abstraction layer supporting PostgreSQL and SQLite.
"""

from taskr.db.factory import get_adapter
from taskr.db.interface import DatabaseAdapter

__all__ = [
    "DatabaseAdapter",
    "get_adapter",
]
