#!/usr/bin/env python3
"""
Test script for the AI Document Organizer V2 plugin system.
This script tests plugin discovery, initialization, and basic functionality.
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PluginTest")

# Check for Google API Key in environment
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
if not GOOGLE_API_KEY:
    logger.warning("No Google API Key found in environment. Set GOOGLE_API_KEY or GEMINI_API_KEY to enable AI features.")

# Import V2 plugin system
from ai_document_organizer_v2.core import PluginManager, SettingsManager
from ai_document_organizer_v2.compatibility import CompatibilityManager


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description='Test AI Document Organizer V2 plugin system')
    parser.add_argument('--pdf', help='Path to a PDF file to test with the PDF parser plugin')
    parser.add_argument('--text', help='Text to analyze with the AI analyzer plugin')
    parser.add_argument('--test-all', action='store_true', help='Test all available plugins')
    args = parser.parse_args()
    
    logger.info("Starting V2 plugin system test")
    
    # Initialize plugin system
    settings_manager = SettingsManager()
    plugin_manager = PluginManager(settings_manager=settings_manager)
    
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
            
            # Configure plugin settings
            logger.info("Configuring PDF parser settings...")
            
            # Enable OCR and image extraction for testing
            settings_manager.set_setting("pdf_parser.ocr_enabled", True)
            settings_manager.set_setting("pdf_parser.ocr_language", "eng")
            settings_manager.set_setting("pdf_parser.extract_images", True)
            
            logger.info("PDF Parser settings:")
            logger.info(f"  - OCR Enabled: {settings_manager.get_setting('pdf_parser.ocr_enabled')}")
            logger.info(f"  - OCR Language: {settings_manager.get_setting('pdf_parser.ocr_language')}")
            logger.info(f"  - Extract Images: {settings_manager.get_setting('pdf_parser.extract_images')}")
            
            # Parse the PDF file
            logger.info("Parsing PDF file...")
            result = pdf_parser.parse_file(args.pdf)
            
            # Debug the result
            logger.info(f"PDF parser result type: {type(result)}")
            
            # Check if result is valid
            if not result:
                logger.error("Error parsing PDF: No result returned")
            elif isinstance(result, dict) and 'error' in result and result['error']:
                logger.error(f"Error parsing PDF: {result['error']}")
            else:
                # Any other valid result - treat as success
                logger.info("PDF parsed successfully")
                logger.info("Metadata:")
                for key, value in result.get('metadata', {}).items():
                    if isinstance(value, dict):
                        logger.info(f"  - {key}:")
                        for subkey, subvalue in value.items():
                            logger.info(f"    - {subkey}: {subvalue}")
                    elif isinstance(value, list) and key == 'images':
                        logger.info(f"  - {key}: (list with {len(value)} items)")
                        for i, img_info in enumerate(value[:2]):  # Show first 2 images only
                            logger.info(f"    Item {i+1}:")
                            for img_key, img_val in img_info.items():
                                logger.info(f"      {img_key}: {img_val}")
                    else:
                        logger.info(f"  - {key}: {value}")
                
                content = result.get('content', '')
                content_preview = content[:100] + '...' if len(content) > 100 else content
                logger.info(f"Content preview: {content_preview}")
                
                # Images already reported above in metadata section
                
                # Check if OCR was used
                if result.get('metadata', {}).get('ocr_used', False):
                    logger.info(f"OCR was used with language: {result['metadata'].get('ocr_language', 'unknown')}")
                
                # If text was extracted and AI analyzer is available, analyze it
                if content and args.test_all:
                    logger.info("Testing PDF content analysis with AI analyzer...")
                    
                    # Find Gemini analyzer
                    ai_analyzers = plugin_manager.get_plugins_of_type('ai_analyzer')
                    gemini_analyzer = None
                    for analyzer_id, analyzer in ai_analyzers.items():
                        if 'gemini' in analyzer_id.lower():
                            gemini_analyzer = analyzer
                            break
                    
                    if gemini_analyzer and getattr(gemini_analyzer, 'gemini_available', False):
                        logger.info(f"Analyzing PDF content with {gemini_analyzer.name}...")
                        analysis = gemini_analyzer.analyze_content(content, "pdf")
                        
                        if 'error' in analysis:
                            logger.error(f"Error analyzing PDF content: {analysis['error']}")
                        else:
                            logger.info("PDF content analyzed successfully")
                            logger.info("Analysis results:")
                            for key, value in analysis.items():
                                if isinstance(value, list):
                                    value_str = ", ".join(value[:3])
                                    if len(value) > 3:
                                        value_str += ", ..."
                                else:
                                    value_str = str(value)
                                logger.info(f"  - {key}: {value_str}")
                    else:
                        logger.warning("AI analyzer not available for PDF content analysis")
        else:
            logger.warning("PDF parser plugin not found")
    
    # Test AI analyzer plugin if text was provided
    if args.text:
        logger.info(f"Testing AI analyzer with text: {args.text[:30]}...")
        
        # Get AI analyzer plugins
        ai_analyzers = plugin_manager.get_plugins_of_type('ai_analyzer')
        
        # Find Gemini analyzer
        gemini_analyzer = None
        for analyzer_id, analyzer in ai_analyzers.items():
            if 'gemini' in analyzer_id.lower():
                gemini_analyzer = analyzer
                break
        
        if gemini_analyzer:
            logger.info(f"Found AI analyzer: {gemini_analyzer.name}")
            
            # Check if Gemini is available
            gemini_available = getattr(gemini_analyzer, 'gemini_available', False)
            status = "Available" if gemini_available else "Missing"
            logger.info(f"Gemini AI availability: {status}")
            
            if gemini_available:
                # Get available models
                models = gemini_analyzer.get_available_models()
                models_preview = models[:3] + ['...'] if len(models) > 3 else models
                logger.info(f"Available models: {', '.join(models_preview)}")
                
                # Analyze text
                logger.info("Analyzing text content...")
                result = gemini_analyzer.analyze_content(args.text, "text")
                
                if 'error' in result:
                    logger.error(f"Error analyzing text: {result['error']}")
                else:
                    logger.info("Text analyzed successfully")
                    logger.info("Analysis results:")
                    for key, value in result.items():
                        if isinstance(value, list):
                            value_str = ", ".join(value[:3])
                            if len(value) > 3:
                                value_str += ", ..."
                        else:
                            value_str = str(value)
                        logger.info(f"  - {key}: {value_str}")
        else:
            logger.warning("AI analyzer plugin not found")
    
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