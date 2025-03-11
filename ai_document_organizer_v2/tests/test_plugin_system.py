"""
Test script for the AI Document Organizer V2 plugin system.

This script demonstrates how to use the plugin system.
"""

import os
import sys
import logging
import argparse
from typing import Dict, List, Any

from ai_document_organizer_v2.core import PluginManager, SettingsManager
from ai_document_organizer_v2.compatibility import CompatibilityManager


def setup_logging():
    """Setup logging for the test script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_plugin_discovery(plugin_dirs=None):
    """
    Test plugin discovery.
    
    Args:
        plugin_dirs: Optional list of plugin directories to search
    """
    print("Testing plugin discovery...")
    
    # Create plugin manager
    plugin_manager = PluginManager(plugin_dirs)
    
    # Discover plugins
    results = plugin_manager.discover_plugins()
    
    print(f"Found {results['found']} plugins")
    print(f"Loaded {results['loaded']} plugins")
    print(f"Failed to load {results['failed']} plugins")
    
    if results['failures']:
        print("\nFailures:")
        for failure in results['failures']:
            print(f"  Path: {failure['path']}")
            print(f"  Error: {failure['error']}")
    
    # Show discovered plugins
    print("\nDiscovered plugins:")
    for plugin_type in plugin_manager.get_plugin_types():
        plugins = plugin_manager.get_plugins_of_type(plugin_type)
        print(f"\n{plugin_type.upper()} Plugins:")
        for plugin_id, plugin in plugins.items():
            print(f"  - {plugin.name} ({plugin_id}), version {plugin.version}")
            print(f"    {plugin.description}")
    
    # Initialize plugins
    init_results = plugin_manager.initialize_plugins()
    print(f"\nInitialized {init_results['successful']} plugins")
    print(f"Failed to initialize {init_results['failed']} plugins")
    
    if init_results['failures']:
        print("\nInitialization failures:")
        for failure in init_results['failures']:
            print(f"  Plugin ID: {failure['plugin_id']}")
            print(f"  Error: {failure['error']}")
    
    return plugin_manager


def test_compatibility_layer(plugin_manager):
    """
    Test the compatibility layer with V1 code.
    
    Args:
        plugin_manager: Initialized plugin manager
    """
    print("\nTesting compatibility layer...")
    
    # Create settings manager
    settings_manager = SettingsManager()
    
    # Create compatibility manager
    compat_manager = CompatibilityManager(plugin_manager, settings_manager)
    
    # Get adapters
    file_parser_adapter = compat_manager.get_adapter('FileParser')
    ai_analyzer_adapter = compat_manager.get_adapter('AIAnalyzer')
    
    if file_parser_adapter:
        print("Successfully created FileParser adapter")
        
        # Create a V1-compatible FileParser instance
        file_parser = file_parser_adapter.create_instance()
        print(f"V1-compatible FileParser instance: {file_parser.__class__.__name__}")
    else:
        print("Failed to create FileParser adapter")
    
    if ai_analyzer_adapter:
        print("Successfully created AIAnalyzer adapter")
        
        # Create a V1-compatible AIAnalyzer instance
        ai_analyzer = ai_analyzer_adapter.create_instance()
        print(f"V1-compatible AIAnalyzer instance: {ai_analyzer.__class__.__name__}")
    else:
        print("Failed to create AIAnalyzer adapter")


def test_pdf_parser_plugin(plugin_manager, file_path=None):
    """
    Test the PDF parser plugin.
    
    Args:
        plugin_manager: Initialized plugin manager
        file_path: Optional path to a PDF file to parse
    """
    print("\nTesting PDF parser plugin...")
    
    # Get file parser plugins
    parsers = plugin_manager.get_plugins_of_type('file_parser')
    
    # Find PDF parser
    pdf_parser = None
    for parser_id, parser in parsers.items():
        if 'pdf' in parser_id.lower():
            pdf_parser = parser
            break
    
    if pdf_parser:
        print(f"Found PDF parser: {pdf_parser.name} ({pdf_parser.plugin_id})")
        print(f"Supported extensions: {pdf_parser.supported_extensions()}")
        
        # Check dependencies
        deps = pdf_parser.check_dependencies()
        print("\nDependency status:")
        for dep, available in deps.items():
            status = "Available" if available else "Missing"
            print(f"  - {dep}: {status}")
        
        # Parse a PDF file if provided
        if file_path and os.path.exists(file_path) and file_path.lower().endswith('.pdf'):
            print(f"\nParsing PDF file: {file_path}")
            result = pdf_parser.parse_file(file_path)
            
            if 'error' in result:
                print(f"Error parsing PDF: {result['error']}")
            else:
                print("\nPDF metadata:")
                for key, value in result.get('metadata', {}).items():
                    print(f"  - {key}: {value}")
                
                content = result.get('content', '')
                content_preview = content[:200] + '...' if len(content) > 200 else content
                print(f"\nContent preview:\n{content_preview}")
        elif file_path:
            print(f"File not found or not a PDF: {file_path}")
        else:
            print("No PDF file provided for testing")
    else:
        print("PDF parser plugin not found")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test AI Document Organizer V2 plugin system")
    parser.add_argument('--pdf', help="Path to a PDF file to test with the PDF parser plugin")
    args = parser.parse_args()
    
    setup_logging()
    
    print("=" * 70)
    print("AI Document Organizer V2 Plugin System Test")
    print("=" * 70)
    
    # Test plugin discovery
    plugin_manager = test_plugin_discovery()
    
    # Test compatibility layer
    test_compatibility_layer(plugin_manager)
    
    # Test PDF parser plugin
    test_pdf_parser_plugin(plugin_manager, args.pdf)
    
    # Shutdown plugins
    shutdown_results = plugin_manager.shutdown_plugins()
    print(f"\nShutdown {shutdown_results['successful']} plugins")
    print(f"Failed to shutdown {shutdown_results['failed']} plugins")
    
    print("\nTest completed!")


if __name__ == "__main__":
    main()