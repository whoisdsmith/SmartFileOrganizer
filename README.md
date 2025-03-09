# AI Document Organizer

A Windows desktop application that uses Google's Gemini 2.0 Flash AI to automatically analyze and intelligently organize various document types.

## Overview

The AI Document Organizer helps you automatically organize your documents by analyzing their content with Google's advanced Gemini AI. The application can process and categorize multiple file formats, creating a structured folder system with meaningful categories based on document content.

## Features

- **Smart Document Analysis**: Uses Google Gemini 2.0 Flash AI to understand document content
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

## Requirements

- Windows 10/11
- Python 3.8 or higher
- Google API key with access to Gemini models

## Installation

1. Clone or download this repository
2. Install required dependencies:
   ```
   pip install beautifulsoup4 chardet python-docx google-generativeai numpy openai openpyxl pandas
   ```
3. Set up your Google API key as an environment variable:
   - Open Command Prompt as Administrator
   - Run: `setx GOOGLE_API_KEY AIzaSyAndYCK_XqP78lnjvVs4o8bFLso_Ar0J_Q` (replace with your actual API key)
   - Restart Command Prompt for the changes to take effect

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

## Advanced Usage

### Testing the System

To verify system functionality without using the GUI:

```
python test_document_organizer.py
```

This will:
1. Process sample files from the test_files directory
2. Generate AI analysis for each file
3. Organize them into the test_output directory
4. Create appropriate category folders and metadata files

### Checking API Connectivity

To verify your Gemini API connection is working properly:

```
python test_ai_analyzer.py
```

## Troubleshooting

- **API Key Issues**: Make sure your GOOGLE_API_KEY environment variable is correctly set
- **File Access Errors**: Ensure you have proper permissions to read source files and write to target directory
- **Model Availability**: The application will attempt to use the most suitable Gemini model available to your API key
- **Large Files**: Very large files may be truncated during analysis to meet API limitations

## Technical Details

The application consists of several key components:

- **GUI Module**: Creates and manages the application interface
- **File Parser**: Extracts text content from various file formats
- **AI Analyzer**: Processes document content using Google Gemini API
- **File Organizer**: Creates categorized folder structure based on analysis

Each document is analyzed to determine:
- The most appropriate category for organization
- Keywords representing document topics
- A concise summary of document content

## Metadata Format

For each processed file, a metadata (.meta.txt) file is created containing:

```
Filename: [original filename]
Original Path: [source path]
Type: [file type]
Size: [file size]
Category: [AI-determined category]
Keywords: [comma-separated keywords]

Summary:
[AI-generated summary of document content]
```

## License

[Include appropriate license information here]

## Credits

This application uses Google's Gemini 2.0 Flash AI technology for document analysis.