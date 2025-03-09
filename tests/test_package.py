#!/usr/bin/env python3
"""
Test script to verify the package structure is working correctly.
"""

import os
import sys
import logging

# Add the parent directory to the path to import the src package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test importing all modules from the package."""
    print("Testing package imports...")
    
    # Try to import all modules
    try:
        from src.ai_analyzer import AIAnalyzer
        from src.file_analyzer import FileAnalyzer
        from src.file_organizer import FileOrganizer
        from src.settings_manager import SettingsManager
        from src.utils import get_readable_size, sanitize_filename
        from src.gui import DocumentOrganizerApp
        
        print("✓ All core modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Error importing modules: {str(e)}")
        return False

def test_version():
    """Test accessing the package version."""
    print("Testing package version...")
    
    try:
        import src
        version = src.__version__
        print(f"✓ Package version: {version}")
        return True
    except (ImportError, AttributeError) as e:
        print(f"✗ Error accessing package version: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("Testing AI Document Organizer package structure")
    print("-" * 50)
    
    success = all([
        test_imports(),
        test_version(),
    ])
    
    print("-" * 50)
    if success:
        print("All package structure tests passed!")
        return 0
    else:
        print("Some package structure tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())