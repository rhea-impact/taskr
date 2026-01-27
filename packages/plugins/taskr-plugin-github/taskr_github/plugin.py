"""
GitHub Plugin for Taskr.

Provides GitHub Projects V2 integration including:
- Creating issues and adding to projects
- Managing project items
- Creating PRs with issue linking
"""

import os
from typing import TYPE_CHECKING

from taskr.plugins import TaskrPlugin, PluginInfo

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class GitHubPlugin(TaskrPlugin):
    """
    GitHub Projects V2 integration plugin.

    Requires GITHUB_TOKEN environment variable or config setting.
    """

    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="github",
            version="0.1.0",
            description="GitHub Projects V2 integration",
            requires_postgres=False,  # Works with SQLite too
            author="Rhea Impact",
        )

    def register_tools(self, mcp: "FastMCP") -> None:
        """Register GitHub tools with the MCP server."""
        from taskr_github import tools
        tools.register(mcp, self)

    def get_github_token(self) -> str:
        """Get GitHub token from config or environment."""
        # Check plugin config first
        token_env = self.get_config("token_env", "GITHUB_TOKEN")
        token = os.environ.get(token_env)

        if not token:
            raise ValueError(
                f"GitHub token not found. Set {token_env} environment variable "
                "or configure plugins.github.token_env in config."
            )

        return token

    def get_default_org(self) -> str:
        """Get default organization from config."""
        return self.get_config("default_org", "")
