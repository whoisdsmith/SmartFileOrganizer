# AI Document Organizer

A Windows desktop application that uses AI to automatically analyze and intelligently organize various document types, supporting both Google Gemini and OpenAI models.

## Overview

The AI Document Organizer helps you automatically organize your documents by analyzing their content with advanced AI models. The application can process and categorize multiple file formats, creating a structured folder system with meaningful categories based on document content.

## Features

- **Smart Document Analysis**: Uses Google Gemini or OpenAI models to understand document content
- **Multiple AI Model Support**:
  - Google Gemini models (2.0 Flash, 1.5 Flash, 1.5 Pro, etc.)
  - OpenAI models (GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo, etc.)
- **In-App API Key Management**: Enter and save API keys directly in the settings
- **Model Selection**: Choose from available AI models for each service
- **Automatic Categorization**: Creates logical folder structure based on document topics and content
- **Multi-Format Support**: Works with various file types:
  - CSV files
  - Excel spreadsheets (XLSX)
  - HTML documents
  - Markdown files (MD)
  - Plain text files (TXT)
  - Word documents (DOCX)
- **Content Extraction**: Automatically extracts and analyzes text from all supported formats
- **Windows-Optimized**: Native Windows interface with proper file handling
- **Detailed Analysis**: Generates metadata files with AI insights for each processed document
- **Content Summaries**: Creates separate summary files with AI-generated content overviews
- **Customizable Organization**: Configure how files are organized with flexible rules:
  - Enable/disable category folder creation
  - Generate standalone summary files for each document
  - Include or exclude metadata files
  - Copy files instead of moving them
- **Folder Content Reports**: Generate summary reports of organized folder contents
- **Advanced Document Relationship Detection**: Identifies relationships between documents using AI-powered analysis:
  - **Keyword-Based Similarity**: Detects shared topics and themes across documents
  - **Category and Theme Analysis**: Groups documents with related classifications
  - **Contextual Relationships**: Discovers deeper connections like prerequisite, sequential, and complementary relationships
  - **Relationship Explanations**: Provides detailed explanations of how documents relate to each other
  - **Relationship Strength Scoring**: Quantifies relationship significance (high, medium, low)
- **Context-Aware Suggestions**: Receive intelligent file relationship suggestions when viewing any document
- **Content Relationship Visualization**: Enhanced visualization of document relationships in reports and metadata
- **Batch Processing**: Processes files in configurable batches to optimize performance
- **Rate Limiting Controls**: Configure batch size and delay to avoid API rate limits
- **Customizable UI**: Choose from multiple themes to match your Windows experience
- **Persistent Settings**: Save your preferred organization rules, batch sizes, and directory locations

## Requirements

- Windows 10/11
- Python 3.8 or higher
- API key for Google Gemini or OpenAI

## Installation

1. Clone or download this repository
2. Install required dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Set up your API key:
   - In the application settings (recommended)
   - Or as an environment variable:

     ```bash
     # For Google Gemini API
     set GOOGLE_API_KEY=your_api_key_here

     # OR for OpenAI API
     set OPENAI_API_KEY=your_api_key_here
     ```

## Quick Start

1. Run the application:

   ```
   python main.py
   ```

2. Using the interface:
   - Click "Browse" to select a source directory containing documents
   - Click "Browse" to select a target directory for organized documents
   - Click "Scan" to analyze documents in the source directory
   - Review the analysis results in the file list
   - Click "Organize" to sort the documents into categorized folders

## User Guide

### Main Interface

The application window consists of several sections:

- **Source Directory**: Select the folder containing documents to be analyzed
- **Target Directory**: Select the destination folder for organized documents
- **File List**: Displays analyzed documents with their detected categories
- **Details Panel**: Shows AI analysis details for the selected document
- **Search Box**: Filter documents by filename or content
- **Control Buttons**: Scan, Organize, and other action buttons
- **Settings Tab**: Configure application preferences and appearance

