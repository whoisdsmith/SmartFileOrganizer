"""
Test script for the AI analyzer component of the Document Organizer application.
This verifies that the Google Gemini API integration is working correctly.
"""
import os
import sys
from ai_analyzer import AIAnalyzer

def test_ai_analyzer():
    print("Testing AI Analyzer with Gemini API...")
    analyzer = AIAnalyzer()
    
    # Test with a simple text document
    test_text = """
    Financial Report - Q1 2024

    Quarter 1 Financial Summary
    ---------------------------

    Revenue: $1.25M
    Expenses: $982K
    Profit: $268K

    Key Highlights:
    - 15% increase in revenue compared to Q1 2023
    - New customer acquisition up 22%
    - Operating expenses reduced by 7%
    - Launched 2 new product features
    """
    
    print("\nTesting text analysis...")
    result = analyzer.analyze_content(test_text, "Text")
    print("\nAnalysis result:")
    print(f"Category: {result.get('category', 'Not available')}")
    print(f"Keywords: {', '.join(result.get('keywords', []))}")
    print(f"Summary: {result.get('summary', 'Not available')}")
    
    # Test with a CSV-like content
    test_csv = """
    id,first_name,last_name,email,department,salary
    1,John,Smith,john.smith@company.com,Engineering,85000
    2,Sarah,Johnson,sarah.j@company.com,Marketing,75000
    3,Robert,Williams,rob.williams@company.com,Finance,95000
    4,Jennifer,Brown,jen.brown@company.com,Human Resources,72000
    5,Michael,Jones,michael.j@company.com,Engineering,90000
    """
    
    print("\nTesting CSV analysis...")
    result = analyzer.analyze_content(test_csv, "CSV")
    print("\nAnalysis result:")
    print(f"Category: {result.get('category', 'Not available')}")
    print(f"Keywords: {', '.join(result.get('keywords', []))}")
    print(f"Summary: {result.get('summary', 'Not available')}")
    
    print("\nAI Analyzer test completed successfully!")

if __name__ == "__main__":
    test_ai_analyzer()