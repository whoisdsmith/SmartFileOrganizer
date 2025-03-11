#!/usr/bin/env python3
"""
Test script for the Image Analyzer plugin.

This script tests the functionality of the Image Analyzer plugin,
including initialization, image analysis, and feature extraction.

Usage:
    python test_image_analyzer.py [--image IMAGE_PATH]
"""

import os
import sys
import logging
import argparse
from PIL import Image

from ai_document_organizer_v2.core.plugin_manager import PluginManager
from ai_document_organizer_v2.core.settings import SettingsManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ImageAnalyzerTest')

def create_test_image(output_path):
    """Create a test image if none is provided."""
    try:
        # Create a simple gradient test image
        width, height = 400, 300
        image = Image.new('RGB', (width, height), color='white')
        
        # Draw a gradient
        for x in range(width):
            for y in range(height):
                r = int(255 * x / width)
                g = int(255 * y / height)
                b = int(255 * (x + y) / (width + height))
                image.putpixel((x, y), (r, g, b))
        
        # Add some shapes for testing
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        draw.rectangle((50, 50, 150, 100), fill=(255, 0, 0))
        draw.ellipse((200, 100, 300, 200), fill=(0, 255, 0))
        draw.polygon([(150, 150), (200, 250), (100, 250)], fill=(0, 0, 255))
        
        # Save the test image
        image.save(output_path)
        logger.info(f"Created test image at {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create test image: {e}")
        return False

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test the Image Analyzer plugin')
    parser.add_argument('--image', type=str, help='Path to image file for testing')
    return parser.parse_args()

def main():
    """Main test function."""
    args = parse_args()
    
    # Check if PIL is available
    try:
        import PIL
        logger.info(f"PIL/Pillow version: {PIL.__version__}")
    except ImportError:
        logger.error("PIL/Pillow library is not installed")
        return
    
    # Get or create an image for testing
    if args.image and os.path.exists(args.image):
        test_image_path = args.image
        logger.info(f"Using provided image: {test_image_path}")
    else:
        test_image_path = 'test_image.png'
        logger.info("No image provided, creating a test image")
        if not create_test_image(test_image_path):
            logger.error("Failed to create or use test image")
            return
    
    # Create settings manager and plugin manager
    settings_manager = SettingsManager()
    plugin_manager = PluginManager(settings_manager=settings_manager)
    
    # Discover plugins
    logger.info("Discovering plugins...")
    plugin_manager.discover_plugins()
    
    if not plugin_manager.plugins:
        logger.error("No plugins found!")
        return
    
    logger.info(f"Found {len(plugin_manager.plugins)} plugins")
    
    # Initialize plugins
    logger.info("Initializing plugins...")
    plugin_manager.initialize_plugins()
    
    # Find image analyzer plugin
    image_analyzers = plugin_manager.get_plugins_of_type('ai_analyzer')
    image_analyzer = None
    
    for analyzer_id, analyzer in image_analyzers.items():
        if 'image_analyzer' in analyzer_id:
            image_analyzer = analyzer
            break
    
    if not image_analyzer:
        logger.error("Image analyzer plugin not found")
        return
    
    logger.info(f"Found image analyzer: {image_analyzer.name}")
    
    # Test image analysis
    logger.info(f"Analyzing image: {test_image_path}")
    
    # Configure settings
    settings_manager.set_setting('image_analyzer.extract_dominant_colors', True)
    settings_manager.set_setting('image_analyzer.max_dominant_colors', 5)
    settings_manager.set_setting('image_analyzer.generate_thumbnails', True)
    
    # Analyze the image
    result = image_analyzer.analyze_image(test_image_path)
    
    if not result.get('success', False):
        logger.error(f"Error analyzing image: {result.get('error', 'Unknown error')}")
        return
    
    # Display results
    logger.info("Image analysis successful")
    
    logger.info("File Information:")
    for key, value in result['file_info'].items():
        logger.info(f"  - {key}: {value}")
    
    logger.info("Image Metadata:")
    for key, value in result['metadata'].items():
        if isinstance(value, dict):
            logger.info(f"  - {key}:")
            for subkey, subvalue in value.items():
                logger.info(f"    - {subkey}: {subvalue}")
        else:
            logger.info(f"  - {key}: {value}")
    
    logger.info("Image Features:")
    if 'dominant_colors' in result.get('features', {}):
        logger.info("  - Dominant Colors:")
        for i, color in enumerate(result['features']['dominant_colors']):
            logger.info(f"    {i+1}. {color['hex']} (RGB: {color['rgb']}, Frequency: {color['frequency']:.2f})")
    
    # Check for thumbnail
    if 'thumbnail_path' in result:
        logger.info(f"Thumbnail generated at: {result['thumbnail_path']}")
    
    # Shutdown plugins
    logger.info("Shutting down plugins...")
    plugin_manager.shutdown_plugins()
    
    logger.info("Test completed successfully")
    
    # Clean up test image if we created it
    if not args.image and os.path.exists(test_image_path):
        try:
            os.remove(test_image_path)
            logger.info(f"Removed test image: {test_image_path}")
        except Exception as e:
            logger.warning(f"Failed to remove test image: {e}")


if __name__ == "__main__":
    main()