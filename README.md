![AI Document Organizer Banner](assets/banner.svg)

# AI Document Organizer

An intelligent document organization application powered by AI, supporting both Google Gemini and OpenAI models.

## Overview

The AI Document Organizer helps you automatically organize your documents by analyzing their content with advanced AI models. The application can process and categorize multiple file formats, creating a structured folder system with meaningful categories based on document content.

## Project Structure

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
│   ├── README.md             # User guide
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
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## Features

- **Smart Document Analysis**: Uses Google Gemini or OpenAI models to understand document content
- **Multiple AI Model Support**:
  - Google Gemini models (2.0 Flash, 1.5 Flash, 1.5 Pro, etc.)
  - OpenAI models (GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo, etc.)
- **In-App API Key Management**: Enter and save API keys directly in the settings
- **Model Selection**: Choose from available AI models for each service
- **Automatic Categorization**: Creates logical folder structure based on document topics and content
- **Multi-Format Support**: Works with various file types (CSV, Excel, HTML, Markdown, Text, Word)
- **Content Extraction**: Automatically extracts and analyzes text from all supported formats
- **Windows-Optimized**: Native Windows interface with proper file handling
- **Batch Processing**: Processes files in configurable batches to optimize performance
- **Rate Limiting Controls**: Configure batch size and delay to avoid API rate limits

## Requirements

- Windows 10/11
- Python 3.8 or higher
- API key for Google Gemini or OpenAI

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/ai-document-organizer.git
   cd ai-document-organizer
   ```

2. Install dependencies:

   ```bash
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

## Running the Application

```bash
python main.py
```

## Documentation

- [User Guide](docs/README.md)
- [Quick Start Guide](docs/QUICK_START_GUIDE.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [Alternative AI Models](docs/ALTERNATIVE_AI_MODELS.md)

## Packaging for Distribution

To create a standalone Windows executable and installer, see the [Packaging Guide](packaging/PACKAGING.md).

## License

MIT License - See [LICENSE.txt](docs/LICENSE.txt) for details.
