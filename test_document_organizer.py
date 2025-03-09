"""
Test script for the Document Organizer application.
This tests the core functionality without requiring the GUI.
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
    
    # Step 2: Organize files
    print("\nStep 2: Organizing files...")
    organizer = FileOrganizer()
    result = organizer.organize_files(files, output_dir)
    
    print(f"\nOrganization results:")
    print(f"Successfully organized: {result['success']} files")
    print(f"Failed to organize: {result['failed']} files")
    
    if result['failed'] > 0:
        print(f"Failed files: {', '.join(result['failed_files'])}")
    
    # Step 3: Check the output directory structure
    print("\nStep 3: Checking output directory structure...")
    categories = []
    
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path):
            categories.append(item)
            files_in_category = os.listdir(item_path)
            print(f"Category: {item} - Contains {len(files_in_category)} files")
    
    print(f"\nCreated {len(categories)} categories: {', '.join(categories)}")
    print("\nTest completed successfully!")

if __name__ == "__main__":
    test_full_workflow()