"""
Supabase Plugin for Taskr.

Provides Supabase integration including:
- Edge Function deployment
- Migration management
- Database operations
"""

import os
from typing import TYPE_CHECKING

from taskr.plugins import TaskrPlugin, PluginInfo

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class SupabasePlugin(TaskrPlugin):
    """
    Supabase integration plugin.

    Requires Supabase project credentials via environment or config.
    """

    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="supabase",
            version="0.1.0",
            description="Supabase Edge Functions and migration management",
            requires_postgres=True,  # Only useful with Supabase PostgreSQL
            author="Rhea Impact",
        )

    def register_tools(self, mcp: "FastMCP") -> None:
        """Register Supabase tools with the MCP server."""
        from taskr_supabase import tools
        tools.register(mcp, self)

    def get_project_ref(self) -> str:
        """Get Supabase project reference ID."""
        ref = self.get_config("project_ref") or os.environ.get("SUPABASE_PROJECT_REF")
        if not ref:
            raise ValueError(
                "Supabase project reference not found. "
                "Set SUPABASE_PROJECT_REF or plugins.supabase.project_ref in config."
            )
        return ref

    def get_service_key(self) -> str:
        """Get Supabase service role key."""
        key_env = self.get_config("service_key_env", "SUPABASE_SERVICE_KEY")
        key = os.environ.get(key_env)
        if not key:
            raise ValueError(
                f"Supabase service key not found in {key_env}. "
                "Set the environment variable or configure plugins.supabase.service_key_env"
            )
        return key

    def get_access_token(self) -> str:
        """Get Supabase Management API access token."""
        token_env = self.get_config("access_token_env", "SUPABASE_ACCESS_TOKEN")
        token = os.environ.get(token_env)
        if not token:
            raise ValueError(
                f"Supabase access token not found in {token_env}. "
                "Generate one at https://app.supabase.com/account/tokens"
            )
        return token
