# AI Document Organizer: Alternative AI Models

This document explains how to use different AI models with the AI Document Organizer application.

## Supported AI Services

The AI Document Organizer now supports two AI services:

1. **Google Gemini** (Default)
   - Uses Google's Gemini 2.0 Flash model
   - Provides advanced document analysis capabilities
   - Offers efficient processing with lower token usage

2. **OpenAI**
   - Uses OpenAI's gpt-4o model
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

### 2. Using the Settings Interface

1. Open the application
2. Go to the "Settings" tab
3. Find the "AI Service Configuration" section
4. Select your preferred AI service
5. Enter your API key
6. Click "Save Settings"

### 3. Programmatically

If you're extending the application, you can use the AIServiceFactory:

```python
from src.ai_service_factory import AIServiceFactory

# Create a Google Gemini analyzer
google_analyzer = AIServiceFactory.create_analyzer('google')

# Create an OpenAI analyzer
openai_analyzer = AIServiceFactory.create_analyzer('openai')

# Let the factory choose based on environment variables
default_analyzer = AIServiceFactory.create_analyzer()
```

## Comparing AI Services

### Google Gemini

- **Pros**:
  - Lower cost per token
  - Faster processing for large documents
  - Excellent at categorization tasks
  - Support for Gemini 2.0 Flash model

- **Use when**:
  - Processing large batches of documents
  - Working with technical or business-oriented content
  - Cost efficiency is important

### OpenAI (GPT-4o)

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
4. Copy the key and use it in the application

### OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Create or sign in to your OpenAI account
3. Navigate to API keys section
4. Create a new secret key
5. Copy the key and use it in the application

#### Setting up OpenAI API Key

##### Windows
```
setx OPENAI_API_KEY "your-openai-api-key-here"
```

##### macOS/Linux
```
export OPENAI_API_KEY="your-openai-api-key-here"
```
Add to your `~/.bashrc` or `~/.zshrc` file for persistence.

##### Verifying the API Key

Run the test script to verify your OpenAI API key is working correctly:
```
python test_api_keys.py
```

This will test both Google and OpenAI API keys and report their status.

## Troubleshooting

If you encounter issues with your AI service:

1. Verify your API key is correct and has not expired
2. Check your internet connection
3. Ensure your API account has sufficient credits
4. Try switching to the alternative AI service
5. Check the application logs for specific error messages
