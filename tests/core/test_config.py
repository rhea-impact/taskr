"""
Tests for taskr configuration.
"""

import pytest
from pathlib import Path
import tempfile
import os


def test_default_config():
    """Test default configuration values."""
    from taskr.config import TaskrConfig, DatabaseConfig, IdentityConfig

    config = TaskrConfig()

    assert config.database.type == "sqlite"
    assert config.database.sqlite_path == "~/.taskr/taskr.db"
    assert config.identity.agent_id == "claude-code"


def test_load_config_without_file():
    """Test loading config when no file exists."""
    from taskr.config import load_config

    # Use a non-existent path
    config = load_config(Path("/nonexistent/config.yaml"))

    assert config.database.type == "sqlite"


def test_load_config_with_env_override(monkeypatch):
    """Test environment variable overrides."""
    from taskr.config import load_config

    monkeypatch.setenv("TASKR_DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("TASKR_AUTHOR", "test-author")
    monkeypatch.setenv("TASKR_AGENT_ID", "test-agent")

    config = load_config(Path("/nonexistent/config.yaml"))

    assert config.database.type == "postgres"
    assert config.database.postgres_url == "postgresql://test:test@localhost/test"
    assert config.identity.author == "test-author"
    assert config.identity.agent_id == "test-agent"


def test_config_to_dict_masks_secrets():
    """Test that to_dict masks sensitive values."""
    from taskr.config import TaskrConfig, DatabaseConfig

    config = TaskrConfig(
        database=DatabaseConfig(
            type="postgres",
            postgres_url="postgresql://user:secretpassword@host:5432/db",
        )
    )

    result = config.to_dict()

    # URL should be masked
    assert "secretpassword" not in str(result)
    assert "..." in result["database"]["postgres_url"]