### Step-By-Step Usage

1. **Select Source Directory**:
   - Click the "Browse" button next to "Source Directory"
   - Navigate to and select the folder containing your documents
   - Click "Select Folder"

2. **Select Target Directory**:
   - Click the "Browse" button next to "Target Directory"
   - Navigate to and select the destination folder for organized documents
   - Click "Select Folder"

3. **Scan Documents**:
   - Click the "Scan" button
   - Wait for the analysis to complete
   - Review the document list showing detected categories

4. **Review Analysis Results**:
   - Click on any document in the list to see detailed analysis
   - The details panel will show:
     - Document category
     - Keywords
     - Content summary
     - File metadata

5. **Organize Documents**:
   - Click the "Organize" button
   - Documents will be copied to the target directory
   - Files will be organized into subfolders named by their categories
   - Each document will have an accompanying .meta.txt file with AI analysis

### Search and Filter

- Use the search box to filter documents by filename or content
- Results update as you type
- Clear the search box to show all documents again

### Application Settings

The Settings tab provides various customization options:

1. **Batch Processing**:
   - Adjust the batch size to control how many files are processed simultaneously
   - Smaller batch sizes use less memory but may take longer
   - Larger batch sizes may be faster but require more system resources
   - Click "Save as Default" to store your preferred batch size for future sessions

2. **Directory Defaults**:
   - Set your commonly used source and target directories as defaults
   - Click "Use Current" to save the currently selected directories
   - These saved locations will be pre-populated when you restart the application

3. **Organization Rules**:
   - **Create Category Folders**: Toggle creation of categorized folder structure
   - **Generate Content Summaries**: Enable/disable creation of standalone summary files
   - **Include Metadata**: Control whether metadata files are generated with AI analysis
   - **Copy Instead of Move**: Choose between copying or moving files during organization
   - All settings are automatically saved when changed

4. **Interface Theme**:
   - Choose from available visual themes to customize the application appearance
   - The theme selector shows all available themes for your system
   - Click "Apply Theme" to switch to the selected theme immediately

## Advanced Usage

### Testing the System

To verify system functionality without using the GUI:

```
python -m tests.test_document_organizer
```

This will:

1. Process sample files from the tests/test_files directory
2. Generate AI analysis for each file
3. Organize them into the tests/test_output directory
4. Create appropriate category folders and metadata files

### Checking API Connectivity

To verify your Gemini API connection is working properly:

```
python -m tests.test_ai_services
```

### Project Structure

The project follows a clean, organized structure:

```
AI-Document-Organizer/
├── src/                      # All source code
│   ├── ai_analyzer.py        # Google Gemini AI integration
│   ├── openai_analyzer.py    # OpenAI integration
│   ├── ai_service_factory.py # Factory for creating AI services
│   ├── file_analyzer.py      # Document scanning and analysis
│   ├── file_organizer.py     # Document organization
│   ├── file_parser.py        # Content extraction from files
│   ├── gui.py                # User interface
│   ├── settings_manager.py   # Application settings
│   └── utils.py              # Helper utilities
├── docs/                     # Documentation
│   ├── README.md             # User guide (this file)
│   ├── QUICK_START_GUIDE.md  # Quick start guide
│   ├── DEVELOPER_GUIDE.md    # Developer documentation
│   └── ALTERNATIVE_AI_MODELS.md # AI model information
├── assets/                   # Application assets
│   └── generated-icon.png    # Application icon
├── packaging/                # Packaging-related files
│   ├── ai_document_organizer.spec # PyInstaller specification
│   ├── installer.nsi         # NSIS installer script
│   └── build_exe.py          # Build script
├── tests/                    # Test files
├── main.py                   # Main entry point
└── requirements.txt          # Dependencies
```

## Packaging for Distribution

To create a standalone Windows executable and installer, see the [Packaging Guide](../packaging/PACKAGING.md).
