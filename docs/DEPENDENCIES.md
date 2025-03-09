# Dependencies for AI Document Organizer

This document lists the dependencies required for the AI Document Organizer application.

## Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| beautifulsoup4 | >=4.11.1 | HTML parsing |
| chardet | >=4.0.0 | Character encoding detection |
| google-generativeai | >=0.3.0 | Google Gemini API client |
| numpy | >=1.22.0 | Numerical operations |
| openai | >=1.0.0 | Optional OpenAI integration |
| openpyxl | >=3.0.9 | Excel file handling |
| pandas | >=1.4.0 | Data manipulation for CSV and Excel |
| python-docx | >=0.8.11 | Word document parsing |

## Installation

```bash
pip install beautifulsoup4 chardet google-generativeai numpy openai openpyxl pandas python-docx
```

## Environment Variables

The application requires the following environment variables:

- `GOOGLE_API_KEY`: Required for Google Gemini API access
- `OPENAI_API_KEY`: Optional, for OpenAI integration if implemented

## System Requirements

- Python 3.8 or higher
- Windows 10/11 (optimized for Windows environment)
- 4GB RAM minimum, 8GB recommended for large document sets
- 100MB free disk space for the application