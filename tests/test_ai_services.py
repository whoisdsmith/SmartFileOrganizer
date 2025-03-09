#!/usr/bin/env python3
"""
Test script to verify both Google Gemini and OpenAI services work correctly.
"""

import os
import sys
import logging
import json

# Add the parent directory to the path to import the src package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_service_factory import AIServiceFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gemini_service():
    """Test the Google Gemini AI service."""
    logger.info("Testing Google Gemini AI service...")
    
    # Create a Google Gemini analyzer
    analyzer = AIServiceFactory.create_analyzer('google')
    
    # Sample text for analysis
    sample_text = """
    Quarterly Financial Report - Q1 2025
    
    The company has reported a 15% increase in revenue compared to the same period last year.
    Operating expenses were reduced by 7% due to efficiency improvements and automation.
    Net profit margin improved from 12% to 14.5%.
    
    Key financial highlights:
    - Total revenue: $24.5 million
    - Operating expenses: $18.3 million
    - Net profit: $3.6 million
    
    The board has recommended a dividend of $0.25 per share for the quarter.
    """
    
    # Analyze the text
    try:
        result = analyzer.analyze_content(sample_text, "txt")
        logger.info(f"Gemini Analysis result: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"Error in Gemini analysis: {str(e)}")
        return False

def test_openai_service():
    """Test the OpenAI service."""
    logger.info("Testing OpenAI service...")
    
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set - skipping OpenAI test")
        return None
    
    # Create an OpenAI analyzer
    analyzer = AIServiceFactory.create_analyzer('openai')
    
    # Sample text for analysis
    sample_text = """
    Employee Performance Review - March 2025
    
    Employee: Jane Smith
    Department: Marketing
    Position: Senior Marketing Specialist
    
    Strengths:
    - Excellent communication and presentation skills
    - Strong analytical capabilities in market research
    - Consistently meets or exceeds targets
    
    Areas for improvement:
    - Time management on complex projects
    - Delegation of routine tasks
    
    Goals for next quarter:
    1. Lead the social media strategy redevelopment
    2. Complete advanced digital marketing certification
    3. Mentor junior team members in analytics
    
    Overall performance rating: 4.2/5.0
    """
    
    # Analyze the text
    try:
        result = analyzer.analyze_content(sample_text, "txt")
        logger.info(f"OpenAI Analysis result: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"Error in OpenAI analysis: {str(e)}")
        return False

def test_document_relationships():
    """Test document relationship detection with both AI services."""
    logger.info("Testing document relationship detection...")
    
    # Create a document list for testing relationships
    test_docs = [
        {
            "filename": "financial_report_q1.txt",
            "path": "/test/docs/financial_report_q1.txt",
            "category": "Finance",
            "keywords": ["quarterly", "finance", "revenue", "profit"],
            "summary": "Q1 2025 financial report showing 15% revenue increase and improved profit margins.",
            "theme": "Financial Performance"
        },
        {
            "filename": "budget_planning.txt",
            "path": "/test/docs/budget_planning.txt",
            "category": "Finance",
            "keywords": ["budget", "forecast", "planning", "expenses"],
            "summary": "Budget planning document for fiscal year 2025 with departmental allocations.",
            "theme": "Budget Planning"
        },
        {
            "filename": "marketing_strategy.txt",
            "path": "/test/docs/marketing_strategy.txt",
            "category": "Marketing",
            "keywords": ["marketing", "strategy", "campaign", "audience"],
            "summary": "2025 marketing strategy with focus on digital channels and audience segmentation.",
            "theme": "Marketing"
        },
        {
            "filename": "competitor_analysis.txt",
            "path": "/test/docs/competitor_analysis.txt",
            "category": "Research",
            "keywords": ["competitors", "market", "analysis", "comparison"],
            "summary": "Analysis of key competitors in the market with SWOT assessments.",
            "theme": "Market Analysis"
        }
    ]
    
    # Test with both services if OpenAI key is available
    services = ['google']
    if os.environ.get("OPENAI_API_KEY"):
        services.append('openai')
    
    success = True
    for service_name in services:
        try:
            logger.info(f"Testing relationships with {service_name} service...")
            analyzer = AIServiceFactory.create_analyzer(service_name)
            
            # Pick the first document as the target
            target_doc = test_docs[0]
            
            # Find similar documents
            similar_docs = analyzer.find_similar_documents(target_doc, test_docs)
            logger.info(f"{service_name} similar documents: {len(similar_docs)} found")
            
            # Find related content
            related_content = analyzer.find_related_content(target_doc, test_docs)
            logger.info(f"{service_name} related content: {len(related_content['related_documents'])} documents, relationship type: {related_content['relationship_type']}")
            
            # Print relationship details for the first related document
            if related_content['related_documents']:
                first_doc = related_content['related_documents'][0]
                logger.info(f"Relationship details for '{first_doc.get('filename')}': {first_doc.get('relationship_explanation', 'No explanation')} (strength: {first_doc.get('relationship_strength', 'unknown')})")
        
        except Exception as e:
            logger.error(f"Error testing relationships with {service_name}: {str(e)}")
            success = False
    
    return success

def main():
    """Run all tests."""
    logger.info("Testing AI Document Organizer AI services")
    logger.info("-" * 50)
    
    # Run tests
    gemini_result = test_gemini_service()
    logger.info("-" * 50)
    
    openai_result = test_openai_service()
    logger.info("-" * 50)
    
    relationship_result = test_document_relationships()
    logger.info("-" * 50)
    
    # Report results
    logger.info("Test Results:")
    logger.info(f"- Google Gemini Service: {'Passed' if gemini_result else 'Failed'}")
    if openai_result is None:
        logger.info(f"- OpenAI Service: Skipped (API key not set)")
    else:
        logger.info(f"- OpenAI Service: {'Passed' if openai_result else 'Failed'}")
    logger.info(f"- Document Relationships: {'Passed' if relationship_result else 'Failed'}")
    
    # Overall result
    if gemini_result and (openai_result is None or openai_result) and relationship_result:
        logger.info("All tests passed!")
        return 0
    else:
        logger.info("Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())