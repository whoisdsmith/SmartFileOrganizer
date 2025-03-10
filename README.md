# AI Document Organizer

An intelligent document organization application powered by Google Gemini Flash 2.0 AI.

This application automatically analyzes, categorizes, and organizes various document types
based on their content, with advanced document relationship detection capabilities.

## Documentation

Detailed documentation can be found in the [docs](./docs) directory:

- [User Guide](docs/README.md)
- [Quick Start Guide](docs/QUICK_START_GUIDE.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [Alternative AI Models](docs/ALTERNATIVE_AI_MODELS.md)

## Features

- Automatic document categorization using AI
- Intelligent document relationship detection
- Support for multiple file formats (CSV, Excel, HTML, Markdown, Text, Word)
- Content summarization and keyword extraction
- Windows-optimized user interface
- Batch processing for large document sets
- Smart rate limiting to prevent API quota errors
- Configurable batch size and delay settings

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-document-organizer.git

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

```bash
python main.py
```

## API Rate Limiting

When processing large numbers of documents, the application may encounter API rate limits from Google Gemini. The application includes the following features to handle this:

- **Configurable Batch Size**: Reduce the number of files processed in each batch (default: 5)
- **Batch Delay**: Add a delay between processing batches (default: 10 seconds)
- **Exponential Backoff**: Automatically retry failed API calls with increasing delays
- **Error Handling**: Gracefully handle rate limit errors and continue processing
- **Conservative Rate Limits**: Default settings are conservative to prevent quota errors

These settings can be adjusted in the application's Settings tab.

## API Keys

To use the AI features, you need to set up your API keys:

1. Get a Google Gemini API key from [Google AI Studio](https://ai.google.dev/)
2. Set the environment variable `GOOGLE_API_KEY` with your API key

Alternatively, you can use OpenAI by setting the `OPENAI_API_KEY` environment variable.
