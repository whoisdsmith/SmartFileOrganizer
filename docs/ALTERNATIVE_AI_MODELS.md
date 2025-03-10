# AI Document Organizer: Alternative AI Models

This document explains how to use different AI models with the AI Document Organizer application.

## Supported AI Services

The AI Document Organizer now supports two AI services:

1. **Google Gemini** (Default)
   - Supports multiple Gemini models (2.0 Flash, 1.5 Flash, 1.5 Pro, etc.)
   - Provides advanced document analysis capabilities
   - Offers efficient processing with lower token usage

2. **OpenAI**
   - Supports multiple models (GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo, etc.)
   - May provide different analysis results for certain document types
   - Requires an OpenAI API key

## Configuring Your AI Service

You can choose which AI service to use in several ways:

### 1. Using Environment Variables

Set the following environment variables:

```
AI_SERVICE_TYPE=google    # or 'openai'
GOOGLE_API_KEY=your_google_api_key  # if using 'google'
OPENAI_API_KEY=your_openai_api_key  # if using 'openai'
```

### 2. Using the Settings Interface (Recommended)

1. Open the application
2. Go to the "Settings" tab
3. Select the "AI Models" tab
4. In the "AI Service Selection" section, choose your preferred service (Google or OpenAI)
5. Enter your API key in the appropriate field
6. Click "Save" to store your API key
7. Select your preferred model from the dropdown list
8. Click "Set" to use the selected model

### 3. Programmatically

If you're extending the application, you can use the AIServiceFactory:

```python
from src.ai_service_factory import AIServiceFactory
from src.settings_manager import SettingsManager

# Initialize settings
settings_manager = SettingsManager()

# Create an AI service using the factory
ai_service = AIServiceFactory.create_ai_service(settings_manager)

# Use the service
analysis_result = ai_service.analyze_document("Sample text to analyze")
```

## Available Models

### Google Gemini Models

The application automatically detects available Gemini models from your API account. Common models include:

- **models/gemini-2.0-flash** (Default) - Latest and most efficient model
- **models/gemini-1.5-flash** - Fast, efficient model with good performance
- **models/gemini-1.5-pro** - More powerful model for complex analysis
- **models/gemini-1.0-pro** - Original Gemini model

### OpenAI Models

The application supports the following OpenAI models:

- **gpt-4o** - Latest and most powerful model (May 2024)
- **gpt-4-turbo** - Fast, powerful model
- **gpt-4-turbo-preview** - Preview version
- **gpt-4** - Standard GPT-4 model
- **gpt-3.5-turbo** - Faster, cheaper model
- **gpt-3.5-turbo-16k** - Extended context model

## Comparing AI Services

### Google Gemini

- **Pros**:
  - Lower cost per token
  - Faster processing for large documents
  - Excellent at categorization tasks
  - Support for multiple Gemini models

- **Use when**:
  - Processing large batches of documents
  - Working with technical or business-oriented content
  - Cost efficiency is important

### OpenAI (GPT-4o and others)

- **Pros**:
  - May provide more nuanced relationship detection
  - Better at extracting complex themes
  - Strong performance with creative content
  - Advanced zero-shot understanding capabilities

- **Use when**:
  - Working with creative or literary documents
  - Relationship detection accuracy is critical
  - Advanced summary quality is needed

## Document Relationship Detection

Both AI services implement our four relationship types:

1. **Prerequisite** - Content that should be understood before the main document
2. **Sequential** - Content that follows as the next step after the main document
3. **Contextual** - Content that provides supporting information for the main document
4. **Extension** - Content that builds upon or extends the concepts in the main document

However, you may notice slight differences in how each AI service categorizes relationships between documents.

## Fallback Behavior

If the selected AI service is not available (e.g., missing API key), the application will:

1. Attempt to use the other service if its API key is available
2. Display a warning if no valid API keys are found
3. Still function with basic categorization, but with reduced accuracy

## Getting API Keys

### Google Gemini API Key

1. Visit [Google AI Studio](https://ai.google.dev/)
2. Create or sign in to your Google account
3. Create a new API key
4. Copy the key and use it in the application's Settings tab

### OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Create or sign in to your OpenAI account
3. Navigate to API keys section
4. Create a new secret key
5. Copy the key and use it in the application's Settings tab

## Rate Limiting and API Quotas

Both Google and OpenAI have rate limits on their APIs. The application includes features to help manage these limits:

- **Configurable Batch Size**: Reduce the number of files processed in each batch (default: 5)
- **Batch Delay**: Add a delay between processing batches (default: 10 seconds)
- **Exponential Backoff**: Automatically retry failed API calls with increasing delays
- **Error Handling**: Gracefully handle rate limit errors and continue processing

These settings can be adjusted in the "Processing" tab of the Settings page.

## Troubleshooting

If you encounter issues with your AI service:

1. Verify your API key is correct and has not expired
2. Check your internet connection
3. Ensure your API account has sufficient credits
4. Try switching to the alternative AI service
5. Check the application logs for specific error messages
6. Reduce batch size or increase batch delay if encountering rate limit errors
