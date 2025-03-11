"""
AI Document Organizer V2 - Plugin-based architecture for document organization.

This package provides a plugin-based architecture for the AI Document Organizer,
allowing for extensibility and customization.
"""

__version__ = "2.0.0"

# Import core components for easier access
from .core.plugin_manager import PluginManager
from .core.settings import SettingsManager
from .core.plugin_base import (
    BasePlugin,
    FileParserPlugin,
    AIAnalyzerPlugin,
    OrganizerPlugin,
    UtilityPlugin
)

# Import compatibility layer
from .compatibility.v1_adapter import CompatibilityManager

# Initialize logging
import logging
logging.getLogger("AIDocumentOrganizerV2").setLevel(logging.INFO)