"""
Test script for the document relationship detection features.
"""
from ai_analyzer import AIAnalyzer

def test_document_relationships():
    """Test the document relationship features with sample data"""
    print("Testing document relationship detection features")
    
    # Create a test set of documents with varying relationships
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
    
    # Initialize AI analyzer
    ai_analyzer = AIAnalyzer()
    
    # Test document similarity detection
    print("\nTesting document similarity detection:")
    target_doc = test_documents[0]  # Financial Report Q1 2024
    print(f"Target document: {target_doc['filename']}")
    
    # Find similar documents using keyword and metadata matching
    similar_docs = ai_analyzer.find_similar_documents(target_doc, test_documents)
    print(f"\nFound {len(similar_docs)} similar documents:")
    for i, doc in enumerate(similar_docs):
        print(f"{i+1}. {doc['filename']} - Score: {doc['similarity_score']}")
        print(f"   Relationship: {doc.get('relationship_explanation', 'N/A')}")
        print(f"   Strength: {doc.get('relationship_strength', 'N/A')}")
    
    # Test contextual relationships using AI
    print("\nTesting contextual relationship detection:")
    related_content = ai_analyzer.find_related_content(target_doc, test_documents)
    related_docs = related_content.get('related_documents', [])
    
    print(f"Relationship type: {related_content.get('relationship_type', 'N/A')}")
    print(f"Overall strength: {related_content.get('relationship_strength', 'N/A')}")
    print(f"\nFound {len(related_docs)} related documents:")
    
    for i, doc in enumerate(related_docs):
        print(f"{i+1}. {doc['filename']}")
        if 'relationship_type' in doc:
            print(f"   Type: {doc.get('relationship_type', 'N/A')}")
        print(f"   Strength: {doc.get('relationship_strength', 'N/A')}")
        print(f"   Explanation: {doc.get('relationship_explanation', 'N/A')}")
    
    print("\nDocument relationship testing completed successfully!")

if __name__ == "__main__":
    test_document_relationships()