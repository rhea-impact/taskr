"""
Pytest configuration and fixtures for taskr tests.
"""

import pytest
import sys
from pathlib import Path

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

# Add packages to path for testing
packages_dir = Path(__file__).parent.parent / "packages"
sys.path.insert(0, str(packages_dir / "taskr-core"))
sys.path.insert(0, str(packages_dir / "taskr-mcp"))


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".taskr"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "title": "Test Task",
        "description": "A test task description",
        "status": "open",
        "priority": "medium",
        "tags": ["test", "sample"],
    }


@pytest.fixture
def sample_devlog_data():
    """Sample devlog data for testing."""
    return {
        "category": "decision",
        "title": "Test Decision",
        "content": "We decided to do X because of Y.",
        "tags": ["architecture", "test"],
        "service_name": "test-service",
    }
