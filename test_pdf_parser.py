#!/usr/bin/env python3
"""
Simple test script for PDF parser plugin with settings.
"""
import os
import logging
import sys
import argparse
from typing import Dict, Any, cast

from ai_document_organizer_v2.core.plugin_manager import PluginManager
from ai_document_organizer_v2.core.settings import SettingsManager
from ai_document_organizer_v2.core.plugin_base import FileParserPlugin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PDFParserTest")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test PDF parser plugin")
    parser.add_argument("pdf_file", help="Path to the PDF file to test")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR processing")
    parser.add_argument("--ocr-lang", default="eng", help="OCR language (default: eng)")
    parser.add_argument("--extract-images", action="store_true", help="Enable image extraction")
    parser.add_argument("--output", "-o", help="Save content to specified file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args()

def main():
    """Test the PDF parser plugin with settings."""
    args = parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    pdf_file = args.pdf_file
    if not os.path.exists(pdf_file):
        logger.error(f"Error: File not found: {pdf_file}")
        return 1
    
    logger.info(f"Testing PDF parser with file: {pdf_file}")
    
    # Initialize settings manager
    settings_manager = SettingsManager()
    
    # Initialize plugin manager with settings_manager parameter
    plugin_manager = PluginManager(settings_manager=settings_manager)
    
    # Discover plugins
    logger.info("Discovering plugins...")
    discovered = plugin_manager.discover_plugins()
    logger.info(f"Found {discovered['found']} plugins, loaded {discovered['loaded']}, failed {discovered['failed']}")
    
    # Initialize plugins
    logger.info("Initializing plugins...")
    initialized = plugin_manager.initialize_plugins()
    logger.info(f"Initialized {initialized['successful']} plugins")
    
    # Get the PDF parser plugin
    pdf_parsers = plugin_manager.get_plugins_of_type('file_parser')
    pdf_parser_base = None
    
    for plugin_id, plugin in pdf_parsers.items():
        if 'pdf_parser' in plugin_id:
            pdf_parser_base = plugin
            break
    
    if not pdf_parser_base:
        logger.error("PDF parser plugin not found")
        return 1
        
    # Verify it's a FileParserPlugin
    if not isinstance(pdf_parser_base, FileParserPlugin):
        logger.error("Found plugin is not a FileParserPlugin")
        return 1
        
    # Cast to FileParserPlugin type for proper type checking
    pdf_parser = cast(FileParserPlugin, pdf_parser_base)
    
    logger.info(f"Found PDF parser plugin: {pdf_parser.name}")
    
    # Configure PDF parser settings
    logger.info("Configuring PDF parser settings...")
    settings_manager.set_setting("pdf_parser.ocr_enabled", args.ocr)
    settings_manager.set_setting("pdf_parser.ocr_language", args.ocr_lang)
    settings_manager.set_setting("pdf_parser.extract_images", args.extract_images)
    
    # Log the settings
    logger.info(f"PDF parser settings:")
    logger.info(f"  OCR enabled: {args.ocr}")
    logger.info(f"  OCR language: {args.ocr_lang}")
    logger.info(f"  Extract images: {args.extract_images}")
    
    # Parse the PDF file
    logger.info("Parsing PDF file...")
    result = pdf_parser.parse_file(pdf_file)
    
    # Display results
    if result.get('success', False):
        logger.info("PDF parsing successful")
        
        # Display metadata
        logger.info("Metadata:")
        for key, value in result.get('metadata', {}).items():
            if isinstance(value, dict):
                logger.info(f"  {key}:")
                for subkey, subvalue in value.items():
                    logger.info(f"    {subkey}: {subvalue}")
            elif isinstance(value, list):
                logger.info(f"  {key}: (list with {len(value)} items)")
                for i, item in enumerate(value[:3]):  # Show first 3 items only
                    if isinstance(item, dict):
                        logger.info(f"    Item {i+1}:")
                        for item_key, item_value in item.items():
                            logger.info(f"      {item_key}: {item_value}")
                    else:
                        logger.info(f"    Item {i+1}: {item}")
                if len(value) > 3:
                    logger.info(f"    ... (and {len(value) - 3} more items)")
            else:
                logger.info(f"  {key}: {value}")
        
        # Display content preview
        content = result.get('content', '')
        content_preview = content[:100] + '...' if len(content) > 100 else content
        logger.info(f"Content preview: {content_preview}")
        
        # Save content to file if requested
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Content saved to: {args.output}")
                
                # Save metadata to a JSON file alongside the content
                import json
                metadata_file = f"{os.path.splitext(args.output)[0]}_metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(result.get('metadata', {}), f, indent=2)
                logger.info(f"Metadata saved to: {metadata_file}")
            except Exception as e:
                logger.error(f"Error saving content to file: {e}")
        
        # Check if OCR was used
        if result.get('metadata', {}).get('ocr_used', False):
            logger.info(f"OCR was used with language: {result['metadata'].get('ocr_language', 'unknown')}")
        
        # Check if images were found
        if 'images' in result.get('metadata', {}):
            logger.info(f"Images found: {len(result['metadata']['images'])}")
    else:
        logger.error(f"PDF parsing failed: {result.get('error', 'Unknown error')}")
    
    # Shutdown plugins
    logger.info("Shutting down plugins...")
    plugin_manager.shutdown_plugins()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())