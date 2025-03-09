#!/usr/bin/env python3
"""
Test API Keys - A simplified script to check if both Google and OpenAI API keys are working
"""

import os
import sys
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("APIKeyTest")

def test_google_api():
    """Test if Google Gemini API key is working"""
    try:
        import google.generativeai as genai
        
        # Get API key from environment variable
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            logger.error("GOOGLE_API_KEY environment variable not set")
            return False
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Get available models
        try:
            models = [m.name for m in genai.list_models()]
            logger.info(f"Available Gemini models: {models[:5]}... (truncated)")
            
            # Try to use a model
            model_name = "models/gemini-1.5-flash"  # Use a standard model
            model = genai.GenerativeModel(model_name)
            
            # Simple test prompt
            response = model.generate_content("Hello, what's the weather like today?")
            
            logger.info("Google Gemini API test successful!")
            logger.info(f"Response preview: {str(response)[:100]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error with Google Gemini API: {e}")
            return False
            
    except ImportError:
        logger.error("google-generativeai package not installed")
        return False

def test_openai_api():
    """Test if OpenAI API key is working"""
    try:
        from openai import OpenAI
        
        # Get API key from environment variable
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            return False
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Try a simple completion
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use a standard model
                messages=[{"role": "user", "content": "Hello, how are you today?"}],
                max_tokens=20
            )
            
            logger.info("OpenAI API test successful!")
            logger.info(f"Response: {response.choices[0].message.content}")
            return True
            
        except Exception as e:
            logger.error(f"Error with OpenAI API: {e}")
            return False
            
    except ImportError:
        logger.error("openai package not installed")
        return False

def main():
    """Main function to test both APIs"""
    logger.info("Testing API keys...")
    
    # Test Google API
    google_success = test_google_api()
    
    # Test OpenAI API
    openai_success = test_openai_api()
    
    # Summary
    logger.info("\n===== API TEST RESULTS =====")
    logger.info(f"Google Gemini API: {'✓ WORKING' if google_success else '✗ NOT WORKING'}")
    logger.info(f"OpenAI API: {'✓ WORKING' if openai_success else '✗ NOT WORKING'}")
    
    if google_success and openai_success:
        logger.info("All API keys are working correctly!")
    elif not google_success and not openai_success:
        logger.error("Both API keys are not working. Please check your credentials.")
    else:
        logger.warning("One API key is working, but the other is not. Review the logs above for details.")

if __name__ == "__main__":
    main()