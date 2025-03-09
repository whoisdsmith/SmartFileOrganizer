"""
Test script for the AI analyzer component of the Document Organizer application.
This verifies that the Google Gemini API integration is working correctly and
tests the document relationship detection features.
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
    
    # Test document relationship detection
    print("\nTesting document relationship detection...")
    
    # Create a set of test documents
    test_documents = [
        {
            "filename": "Financial_Report_Q1_2024.txt",
            "path": "/documents/financial/Q1_2024.txt",
            "file_type": "Text",
            "category": "Financial Report",
            "theme": "Finance",
            "keywords": ["revenue", "financial", "quarterly", "profit", "expenses"],
            "summary": "Q1 2024 financial report showing $1.25M revenue, $982K expenses, and $268K profit with 15% YoY growth."
        },
        {
            "filename": "Budget_Planning_2024.txt",
            "path": "/documents/financial/budget_2024.txt",
            "file_type": "Text",
            "category": "Financial Planning",
            "theme": "Budget",
            "keywords": ["budget", "financial", "planning", "forecast", "expenses"],
            "summary": "2024 budget planning document outlining departmental budgets, investment plans, and expense forecasts."
        },
        {
            "filename": "Employee_Directory.csv",
            "path": "/documents/hr/employee_dir.csv",
            "file_type": "CSV",
            "category": "Human Resources",
            "theme": "Employees",
            "keywords": ["employees", "directory", "departments", "contact", "personnel"],
            "summary": "Company employee directory listing names, departments, emails, and salary information."
        },
        {
            "filename": "Q4_2023_Financial_Summary.txt",
            "path": "/documents/financial/Q4_2023.txt",
            "file_type": "Text",
            "category": "Financial Report",
            "theme": "Finance",
            "keywords": ["revenue", "financial", "quarterly", "profit", "summary"],
            "summary": "Q4 2023 financial summary showing end-of-year performance metrics and comparison to previous quarters."
        },
        {
            "filename": "Marketing_Strategy_2024.txt",
            "path": "/documents/marketing/strategy_2024.txt",
            "file_type": "Text",
            "category": "Marketing",
            "theme": "Strategy",
            "keywords": ["marketing", "strategy", "campaigns", "budget", "targets"],
            "summary": "2024 marketing strategy document outlining key campaigns, target demographics, and budget allocation."
        }
    ]
    
    # Test finding similar documents (should find financial documents related to Q1 report)
    target_doc = test_documents[0]  # Financial Report Q1 2024
    print(f"\nFinding documents similar to: {target_doc['filename']}")
    similar_docs = analyzer.find_similar_documents(target_doc, test_documents)
    
    print("\nSimilar documents:")
    for i, doc in enumerate(similar_docs):
        print(f"{i+1}. {doc.get('filename')} - Score: {doc.get('similarity_score')}")
        print(f"   Relationship: {doc.get('relationship_explanation', 'N/A')}")
    
    # Test finding related content with AI insights
    print("\nFinding related content with AI insights:")
    related_content = analyzer.find_related_content(target_doc, test_documents)
    
    print("\nRelated documents with context:")
    for i, doc in enumerate(related_content.get('related_documents', [])):
        print(f"{i+1}. {doc.get('filename')}")
        if 'relationship_type' in doc:
            print(f"   Type: {doc.get('relationship_type', 'N/A')}")
        print(f"   Strength: {doc.get('relationship_strength', 'N/A')}")
        print(f"   Explanation: {doc.get('relationship_explanation', 'N/A')}")
    
    print("\nAI Analyzer test completed successfully!")

if __name__ == "__main__":
    test_ai_analyzer()