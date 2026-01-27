"""
Taskr Plugin System

Plugins extend Taskr with additional tools and capabilities.
"""

from taskr.plugins.interface import TaskrPlugin, PluginInfo

__all__ = [
    "TaskrPlugin",
    "PluginInfo",
]
