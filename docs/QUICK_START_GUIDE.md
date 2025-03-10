# AI Document Organizer - Quick Start Guide

This guide will help you quickly set up and start using the AI Document Organizer application.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/ai-document-organizer.git
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Google Gemini API key:
   - Create or use an existing Google Cloud account
   - Enable the Gemini API
   - Create an API key
   - Add the key to your environment variables:

     ```bash
     # On Windows
     set GOOGLE_API_KEY=your_api_key_here

     # On macOS/Linux
     export GOOGLE_API_KEY=your_api_key_here
     ```

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

- Default batch size for analysis
- Application theme
- Organization rules (create folders, generate summaries, etc.)

## Troubleshooting

- Ensure your API key is correctly set in environment variables
- Check internet connectivity for AI analysis
- For large documents, increase batch size in settings

For more detailed information, refer to the full [User Guide](./README.md) or [Developer Guide](./DEVELOPER_GUIDE.md).
