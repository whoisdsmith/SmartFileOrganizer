# Dependencies for AI Document Organizer

This document lists the dependencies required for the AI Document Organizer application.

## Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| beautifulsoup4 | >=4.12.2 | HTML parsing |
| google-generativeai | >=0.3.1 | Google Gemini API client |
| markdown | >=3.4.3 | Markdown file parsing |
| openai | >=1.3.0 | OpenAI API integration |
| openpyxl | >=3.1.2 | Excel file handling |
| pandas | >=1.5.3 | Data manipulation for CSV and Excel |
| pillow | >=9.5.0 | Image processing for GUI |
| python-docx | >=0.8.11 | Word document parsing |
| python-dotenv | >=1.0.0 | Environment variable management |
| pywin32 | >=306 | Windows-specific functionality |
| requests | >=2.31.0 | HTTP requests for API calls |
| tqdm | >=4.66.1 | Progress bars for batch processing |

## Development & Packaging Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pyinstaller | >=5.13.0 | Creating standalone executables |
| cx_freeze | >=6.15.0 | Alternative executable creation |
| pytest | >=7.0.0 | Testing framework |
| black | >=23.0.0 | Code formatting |
| isort | >=5.12.0 | Import sorting |
| flake8 | >=6.0.0 | Code linting |

## Installation

All dependencies are listed in the `requirements.txt` file in the project root. To install:

```bash
pip install -r requirements.txt
```

For development dependencies:

```bash
pip install -r requirements.txt -e ".[dev,packaging]"
```

## Environment Variables

The application supports the following environment variables:

- `GOOGLE_API_KEY`: For Google Gemini API access
- `OPENAI_API_KEY`: For OpenAI API access

These can also be configured directly in the application settings.

## System Requirements

- Python 3.8 or higher
- Windows 10/11 (optimized for Windows environment)
- 4GB RAM minimum, 8GB recommended for large document sets
- 100MB free disk space for the application
