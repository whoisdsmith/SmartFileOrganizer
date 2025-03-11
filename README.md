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
│   ├── media_analyzer.py     # Audio/video file analysis
│   ├── transcription_service.py # Audio transcription service
│   ├── cloud_integration.py  # Cloud storage integration
│   ├── organization_scheme.py # Organization scheme management
│   ├── templates/            # Organization templates
│   └── utils.py             # Helper utilities
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
│   └── build_exe.py         # Build script
├── tests/                    # Test files
├── main.py                   # Main entry point
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## Features

- **Smart Document Analysis**: Uses Google Gemini or OpenAI models to understand document content
- **Multiple AI Model Support**:
  - Google Gemini models (2.0 Flash, 1.5 Flash, 1.5 Pro, etc.)
  - OpenAI models (GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, etc.)
- **In-App API Key Management**: Enter and save API keys directly in the settings
- **Model Selection**: Choose from available AI models for each service
- **Automatic Categorization**: Creates logical folder structure based on document topics and content
- **Multi-Format Support**: Works with various file types:
  - Documents: CSV, Excel, HTML, Markdown, Text, Word
  - Images: JPG, PNG, GIF, BMP, TIFF, WebP
  - Audio: MP3, WAV, FLAC, AAC, OGG, M4A
  - Video: MP4, AVI, MKV, MOV, WMV, WebM, FLV
- **Content Extraction**: Automatically extracts and analyzes text from all supported formats
- **Media Analysis**:
  - Audio file analysis (duration, bitrate, channels, etc.)
  - Video file analysis (resolution, frame rate, codecs, etc.)
  - Audio waveform generation
  - Video thumbnail generation
  - Audio transcription with multiple providers
- **Cloud Storage Integration**:
  - Support for Google Drive, OneDrive, and Dropbox
  - Bidirectional synchronization
  - Conflict resolution
  - Selective sync by file type
  - Bandwidth control
- **Organization Schemes**:
  - Import/export organization rules
  - Predefined templates for common use cases
  - Custom rule creation
  - Rule conflict detection
  - Scheme merging and validation
- **Windows-Optimized**: Native Windows interface with proper file handling
- **Batch Processing**: Processes files in configurable batches to optimize performance
- **Rate Limiting Controls**: Configure batch size and delay to avoid API rate limits

## Requirements

- Windows 10/11
- Python 3.8 or higher
- API key for Google Gemini or OpenAI
- FFmpeg for audio/video processing
- Optional: Cloud storage provider credentials

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

3. Install FFmpeg:
   - Download from [FFmpeg official website](https://ffmpeg.org/download.html)
   - Add FFmpeg to your system PATH

4. Set up your API keys:
   - In the application settings (recommended)
   - Or as environment variables:

     ```bash
     # For Google Gemini API
     set GOOGLE_API_KEY=your_api_key_here

     # OR for OpenAI API
     set OPENAI_API_KEY=your_api_key_here

     # For cloud storage (optional)
     set GOOGLE_DRIVE_CREDENTIALS=path_to_credentials.json
     set ONEDRIVE_CLIENT_ID=your_client_id
     set ONEDRIVE_CLIENT_SECRET=your_client_secret
     set DROPBOX_APP_KEY=your_app_key
     set DROPBOX_APP_SECRET=your_app_secret
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

## Organization Templates

The application comes with predefined organization templates:

- **Media Organization**: Rules for organizing audio and video files by type, metadata, resolution, and duration
- **Cloud Storage Sync**: Configuration for synchronizing files with cloud storage providers
- **Custom Templates**: Create and share your own organization schemes

## Cloud Storage Support

Supported cloud storage providers:

- **Google Drive**: Full integration with Google Drive API
- **OneDrive**: Integration with Microsoft Graph API
- **Dropbox**: Integration with Dropbox API

Features:

- Bidirectional synchronization
- Selective sync by file type
- Conflict resolution
- Version control
- Bandwidth management
- Progress tracking
- Error handling and retry mechanisms

## Packaging for Distribution

To create a standalone Windows executable and installer, see the [Packaging Guide](packaging/PACKAGING.md).

## License

MIT License - See [LICENSE.txt](docs/LICENSE.txt) for details.
