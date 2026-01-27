"""
Database abstraction layer supporting PostgreSQL and SQLite.
"""

from taskr.db.interface import DatabaseAdapter
from taskr.db.factory import get_adapter

__all__ = [
    "DatabaseAdapter",
    "get_adapter",
]
