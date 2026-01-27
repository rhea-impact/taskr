"""
Taskr Plugin System

Plugins extend Taskr with additional tools and capabilities.
"""

from taskr.plugins.interface import PluginInfo, TaskrPlugin

__all__ = [
    "TaskrPlugin",
    "PluginInfo",
]
