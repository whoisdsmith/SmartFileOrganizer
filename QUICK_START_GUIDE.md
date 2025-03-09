# AI Document Organizer - Quick Start Guide

This guide provides simple step-by-step instructions to get the AI Document Organizer up and running quickly.

## Setup

### 1. Install Python

If you don't have Python installed:
- Download and install Python 3.8 or higher from [python.org](https://www.python.org/downloads/)
- During installation, check "Add Python to PATH"

### 2. Install Required Libraries

Open Command Prompt (Windows) or Terminal (macOS/Linux) and run:

```
pip install beautifulsoup4 chardet python-docx google-generativeai numpy openai openpyxl pandas
```

### 3. Get a Google API Key

1. Go to the [Google AI Studio](https://makersuite.google.com/)
2. Create or sign in to your Google account
3. Follow the prompts to create an API key
4. Save your API key in a secure location

### 4. Set Up Your API Key

#### Windows
1. Open Command Prompt as Administrator
2. Run: `setx GOOGLE_API_KEY "your-api-key-here"` (replace with your actual API key)
3. Close and reopen Command Prompt

#### macOS/Linux
1. Open Terminal
2. Run: `export GOOGLE_API_KEY="your-api-key-here"` (replace with your actual API key)
3. To make it permanent, add this line to your `~/.bashrc` or `~/.zshrc` file

## Running the Application

1. Download the AI Document Organizer application
2. Open Command Prompt/Terminal and navigate to the application folder
3. Run: `python main.py`
4. The application window will open

## Organizing Your Documents

### Step 1: Select Source Folder
1. Click the "Browse" button next to "Source Directory"
2. Navigate to the folder containing your documents
3. Click "Select Folder"

### Step 2: Select Target Folder
1. Click the "Browse" button next to "Target Directory"
2. Navigate to where you want to save organized documents
3. Click "Select Folder"

### Step 3: Scan Documents
1. Click the "Scan" button
2. Wait for scanning and AI analysis to complete
3. Review the list of found documents and their categories

### Step 4: Organize Documents
1. Click the "Organize" button
2. Wait for files to be organized
3. A confirmation message will appear when complete

### Step 5: View Results
1. Navigate to your target folder
2. You'll see documents organized into category folders
3. Each document has an accompanying .meta.txt file with AI analysis

## Supported File Formats

The application can analyze and organize:
- Text files (.txt)
- CSV files (.csv)
- Excel files (.xlsx)
- HTML files (.html)
- Markdown files (.md)
- Word documents (.docx)

## Troubleshooting

### API Key Issues
- Make sure you've correctly set up the GOOGLE_API_KEY environment variable
- Check that your API key is active and has access to Gemini models

### Application Won't Start
- Verify Python is correctly installed
- Ensure all required libraries are installed
- Try running from the command line to see error messages

### No Categories Generated
- Ensure your Google API key has access to the Gemini models
- Check that document files are not corrupted or empty
- Try with simpler test documents first

## Getting Help

For more detailed information:
- See the full README.md file
- Check the DEVELOPER_GUIDE.md for technical details
- Run test scripts to verify functionality:
  - `python test_document_organizer.py`