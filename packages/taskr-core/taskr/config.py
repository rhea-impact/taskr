"""
Taskr Configuration

Loads settings from ~/.taskr/config.yaml with environment variable overrides.
Supports both PostgreSQL and SQLite database configurations.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

CONFIG_DIR = Path.home() / ".taskr"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    type: str = "sqlite"  # "sqlite" or "postgres"
    sqlite_path: str = "~/.taskr/taskr.db"
    postgres_url: Optional[str] = None


@dataclass
class IdentityConfig:
    """User/agent identity settings."""

    author: Optional[str] = None
    agent_id: str = "claude-code"


@dataclass
class PluginConfig:
    """Plugin configuration."""

    enabled: List[str] = field(default_factory=list)
    settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class TaskrConfig:
    """
    Complete Taskr configuration.

    Loaded from ~/.taskr/config.yaml with environment variable overrides.
    """

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    identity: IdentityConfig = field(default_factory=IdentityConfig)
    plugins: PluginConfig = field(default_factory=PluginConfig)

    # Convenience accessors
    @property
    def author(self) -> Optional[str]:
        return self.identity.author

    @property
    def agent_id(self) -> str:
        return self.identity.agent_id

    def to_dict(self) -> dict:
        """Convert to dictionary for display (masks secrets)."""
        result = asdict(self)

        # Mask database URL
        if result.get("database", {}).get("postgres_url"):
            url = result["database"]["postgres_url"]
            result["database"]["postgres_url"] = url[:30] + "..." if len(url) > 30 else "***"

        return result


def _parse_database_config(data: dict) -> DatabaseConfig:
    """Parse database configuration from YAML data."""
    db_data = data.get("database", {})

    db_type = db_data.get("type", "sqlite")

    # SQLite config
    sqlite_config = db_data.get("sqlite", {})
    sqlite_path = sqlite_config.get("path", "~/.taskr/taskr.db")

    # PostgreSQL config
    postgres_config = db_data.get("postgres", {})
    postgres_url = postgres_config.get("url")

    # Check for URL from environment variable reference
    url_env = postgres_config.get("url_env")
    if url_env and not postgres_url:
        postgres_url = os.environ.get(url_env)

    return DatabaseConfig(
        type=db_type,
        sqlite_path=sqlite_path,
        postgres_url=postgres_url,
    )


def _parse_identity_config(data: dict) -> IdentityConfig:
    """Parse identity configuration from YAML data."""
    identity_data = data.get("identity", {})

    return IdentityConfig(
        author=identity_data.get("author"),
        agent_id=identity_data.get("agent_id", "claude-code"),
    )


def _parse_plugin_config(data: dict) -> PluginConfig:
    """Parse plugin configuration from YAML data."""
    plugins_data = data.get("plugins", {})

    enabled = plugins_data.get("enabled", [])

    # Plugin-specific settings (everything except 'enabled')
    settings = {k: v for k, v in plugins_data.items() if k != "enabled" and isinstance(v, dict)}

    return PluginConfig(
        enabled=enabled,
        settings=settings,
    )


def load_config(config_path: Optional[Path] = None) -> TaskrConfig:
    """
    Load configuration from file with environment variable overrides.

    Args:
        config_path: Optional path to config file. Defaults to ~/.taskr/config.yaml

    Returns:
        TaskrConfig instance
    """
    config_file = config_path or CONFIG_FILE
    config = TaskrConfig()

    # Load from YAML if available
    if HAS_YAML and config_file.exists():
        try:
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f) or {}

            config.database = _parse_database_config(data)
            config.identity = _parse_identity_config(data)
            config.plugins = _parse_plugin_config(data)

        except yaml.YAMLError as e:
            logger.warning(f"Could not parse config file at {config_file}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error loading config from {config_file}: {e}")

    # Environment variable overrides
    if os.environ.get("TASKR_DATABASE_URL"):
        config.database.type = "postgres"
        config.database.postgres_url = os.environ["TASKR_DATABASE_URL"]
    elif os.environ.get("SUPABASE_DB_URL"):
        config.database.type = "postgres"
        config.database.postgres_url = os.environ["SUPABASE_DB_URL"]

    if os.environ.get("TASKR_AUTHOR"):
        config.identity.author = os.environ["TASKR_AUTHOR"]

    if os.environ.get("TASKR_AGENT_ID"):
        config.identity.agent_id = os.environ["TASKR_AGENT_ID"]

    return config


def save_config(config: TaskrConfig, config_path: Optional[Path] = None) -> None:
    """
    Save configuration to file.

    Args:
        config: TaskrConfig instance to save
        config_path: Optional path to config file. Defaults to ~/.taskr/config.yaml
    """
    if not HAS_YAML:
        raise RuntimeError("PyYAML not installed. Run: pip install pyyaml")

    config_file = config_path or CONFIG_FILE

    # Ensure config directory exists
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Build YAML structure
    data = {
        "database": {
            "type": config.database.type,
        },
        "identity": {},
        "plugins": {
            "enabled": config.plugins.enabled,
        },
    }

    # Add database-specific config
    if config.database.type == "sqlite":
        data["database"]["sqlite"] = {"path": config.database.sqlite_path}
    elif config.database.postgres_url:
        data["database"]["postgres"] = {"url": config.database.postgres_url}

    # Add identity
    if config.identity.author:
        data["identity"]["author"] = config.identity.author
    if config.identity.agent_id != "claude-code":
        data["identity"]["agent_id"] = config.identity.agent_id

    # Add plugin settings
    data["plugins"].update(config.plugins.settings)

    # Write file
    with open(config_file, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    # Secure permissions (readable only by owner)
    config_file.chmod(0o600)

    logger.info(f"Configuration saved to {config_file}")


def ensure_config_dir() -> Path:
    """Ensure config directory exists and return its path."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


# Cached config instance
_config: Optional[TaskrConfig] = None


def get_config() -> TaskrConfig:
    """Get cached config instance, loading if needed."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> TaskrConfig:
    """Force reload config from file."""
    global _config
    _config = load_config()
    return _config
