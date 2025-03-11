"""
Test script for the lightweight audio analyzer
"""

import os
import sys
import logging
from pprint import pprint

# Import our lightweight analyzer
from lite_audio_analyzer import LiteAudioAnalyzer, analyze_file

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LiteAudioTest")

def main():
    """Main test function"""
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
    else:
        audio_path = "test_files/test_audio.wav"
        
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return False
    
    logger.info(f"Testing audio analysis with file: {audio_path}")
    
    # Method 1: Use the class directly
    analyzer = LiteAudioAnalyzer()
    logger.info(f"Created analyzer: {analyzer.name} v{analyzer.version}")
    logger.info(f"Supported extensions: {analyzer.supported_extensions}")
    
    results = analyzer.analyze_audio(audio_path)
    
    if results.get('success', False):
        logger.info("Analysis successful")
        logger.info("Analysis results:")
        pprint(results)
    else:
        logger.error(f"Analysis failed: {results.get('error', 'Unknown error')}")
        return False
    
    # Method 2: Use the standalone function
    logger.info("\nTesting standalone analyze_file function")
    func_results = analyze_file(audio_path)
    
    if func_results.get('success', False):
        logger.info("Standalone function analysis successful")
    else:
        logger.error(f"Standalone function analysis failed: {func_results.get('error', 'Unknown error')}")
        return False
    
    logger.info("All tests completed successfully")
    return True

if __name__ == "__main__":
    main()