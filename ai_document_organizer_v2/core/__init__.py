"""
Core components for AI Document Organizer V2.

Provides plugin architecture and management.
"""

from .plugin_base import PluginBase
from .plugin_manager import PluginManager

__all__ = [
    'PluginBase',
    'PluginManager'
]