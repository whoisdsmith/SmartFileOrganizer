"""
Simple script to test the AudioAnalyzerPlugin
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AudioPluginTest")

def main():
    """Test the simple import of the AudioAnalyzerPlugin"""
    logger.info("Testing AudioAnalyzerPlugin import")
    
    try:
        # Add the project root to the path
        sys.path.append(os.path.abspath('.'))
        
        # Try to import the AudioAnalyzerPlugin
        from ai_document_organizer_v2.plugins.audio_analyzer import AudioAnalyzerPlugin
        
        logger.info("Successfully imported AudioAnalyzerPlugin")
        
        # Try to instantiate the plugin
        plugin = AudioAnalyzerPlugin()
        logger.info(f"Successfully created AudioAnalyzerPlugin instance: {plugin}")
        
        # Print plugin information
        logger.info(f"Plugin name: {plugin.name}")
        logger.info(f"Plugin version: {plugin.version}")
        logger.info(f"Plugin supported file types: {plugin.supported_file_types}")
        
        return True
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()