"""
Core module for AI Document Organizer V2 plugin architecture.
"""

# Export plugin base classes for easier imports
from .plugin_base import (
    BasePlugin,
    FileParserPlugin,
    AIAnalyzerPlugin,
    OrganizerPlugin,
    UtilityPlugin
)

# Export manager classes
from .plugin_manager import PluginManager
from .settings import SettingsManager