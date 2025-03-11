"""
External API Integration Framework for AI Document Organizer V2.

This framework provides a standardized way to connect with various external APIs,
enhancing the application's capabilities and allowing for extensible third-party service integration.
"""

from .api_plugin_base import APIPluginBase
from .api_gateway import APIGateway
from .rate_limiter import RateLimiter
from .auth_provider import AuthProvider