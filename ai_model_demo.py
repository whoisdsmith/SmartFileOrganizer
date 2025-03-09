#!/usr/bin/env python3
"""
AI Model Demo - Demonstrates using both Google Gemini and OpenAI models
for document analysis in the AI Document Organizer.

This script shows how to:
1. Use the AIServiceFactory to create AI analyzers
2. Analyze document content with both AI models
3. Compare the results

Note: You need valid API keys for both services to run this demo.
"""

import os
import json
import logging
import sys
sys.path.append('.')  # Add the current directory to Python path

from src.ai_service_factory import AIServiceFactory
from src.settings_manager import SettingsManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AIModelDemo")

def check_api_keys():
    """Check if API keys are available"""
    google_key = os.environ.get("GOOGLE_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    if not google_key and not openai_key:
        logger.error("No API keys found for Google Gemini or OpenAI!")
        logger.info("Please set at least one of these environment variables:")
        logger.info("- GOOGLE_API_KEY: Your Google Gemini API key")
        logger.info("- OPENAI_API_KEY: Your OpenAI API key")
        return False
    
    services_available = []
    if google_key:
        services_available.append("Google Gemini")
    if openai_key:
        services_available.append("OpenAI")
    
    logger.info(f"Available AI services: {', '.join(services_available)}")
    return True

def analyze_with_both_services(text, file_type="txt"):
    """Analyze text with both AI services and compare results"""
    # Check if we can analyze with at least one service
    if not check_api_keys():
        return
    
    # Create settings manager
    settings_manager = SettingsManager()
    
    # Analysis results
    results = {}
    
    # Try Google Gemini if available
    if os.environ.get("GOOGLE_API_KEY"):
        logger.info("Analyzing with Google Gemini...")
        google_analyzer = AIServiceFactory.create_analyzer("google", settings_manager)
        try:
            results["google"] = google_analyzer.analyze_content(text, file_type)
            logger.info(f"Google Gemini analysis complete")
        except Exception as e:
            logger.error(f"Google Gemini analysis failed: {str(e)}")
    
    # Try OpenAI if available
    if os.environ.get("OPENAI_API_KEY"):
        logger.info("Analyzing with OpenAI...")
        openai_analyzer = AIServiceFactory.create_analyzer("openai", settings_manager)
        try:
            results["openai"] = openai_analyzer.analyze_content(text, file_type)
            logger.info(f"OpenAI analysis complete")
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {str(e)}")
    
    # Display results
    if not results:
        logger.error("No analysis results available!")
        return
    
    # Print results in a formatted way
    logger.info("=" * 50)
    logger.info("AI ANALYSIS RESULTS")
    logger.info("=" * 50)
    
    for service_name, result in results.items():
        logger.info(f"\n{service_name.upper()} ANALYSIS:")
        logger.info(f"Category: {result.get('category', 'Not available')}")
        logger.info(f"Theme: {result.get('theme', 'Not available')}")
        logger.info(f"Keywords: {', '.join(result.get('keywords', ['Not available']))}")
        logger.info(f"Summary: {result.get('summary', 'Not available')}")
        logger.info("-" * 50)
    
    # Compare the results if both are available
    if "google" in results and "openai" in results:
        logger.info("\nCOMPARISON OF RESULTS:")
        
        # Compare categories
        if results["google"].get("category") == results["openai"].get("category"):
            logger.info("✓ Both services assigned the same category")
        else:
            logger.info(f"✗ Different categories assigned:")
            logger.info(f"  - Google: {results['google'].get('category')}")
            logger.info(f"  - OpenAI: {results['openai'].get('category')}")
        
        # Compare themes
        if results["google"].get("theme") == results["openai"].get("theme"):
            logger.info("✓ Both services identified the same theme")
        else:
            logger.info(f"✗ Different themes identified:")
            logger.info(f"  - Google: {results['google'].get('theme')}")
            logger.info(f"  - OpenAI: {results['openai'].get('theme')}")
        
        # Compare keywords overlap
        google_keywords = set(results["google"].get("keywords", []))
        openai_keywords = set(results["openai"].get("keywords", []))
        common_keywords = google_keywords.intersection(openai_keywords)
        
        if common_keywords:
            logger.info(f"✓ Common keywords: {', '.join(common_keywords)}")
        else:
            logger.info("✗ No common keywords between the two services")
        
        # Exclusive keywords
        google_exclusive = google_keywords - openai_keywords
        if google_exclusive:
            logger.info(f"- Google exclusive keywords: {', '.join(google_exclusive)}")
        
        openai_exclusive = openai_keywords - google_keywords
        if openai_exclusive:
            logger.info(f"- OpenAI exclusive keywords: {', '.join(openai_exclusive)}")

def main():
    """Main function to demonstrate AI model usage"""
    logger.info("AI Document Organizer - AI Model Demo")
    logger.info("-" * 50)
    
    # Sample document text for analysis
    sample_text = """
    Project Proposal: Smart City Infrastructure
    
    Executive Summary:
    This proposal outlines a comprehensive plan to implement smart city infrastructure
    in downtown areas to improve traffic flow, reduce energy consumption, and enhance
    public safety. The project will utilize IoT sensors, AI-driven analytics, and a
    centralized management platform.
    
    Project Components:
    1. Traffic Management System
       - Adaptive traffic signals based on real-time flow
       - Predictive congestion management
       - Emergency vehicle prioritization
    
    2. Energy Optimization
       - Smart street lighting that adjusts based on time and activity
       - Building energy management integration
       - Renewable energy incorporation
    
    3. Public Safety Enhancement
       - Environmental monitoring (air quality, noise levels)
       - Pedestrian flow analysis
       - Emergency response optimization
    
    Timeline and Budget:
    The project is estimated to take 18 months with a budget of $4.2 million.
    Implementation will be phased, with traffic management as the first priority.
    
    Expected Benefits:
    - 30% reduction in traffic congestion
    - 25% decrease in energy consumption
    - 15% improvement in emergency response times
    - Enhanced quality of life for residents and visitors
    
    This proposal is submitted for consideration by the city planning committee.
    """
    
    # Analyze the sample text with both AI services
    analyze_with_both_services(sample_text)

if __name__ == "__main__":
    main()