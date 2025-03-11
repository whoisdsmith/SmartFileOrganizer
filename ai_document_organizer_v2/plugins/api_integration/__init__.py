"""
External API Integration Framework for AI Document Organizer V2.

This package provides a standardized way to connect with various external APIs,
enhancing the application's capabilities and allowing for extensible third-party
service integrations.

Key features:
- Plugin-based API integration
- Centralized API gateway
- Secure authentication management
- Intelligent rate limiting
- Webhook support for event-driven architecture
- Polling for services without push capabilities
- Batch processing for efficiency
"""

from .api_plugin_base import APIPluginBase
from .api_gateway import APIGateway
from .rate_limiter import RateLimiter
from .auth_provider import AuthenticationProvider
from .plugin_manager import APIPluginManager
from .webhook_manager import WebhookManager, WebhookHandler
from .polling_manager import PollingManager, PollingJob
from .batch_processor import BatchProcessor, BatchJob


__all__ = [
    'APIPluginBase',
    'APIGateway',
    'RateLimiter',
    'AuthenticationProvider',
    'APIPluginManager',
    'WebhookManager',
    'WebhookHandler',
    'PollingManager',
    'PollingJob',
    'BatchProcessor',
    'BatchJob'
]