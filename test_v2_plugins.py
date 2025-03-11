#!/usr/bin/env python3
"""
Test script for the AI Document Organizer V2 plugin system.
This script tests plugin discovery, initialization, and basic functionality.
"""

import os
import sys
import argparse
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PluginTest")

# Import V2 plugin system
from ai_document_organizer_v2.core import PluginManager, SettingsManager
from ai_document_organizer_v2.compatibility import CompatibilityManager


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description='Test AI Document Organizer V2 plugin system')
    parser.add_argument('--pdf', help='Path to a PDF file to test with the PDF parser plugin')
    args = parser.parse_args()
    
    logger.info("Starting V2 plugin system test")
    
    # Initialize plugin system
    settings_manager = SettingsManager()
    plugin_manager = PluginManager()
    
    # Discover plugins
    logger.info("Discovering plugins...")
    discovery_results = plugin_manager.discover_plugins()
    logger.info(f"Found {discovery_results['found']} plugins")
    logger.info(f"Loaded {discovery_results['loaded']} plugins")
    
    if discovery_results['failed'] > 0:
        logger.warning(f"Failed to load {discovery_results['failed']} plugins")
        for failure in discovery_results['failures']:
            logger.warning(f"  - {failure['path']}: {failure['error']}")
    
    # Initialize plugins
    logger.info("Initializing plugins...")
    init_results = plugin_manager.initialize_plugins()
    logger.info(f"Initialized {init_results['successful']} plugins")
    
    if init_results['failed'] > 0:
        logger.warning(f"Failed to initialize {init_results['failed']} plugins")
        for failure in init_results['failures']:
            logger.warning(f"  - {failure['plugin_id']}: {failure['error']}")
    
    # Get list of plugin types
    plugin_types = plugin_manager.get_plugin_types()
    logger.info(f"Registered plugin types: {plugin_types}")
    
    # List all plugins
    logger.info("Registered plugins:")
    for plugin_type in plugin_types:
        plugins = plugin_manager.get_plugins_of_type(plugin_type)
        logger.info(f"  {plugin_type.upper()} plugins:")
        for plugin_id, plugin in plugins.items():
            logger.info(f"    - {plugin.name} ({plugin_id}), version {plugin.version}")
            logger.info(f"      {plugin.description}")
    
    # Test PDF parser plugin if a PDF file path was provided
    if args.pdf and os.path.exists(args.pdf) and args.pdf.lower().endswith('.pdf'):
        logger.info(f"Testing PDF parser with file: {args.pdf}")
        
        # Get file parser plugins
        file_parsers = plugin_manager.get_plugins_of_type('file_parser')
        
        # Find PDF parser
        pdf_parser = None
        for parser_id, parser in file_parsers.items():
            if 'pdf' in parser_id.lower():
                pdf_parser = parser
                break
        
        if pdf_parser:
            logger.info(f"Found PDF parser: {pdf_parser.name}")
            
            # Get PDF library availability status
            logger.info("Dependency status:")
            pdf_lib_available = getattr(pdf_parser, 'pdf_library_available', False)
            status = "Available" if pdf_lib_available else "Missing"
            logger.info(f"  - PDF Library: {status}")
            
            # Parse the PDF file
            logger.info("Parsing PDF file...")
            result = pdf_parser.parse_file(args.pdf)
            
            if 'error' in result:
                logger.error(f"Error parsing PDF: {result['error']}")
            else:
                logger.info("PDF parsed successfully")
                logger.info("Metadata:")
                for key, value in result.get('metadata', {}).items():
                    logger.info(f"  - {key}: {value}")
                
                content = result.get('content', '')
                content_preview = content[:100] + '...' if len(content) > 100 else content
                logger.info(f"Content preview: {content_preview}")
        else:
            logger.warning("PDF parser plugin not found")
    
    # Test compatibility layer
    logger.info("Testing compatibility layer...")
    compat_manager = CompatibilityManager(plugin_manager, settings_manager)
    
    # Get adapters
    file_parser_adapter = compat_manager.get_adapter('FileParser')
    ai_analyzer_adapter = compat_manager.get_adapter('AIAnalyzer')
    
    if file_parser_adapter:
        logger.info("FileParser adapter is available")
        
        # Create V1-compatible FileParser instance
        v1_file_parser = file_parser_adapter.create_instance()
        logger.info(f"Created V1-compatible FileParser: {v1_file_parser.__class__.__name__}")
    else:
        logger.warning("FileParser adapter not found")
    
    if ai_analyzer_adapter:
        logger.info("AIAnalyzer adapter is available")
        
        # Create V1-compatible AIAnalyzer instance
        v1_ai_analyzer = ai_analyzer_adapter.create_instance()
        logger.info(f"Created V1-compatible AIAnalyzer: {v1_ai_analyzer.__class__.__name__}")
    else:
        logger.warning("AIAnalyzer adapter not found")
    
    # Shutdown plugins
    logger.info("Shutting down plugins...")
    shutdown_results = plugin_manager.shutdown_plugins()
    logger.info(f"Shutdown {shutdown_results['successful']} plugins")
    
    if shutdown_results['failed'] > 0:
        logger.warning(f"Failed to shutdown {shutdown_results['failed']} plugins")
        for failure in shutdown_results['failures']:
            logger.warning(f"  - {failure['plugin_id']}: {failure['error']}")
    
    logger.info("Test completed successfully")


if __name__ == "__main__":
    main()