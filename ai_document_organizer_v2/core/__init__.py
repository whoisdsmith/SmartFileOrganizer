"""
Core components for AI Document Organizer V2.

This package provides the core functionality for the AI Document Organizer,
including the plugin system, settings management, and other essential components.
"""

from .plugin_base import PluginBase
from .plugin_manager import PluginManager
from .settings import SettingsManager

__all__ = ['PluginBase', 'PluginManager', 'SettingsManager']