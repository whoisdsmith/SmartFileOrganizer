"""
Core components for AI Document Organizer V2.
"""

from .plugin_base import PluginBase
from .plugin_manager import PluginManager
from .settings_manager import SettingsManager

__all__ = ["PluginBase", "PluginManager", "SettingsManager"]