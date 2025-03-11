#!/usr/bin/env python
"""
Test script for API Integration Framework's caching and transformation features.

This script demonstrates how to:
1. Use caching with API operations
2. Apply transformation pipelines to API responses
3. Verify cache hits and statistics
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, List

# Add the root project directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # ai_document_organizer_v2 directory
root_dir = os.path.dirname(parent_dir)     # project root directory
sys.path.insert(0, root_dir)

# Import project modules
from ai_document_organizer_v2.plugins.api_integration.api_gateway import APIGateway
from ai_document_organizer_v2.plugins.api_integration.plugins.translation_api import TranslationAPIPlugin


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_api_gateway() -> APIGateway:
    """Set up the API Gateway with test configuration."""
    config = {
        'cache_config': {
            'cache_dir': './cache',
            'max_cache_size': 1024 * 1024 * 10,  # 10 MB
            'enable_memory_cache': True,
            'memory_cache_size': 100,
            'enable_disk_cache': True
        },
        'transform_config_dir': './transform_configs'
    }
    
    # Create the API Gateway
    gateway = APIGateway(config)
    return gateway


def register_plugins(gateway: APIGateway) -> None:
    """Register test plugins with the API Gateway."""
    # Register the Translation API plugin
    translation_plugin = TranslationAPIPlugin()
    gateway.register_plugin(translation_plugin)
    
    # Initialize and authenticate the plugin
    # Note: In production, these would be secure credentials from an environment variable
    api_key = os.environ.get('GOOGLE_API_KEY', 'test_api_key')
    project_id = os.environ.get('GOOGLE_PROJECT_ID', 'test_project_id')
    
    plugin_name = translation_plugin.__class__.__name__
    plugin = gateway.get_plugin(plugin_name)
    plugin.initialize({
        'api_key': api_key,
        'project_id': project_id
    })
    
    # In a real test, you would properly authenticate with valid credentials
    # For demo purposes, we're mocking this
    logger.warning("Using test credentials - mocking authentication and API responses")
    translation_plugin._is_authenticated = True
    
    # Mock the _operation_translate_text method for testing
    original_translate = translation_plugin._operation_translate_text
    
    def mock_operation_translate_text(self, text, target_language, source_language=None, **kwargs):
        """Mock translation method that returns predefined responses."""
        logger.info(f"Mocked translation: {text} -> {target_language}")
        
        # Create a mock response that matches the structure expected by the transformer
        translations = [{
            "translatedText": f"[{target_language}] {text}",
            "model": "mock-nmt-model",
            "detectedLanguage": source_language or "en"
        }]
        
        return {
            "success": True,
            "data": {
                "translations": translations
            },
            "timestamp": time.time(),
            "status_code": 200
        }
    
    # Replace the real method with our mock
    translation_plugin._operation_translate_text = mock_operation_translate_text.__get__(translation_plugin)


def create_test_transform_pipeline(gateway: APIGateway) -> None:
    """Create a test transformation pipeline."""
    # Define a simple transform pipeline for translation responses
    transform_config = {
        'name': 'translation_transformer',
        'description': 'Transforms translation API responses',
        'stages': [
            {
                'type': 'filter',
                'name': 'extract_translated_text',
                'config': {
                    'path': 'translations[0].translatedText'
                }
            },
            {
                'type': 'json_mapping',
                'name': 'add_metadata',
                'config': {
                    'mappings': {
                        'translated_text': '.',
                        'source': 'context.parameters.text',
                        'target_language': 'context.parameters.target_language',
                        'source_language': 'context.parameters.source_language',
                        'timestamp': 'timestamp()',
                        'cached': 'context.from_cache || false'
                    }
                }
            }
        ]
    }
    
    # Register the transformation pipeline
    gateway.register_transformation_pipeline('translation_transformer', transform_config)


def test_caching(gateway: APIGateway) -> None:
    """Test the caching functionality with the Translation API."""
    logger.info("Testing API caching functionality...")
    
    # First request should be a cache miss
    logger.info("Making first request (should be cache miss)...")
    result1 = gateway.execute_operation(
        plugin_name='TranslationAPIPlugin',
        operation='translate_text',
        text='Hello world',
        target_language='es',
        source_language='en'
    )
    
    if result1.get('success', False):
        logger.info(f"Translation result: {result1.get('data')}")
    else:
        logger.error(f"Translation failed: {result1.get('error')}")
        return
    
    # Second identical request should be a cache hit
    logger.info("Making second identical request (should be cache hit)...")
    result2 = gateway.execute_operation(
        plugin_name='TranslationAPIPlugin',
        operation='translate_text',
        text='Hello world',
        target_language='es',
        source_language='en'
    )
    
    # Check if it was a cache hit
    if result2.get('from_cache', False):
        logger.info("Cache hit confirmed!")
        logger.info(f"Cache metadata: {result2.get('cache_metadata', {})}")
    else:
        logger.warning("Expected cache hit, but got a miss!")
    
    # Get cache statistics
    cache_stats = gateway.get_cache_stats()
    logger.info(f"Cache statistics: {json.dumps(cache_stats, indent=2)}")


def test_transformation(gateway: APIGateway) -> None:
    """Test transformation pipelines with the Translation API."""
    logger.info("Testing transformation pipeline functionality...")
    
    # Execute with transformation pipeline
    result = gateway.execute_operation(
        plugin_name='TranslationAPIPlugin',
        operation='translate_text',
        transform_pipeline='translation_transformer',
        text='Good morning',
        target_language='fr',
        source_language='en'
    )
    
    if result.get('success', False):
        logger.info(f"Transformed result: {json.dumps(result.get('data'), indent=2)}")
    else:
        logger.error(f"Translation with transformation failed: {result.get('error')}")


def test_cache_invalidation(gateway: APIGateway) -> None:
    """Test cache invalidation."""
    logger.info("Testing cache invalidation...")
    
    # Make a request to cache
    gateway.execute_operation(
        plugin_name='TranslationAPIPlugin',
        operation='translate_text',
        text='Good evening',
        target_language='de',
        source_language='en'
    )
    
    # Get cache stats before invalidation
    stats_before = gateway.get_cache_stats()
    logger.info(f"Cache statistics before invalidation: {json.dumps(stats_before, indent=2)}")
    
    # Invalidate specific cache entries
    invalidation_result = gateway.invalidate_cache(
        plugin_name='TranslationAPIPlugin',
        operation='translate_text'
    )
    
    logger.info(f"Invalidation result: {json.dumps(invalidation_result, indent=2)}")
    
    # Get cache stats after invalidation
    stats_after = gateway.get_cache_stats()
    logger.info(f"Cache statistics after invalidation: {json.dumps(stats_after, indent=2)}")


def test_bypass_cache(gateway: APIGateway) -> None:
    """Test bypassing the cache."""
    logger.info("Testing cache bypass...")
    
    # Make a cacheable request
    gateway.execute_operation(
        plugin_name='TranslationAPIPlugin',
        operation='translate_text',
        text='Hello',
        target_language='it',
        source_language='en'
    )
    
    # Now bypass the cache for the same request
    logger.info("Making the same request with cache bypass...")
    result = gateway.execute_operation(
        plugin_name='TranslationAPIPlugin',
        operation='translate_text',
        bypass_cache=True,
        text='Hello',
        target_language='it',
        source_language='en'
    )
    
    if not result.get('from_cache', False):
        logger.info("Cache successfully bypassed")
    else:
        logger.warning("Failed to bypass cache!")


def main():
    """Main function to demonstrate API caching and transformation."""
    logger.info("Starting API caching and transformation test...")
    
    try:
        # Set up the API Gateway
        gateway = setup_api_gateway()
        
        # Register plugins
        register_plugins(gateway)
        
        # Create test transformation pipeline
        create_test_transform_pipeline(gateway)
        
        # Test caching
        test_caching(gateway)
        
        # Test transformation
        test_transformation(gateway)
        
        # Test cache invalidation
        test_cache_invalidation(gateway)
        
        # Test cache bypass
        test_bypass_cache(gateway)
        
        logger.info("API caching and transformation test completed successfully!")
        
    except Exception as e:
        logger.exception(f"Error during API caching and transformation test: {e}")


if __name__ == '__main__':
    main()