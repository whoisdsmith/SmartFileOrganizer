"""
Test script for the Document Organizer application.
This tests the core functionality without requiring the GUI, including the
new document relationship detection features.
"""
import os
import shutil
from pathlib import Path

from file_analyzer import FileAnalyzer
from file_organizer import FileOrganizer
from ai_analyzer import AIAnalyzer

def test_full_workflow():
    """Test the complete document organizing workflow"""
    print("Testing Document Organizer full workflow")
    
    # Define test directories
    test_dir = "./test_files"
    output_dir = "./test_output"
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        # Clean output directory
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    
    # Create instances of the required classes
    analyzer = FileAnalyzer()
    ai_analyzer = AIAnalyzer()
    
    # Step 1: Scan files
    print("\nStep 1: Scanning files in test directory...")
    files = analyzer.scan_directory(test_dir)
    print(f"Found {len(files)} files.")
    
    # Print basic details about each file
    for i, file in enumerate(files):
        print(f"\nFile {i+1}: {file['filename']}")
        print(f"Type: {file['file_type']}")
        print(f"Category: {file.get('category', 'Unknown')}")
        print(f"Keywords: {', '.join(file.get('keywords', ['None']))}")
        print(f"Summary: {file.get('summary', 'No summary available')[:100]}...")
    
    # Step 2: Find document relationships
    print("\nStep 2: Finding document relationships...")
    for i, file in enumerate(files):
        if i == 0:  # Test with the first file as target
            print(f"\nTesting document relationships for: {file['filename']}")
            
            # Find similar documents using keyword and metadata matching
            similar_docs = ai_analyzer.find_similar_documents(file, files)
            print(f"\nFound {len(similar_docs)} similar documents:")
            for j, similar in enumerate(similar_docs):
                print(f"  {j+1}. {similar['filename']} - Score: {similar['similarity_score']}")
                print(f"     Explanation: {similar.get('relationship_explanation', 'N/A')}")
            
            # Find related documents using deep content analysis
            print("\nFinding contextually related documents...")
            related_content = ai_analyzer.find_related_content(file, files)
            related_docs = related_content.get('related_documents', [])
            print(f"Found {len(related_docs)} related documents:")
            for j, related in enumerate(related_docs):
                print(f"  {j+1}. {related['filename']}")
                if 'relationship_type' in related:
                    print(f"     Type: {related.get('relationship_type', 'N/A')}")
                print(f"     Strength: {related.get('relationship_strength', 'N/A')}")
                print(f"     Explanation: {related.get('relationship_explanation', 'N/A')}")
            break
    
    # Step 3: Organize files
    print("\nStep 3: Organizing files...")
    organizer = FileOrganizer()
    # Enable all organization options
    organization_options = {
        "create_category_folders": True,
        "generate_summaries": True,
        "include_metadata": True,
        "copy_instead_of_move": True
    }
    result = organizer.organize_files(files, output_dir, options=organization_options)
    
    print(f"\nOrganization results:")
    print(f"Successfully organized: {result['success']} files")
    print(f"Failed to organize: {result['failed']} files")
    
    if result['failed'] > 0:
        print(f"Failed files: {', '.join(result['failed_files'])}")
    
    # Step 4: Check the output directory structure
    print("\nStep 4: Checking output directory structure...")
    categories = []
    
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path):
            categories.append(item)
            files_in_category = os.listdir(item_path)
            print(f"Category: {item} - Contains {len(files_in_category)} files")
            
            # Check for metadata and summary files
            meta_files = [f for f in files_in_category if f.endswith('.meta.txt')]
            summary_files = [f for f in files_in_category if f.endswith('_summary.txt')]
            print(f"  Found {len(meta_files)} metadata files and {len(summary_files)} summary files")
            
            # Check the first metadata file for relationship information
            if meta_files:
                first_meta = os.path.join(item_path, meta_files[0])
                with open(first_meta, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "Related Documents:" in content:
                        print("  Metadata files include document relationship information")
    
    # Step 5: Generate a folder report
    print("\nStep 5: Generating folder report...")
    report_path = organizer.generate_folder_report(output_dir, include_summaries=True)
    
    if report_path and os.path.exists(report_path):
        print(f"Successfully generated folder report at: {report_path}")
        
        # Check if the report includes document relationships
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
            if "Document Relationships" in report_content:
                print("Folder report includes document relationship analysis")
    else:
        print("Failed to generate folder report")
    
    print(f"\nCreated {len(categories)} categories: {', '.join(categories)}")
    print("\nTest completed successfully!")

def test_document_relationships():
    """Test just the document relationship features with sample data"""
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
    # Run both tests
    test_full_workflow()
    print("\n" + "="*50 + "\n")
    test_document_relationships()