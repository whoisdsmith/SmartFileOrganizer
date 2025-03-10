# AI Document Organizer - Quick Start Guide

This guide will help you quickly set up and start using the AI Document Organizer application.

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

   **Option 1: Using environment variables**

   ```bash
   # For Google Gemini API
   # On Windows
   set GOOGLE_API_KEY=your_api_key_here

   # On macOS/Linux
   export GOOGLE_API_KEY=your_api_key_here

   # OR for OpenAI API
   # On Windows
   set OPENAI_API_KEY=your_api_key_here

   # On macOS/Linux
   export OPENAI_API_KEY=your_api_key_here
   ```

   **Option 2: Using the application settings (recommended)**
   - Launch the application
   - Go to the Settings tab
   - Select the "AI Models" tab
   - Enter your API key in the appropriate field
   - Click "Save"

## Running the Application

Launch the application by running:

```bash
python main.py
```

The graphical user interface will appear.

## Basic Usage

1. **Selecting Source Directory**
   - Click the "Browse" button next to "Source Directory"
   - Navigate to and select the folder containing your documents

2. **Analyzing Documents**
   - Click "Analyze Documents" to begin the AI analysis process
   - Wait for the processing to complete (progress is shown in the status bar)
   - Review the analyzed documents in the table

3. **Viewing Document Details**
   - Select any document in the table to view its details
   - The right panel will show category, keywords, and summary information

4. **Organizing Documents**
   - Click "Organize Files" to create an organized structure
   - Select a target directory when prompted
   - The application will create category folders and organize your files

## Settings Customization

Access the Settings tab to customize:

### Processing Settings

- Batch size for analysis (lower values help avoid API rate limits)
- Batch delay between processing batches (higher values help avoid API rate limits)

### AI Models Settings

- Select AI service (Google Gemini or OpenAI)
- Enter API keys
- Choose specific AI models for each service

### Organization Rules

- Create category folders
- Generate content summaries
- Include metadata in separate files
- Copy files instead of moving them

## Choosing an AI Model

The application supports multiple AI models from both Google and OpenAI:

1. **Google Gemini Models**:
   - models/gemini-2.0-flash (Default)
   - models/gemini-1.5-flash
   - models/gemini-1.5-pro
   - And more...

2. **OpenAI Models**:
   - gpt-4o (Latest model)
   - gpt-4-turbo
   - gpt-3.5-turbo
   - And more...

To select a model:

1. Go to the Settings tab
2. Select the "AI Models" tab
3. Choose your preferred model from the dropdown list
4. Click "Set" to use the selected model

## Troubleshooting

- Ensure your API key is correctly set in the Settings tab or environment variables
- Check internet connectivity for AI analysis
- For large documents, increase batch size in settings
- If encountering rate limit errors, reduce batch size or increase batch delay

For more detailed information, refer to the full [User Guide](./README.md), [Developer Guide](./DEVELOPER_GUIDE.md), or [Alternative AI Models](./ALTERNATIVE_AI_MODELS.md) documentation.
