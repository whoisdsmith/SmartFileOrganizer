# AI Document Organizer - Developer Guide

This document provides technical information about the AI Document Organizer application architecture, code structure, and guidelines for extending its functionality.

## Architecture Overview

The application follows a modular design with clear separation of concerns:

```
┌───────────────┐        ┌────────────────┐        ┌────────────────┐
│    GUI Layer  │───────▶│  Business Layer │───────▶│   AI Services  │
└───────────────┘        └────────────────┘        └────────────────┘
       │                         │                         │
       │                         │                         │
       ▼                         ▼                         ▼
┌───────────────┐        ┌────────────────┐        ┌────────────────┐
│   User Input  │        │  File System    │        │  Google Gemini │
│   & Display   │        │  Operations     │        │    & OpenAI    │
└───────────────┘        └────────────────┘        └────────────────┘
```

## Project Structure

The project follows a clean, organized structure:

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
│   ├── DEVELOPER_GUIDE.md    # Developer documentation (this file)
│   └── ALTERNATIVE_AI_MODELS.md # AI model information
├── assets/                   # Application assets
│   └── generated-icon.png    # Application icon
├── packaging/                # Packaging-related files
│   ├── ai_document_organizer.spec # PyInstaller specification
│   ├── installer.nsi         # NSIS installer script
│   └── build_exe.py          # Build script
├── tests/                    # Test files
│   ├── test_ai_services.py   # Tests for AI services
│   ├── test_document_organizer.py # Integration tests
│   └── test_files/           # Sample files for testing
├── main.py                   # Main entry point
├── requirements.txt          # Dependencies
└── pyproject.toml            # Project metadata
```

## Code Structure

### Main Components

1. **main.py**: Application entry point and initialization
   - Sets up logging
   - Configures application environment (DPI awareness, icons, theme)
   - Initializes and launches the GUI

2. **src/gui.py**: User interface components
   - Implements `DocumentOrganizerApp` class for the main window
   - Handles user input, file browsing, and results display
   - Manages threading for non-blocking operations
   - Implements settings tab for customization options
   - Provides theme management and user preferences
   - Includes AI model selection and API key management

3. **src/file_analyzer.py**: Document scanning and analysis
   - Scans directories for supported file types
   - Collects file information
   - Coordinates between parser and AI analyzer
   - Implements batch processing with configurable size and delay

4. **src/file_parser.py**: Content extraction from various file formats
   - Implements parsing logic for each supported file type
   - Extracts text and metadata
   - Handles encoding detection and character set issues

5. **src/ai_analyzer.py**: AI processing using Google Gemini
   - Connects to Google Gemini API
   - Constructs appropriate prompts for analysis
   - Implements rate limiting and exponential backoff
   - Provides model selection capabilities
   - Handles API errors gracefully

6. **src/openai_analyzer.py**: AI processing using OpenAI
   - Connects to OpenAI API
   - Constructs appropriate prompts for analysis
   - Provides model selection capabilities
   - Handles API errors gracefully

7. **src/ai_service_factory.py**: Factory for creating AI analyzers
   - Creates the appropriate AI analyzer based on settings
   - Handles fallback behavior if a service is unavailable
   - Provides access to available services

8. **src/settings_manager.py**: Application settings management
   - Loads and saves user preferences
   - Manages API keys securely
   - Stores selected AI models and service preferences
   - Provides access to settings through a consistent interface

9. **src/file_organizer.py**: Document organization based on analysis
   - Creates category-based folder structure
   - Moves/copies files to appropriate locations
   - Generates metadata files with analysis results

10. **src/utils.py**: Helper functions and utilities
    - File size formatting
    - Filename sanitization
    - Text processing utilities

### Data Flow

1. User selects source directory containing documents
2. `FileAnalyzer` scans directory for supported files
3. For each file:
   - `FileParser` extracts text content based on file type
   - `AIAnalyzer` processes content via Google Gemini API
   - Results are displayed in the GUI
4. User selects target directory and initiates organization
5. `FileOrganizer` creates category folders and copies files

## Key Classes and Methods

### FileAnalyzer

```python
class FileAnalyzer:
    def __init__(self):
        self.parser = FileParser()
        self.ai_analyzer = AIAnalyzer()

    def scan_directory(self, directory_path):
        # Scans directory and returns list of analyzed files

    def _get_file_info(self, file_path, file_ext):
        # Extracts basic file information
```

### FileParser

```python
class FileParser:
    def extract_text(self, file_path, file_ext):
        # Extracts text content from various file types

    def extract_metadata(self, file_path, file_ext):
        # Extracts metadata from files

    def _parse_csv(self, file_path):
        # CSV-specific parsing logic

    # Additional parsing methods for other file types
```

### AIAnalyzer

```python
class AIAnalyzer:
    def __init__(self):
        # Initialize Google Gemini API connection

    def analyze_content(self, text, file_type):
        # Analyze document content using AI

    def _get_content_analysis(self, text, file_type):
        # Constructs prompt and processes API response

    def find_similar_documents(self, target_doc, document_list, max_results=5):
        # Find documents similar to the target document
        # Returns list of similar document dictionaries with similarity scores

    def find_related_content(self, target_doc, document_list, max_results=5):
        # Find documents related to the target document using AI comparison
        # Returns dictionary with relationship information and related documents
        # Identifies relationship types (prerequisite, sequential, contextual, extension)
        # Provides strength ratings (high, medium, low) with explanations
```

### FileOrganizer

```python
class FileOrganizer:
    def organize_files(self, analyzed_files, target_dir, callback=None, options=None):
        # Organizes files based on AI analysis with customizable options
        # Options include:
        # - create_category_folders: Whether to create category folders (default: True)
        # - generate_summaries: Whether to generate content summary files (default: True)
        # - include_metadata: Whether to create metadata files (default: True)
        # - copy_instead_of_move: Whether to copy files instead of moving them (default: True)

    def _create_metadata_file(self, file_info, target_path):
        # Creates metadata file with AI analysis

    def _create_summary_file(self, file_info, target_path):
        # Creates separate summary file with content summary and timestamps
```

## Extending the Application

### Adding Support for New File Types

1. Update `FileParser.extract_text()` to recognize the new extension
2. Implement a new parsing method (`_parse_new_type()`)
3. Add metadata extraction for the new type if applicable

Example:

```python
def extract_text(self, file_path, file_ext):
    # Existing code...
    elif file_ext == '.pdf':
        return self._parse_pdf(file_path)
    # ...

def _parse_pdf(self, file_path):
    """Parse PDF file content"""
    try:
        # Use appropriate PDF library
        import PyPDF2

        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text() + "\n\n"
            return text
    except Exception as e:
        return f"Error parsing PDF file: {str(e)}"
```

### Customizing AI Analysis

The analysis prompt can be customized in `AIAnalyzer._get_content_analysis()`:

```python
def _get_content_analysis(self, text, file_type):
    # Modify the prompt to extract different or additional information
    prompt = f"""
    Please analyze the following {file_type} document content and provide:
    1. A category for document organization (choose the most specific appropriate category)
    2. 3-5 keywords that represent the main topics in the document
    3. A brief summary of the document content (max 2-3 sentences)
    4. The intended audience for this document
    5. A difficulty rating from 1-5 (1=simple, 5=complex)

    Content:
    {text}

    Return your analysis in JSON format with the following structure:
    {{
        "category": "Category name",
        "keywords": ["keyword1", "keyword2", "keyword3"],
        "summary": "Brief summary of the content",
        "audience": "Intended audience",
        "difficulty": 3
    }}

    Make sure to return ONLY valid JSON without any additional text or explanation.
    """

    # Update the rest of the method to handle the new fields
```

### Adding Support for Other AI Models

The application can be extended to work with different AI models:

1. Create a new analyzer class (e.g., `OpenAIAnalyzer`)
2. Implement compatible analysis methods
3. Update `file_analyzer.py` to select the appropriate analyzer

Example:

```python
# In a new file openai_analyzer.py
import os
import json
from openai import OpenAI

class OpenAIAnalyzer:
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY", "")
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"  # the newest OpenAI model

    def analyze_content(self, text, file_type):
        # Similar to AIAnalyzer.analyze_content()

    def _get_content_analysis(self, text, file_type):
        prompt = f"""
        Please analyze the following {file_type} document content and provide:
        1. A category for document organization (choose the most specific appropriate category)
        2. 3-5 keywords that represent the main topics in the document
        3. A brief summary of the document content (max 2-3 sentences)

        Content:
        {text}
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result
```

## UI Customization

### Application Settings and Preferences

The application implements a settings system through a dedicated tab in the main interface:

1. **Accessing Settings**: The settings tab is implemented in `_create_settings_widgets()` method
2. **Theme Management**: The application supports multiple built-in ttk themes
3. **User Preferences**: Various user preferences can be saved for future sessions

Example settings implementation:

```python
def _create_settings_widgets(self):
    """Create widgets for the settings tab"""
    # App settings frame
    self.app_settings_frame = ttk.LabelFrame(self.settings_tab, text="Application Settings", padding=(10, 5))

    # Performance settings
    self.performance_frame = ttk.Frame(self.app_settings_frame)
    ttk.Label(self.performance_frame, text="Default Batch Size:").grid(row=0, column=0, sticky='w', padx=5, pady=5)

    # Default batch size setting
    default_batch_combobox = ttk.Combobox(self.performance_frame, textvariable=self.batch_size,
                                        values=["5", "10", "20", "50", "100"], width=5)
    default_batch_combobox.current(2)  # Default to 20
    default_batch_combobox.grid(row=0, column=1, sticky='w', padx=5, pady=5)

    # Save settings button
    save_settings_button = ttk.Button(self.performance_frame, text="Save as Default",
                                    command=self.save_batch_size)
    save_settings_button.grid(row=0, column=2, sticky='w', padx=5, pady=5)

    # UI settings
    self.ui_frame = ttk.Frame(self.app_settings_frame)
    ttk.Label(self.ui_frame, text="Interface Theme:").grid(row=0, column=0, sticky='w', padx=5, pady=5)

    # Theme selector
    theme_names = list(self.style.theme_names())
    theme_combobox = ttk.Combobox(self.ui_frame, textvariable=self.theme_var, values=theme_names, width=10)
    theme_combobox.grid(row=0, column=1, sticky='w', padx=5, pady=5)

    # Apply theme button
    apply_theme_button = ttk.Button(self.ui_frame, text="Apply Theme",
                                  command=self.apply_theme)
    apply_theme_button.grid(row=0, column=2, sticky='w', padx=5, pady=5)

    # Organization Rules Frame
    self.org_rules_frame = ttk.LabelFrame(self.settings_tab, text="Organization Rules", padding=(10, 5))

    # Create checkboxes for organization rules
    ttk.Checkbutton(self.org_rules_frame, text="Create category folders",
                   variable=self.create_category_folders,
                   command=self.save_organization_rules).grid(row=0, column=0, sticky='w', padx=5, pady=5)

    ttk.Checkbutton(self.org_rules_frame, text="Generate content summaries",
                   variable=self.generate_summaries,
                   command=self.save_organization_rules).grid(row=1, column=0, sticky='w', padx=5, pady=5)

    ttk.Checkbutton(self.org_rules_frame, text="Include metadata in separate files",
                   variable=self.include_metadata,
                   command=self.save_organization_rules).grid(row=2, column=0, sticky='w', padx=5, pady=5)

    ttk.Checkbutton(self.org_rules_frame, text="Copy files instead of moving them",
                   variable=self.copy_instead_of_move,
                   command=self.save_organization_rules).grid(row=3, column=0, sticky='w', padx=5, pady=5)

    # Help text explaining the rules
    rules_help_frame = ttk.Frame(self.org_rules_frame)
    rules_help_text = ScrolledText(rules_help_frame, wrap=tk.WORD, width=40, height=5)
    rules_help_text.insert(tk.END, "Organization Rules Help:\n\n")
    rules_help_text.insert(tk.END, "- Create category folders: Create a folder structure based on AI-detected categories\n")
    rules_help_text.insert(tk.END, "- Generate summaries: Create summary files with AI-generated content descriptions\n")
    rules_help_text.insert(tk.END, "- Include metadata: Save detailed AI analysis alongside each file\n")
    rules_help_text.insert(tk.END, "- Copy files: Keep original files intact (vs. moving them)\n")
    rules_help_text.config(state=tk.DISABLED)
    rules_help_frame.grid(row=0, column=1, rowspan=4, sticky='nsew', padx=5, pady=5)
    rules_help_text.pack(fill='both', expand=True)
```

Methods to handle settings changes:

```python
def apply_theme(self):
    """Apply the selected theme and update the UI"""
    theme = self.theme_var.get()
    try:
        # Apply the theme
        self.style.theme_use(theme)
        messagebox.showinfo("Theme Changed", f"Theme changed to: {theme}")
        logger.info(f"Changed theme to: {theme}")
    except Exception as e:
        logger.error(f"Error changing theme: {str(e)}")
        messagebox.showerror("Error", f"Could not apply theme: {str(e)}")

def save_batch_size(self):
    """Save the current batch size as the default"""
    try:
        batch_size = self.batch_size.get()
        # Here you would save to a config file
        messagebox.showinfo("Settings Saved", f"Default batch size set to: {batch_size}")
        logger.info(f"Default batch size saved: {batch_size}")
    except Exception as e:
        logger.error(f"Error saving batch size: {str(e)}")
        messagebox.showerror("Error", f"Could not save settings: {str(e)}")

def save_organization_rules(self):
    """Save the organization rules to settings"""
    try:
        # Get values from UI
        rules = {
            "create_category_folders": self.create_category_folders.get(),
            "generate_summaries": self.generate_summaries.get(),
            "include_metadata": self.include_metadata.get(),
            "copy_instead_of_move": self.copy_instead_of_move.get()
        }

        # Save to settings
        for key, value in rules.items():
            self.settings_manager.set_setting(f"organization_rules.{key}", value)

        logger.info(f"Organization rules saved: {rules}")
    except Exception as e:
        logger.error(f"Error saving organization rules: {str(e)}")
        messagebox.showerror("Error", f"Could not save organization rules: {str(e)}")
```

### Adding New Features to the GUI

To add new buttons or functionality to the GUI:

1. Modify `DocumentOrganizerApp._create_widgets()` to add new UI elements
2. Add corresponding methods to handle new actions
3. Update the layout in `_setup_layout()`

Example - Adding an "Export Analysis" button:

```python
def _create_widgets(self):
    # Existing code...

    # Add export button
    self.export_button = ttk.Button(
        self.button_frame,
        text="Export Analysis",
        command=self.export_analysis
    )

    # ...

def _setup_layout(self):
    # Existing code...

    # Add export button to layout
    self.export_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

    # ...

def export_analysis(self):
    """Export analysis results to CSV file"""
    if not self.analyzed_files:
        messagebox.showinfo("Export", "No files have been analyzed yet.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if not file_path:
        return

    try:
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Filename", "Category", "Keywords", "Summary"])

            for file in self.analyzed_files:
                writer.writerow([
                    file["filename"],
                    file.get("category", "Unknown"),
                    ", ".join(file.get("keywords", [])),
                    file.get("summary", "")
                ])

        messagebox.showinfo("Export", f"Analysis exported to {file_path}")
    except Exception as e:
        messagebox.showerror("Export Error", f"Error exporting analysis: {str(e)}")
```

## Performance Optimization

### Handling Large Document Sets

For large sets of documents, consider these optimizations:

1. **Batch Processing**: Process files in batches to manage memory usage

```python
def scan_directory(self, directory_path, batch_size=50):
    all_files = []
    file_paths = [os.path.join(directory_path, f) for f in os.listdir(directory_path)]

    # Process in batches
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i+batch_size]
        # Process this batch
        batch_results = self._process_batch(batch)
        all_files.extend(batch_results)

    return all_files
```

2. **Parallelization**: Use multiprocessing for CPU-bound parsing operations

```python
from multiprocessing import Pool

def _process_batch(self, file_paths):
    # Use multiprocessing for parsing
    with Pool(processes=4) as pool:
        results = pool.map(self._process_single_file, file_paths)
    return [r for r in results if r is not None]
```

## Logging and Debugging

The application uses Python's built-in logging module. Logs are stored in:

- Windows: `%USERPROFILE%\AppData\Local\AIDocumentOrganizer\app.log`
- macOS/Linux: `~/.local/share/AIDocumentOrganizer/app.log`

To increase log detail for debugging:

```python
# In setup_logging()
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
```

## Testing

The application includes test scripts:

- `test_document_organizer.py`: Tests the end-to-end workflow
- `test_ai_analyzer.py`: Tests the AI integration
- `test_relationships.py`: Tests basic document relationship detection
- `test_deep_relationships.py`: Tests advanced contextual document relationship detection

To add new tests, follow this pattern:

```python
def test_new_feature():
    """Test description"""
    print("Testing new feature")

    # Setup
    # ...

    # Test steps
    # ...

    # Verification
    assert result == expected, f"Expected {expected}, got {result}"

    print("Test completed successfully!")

if __name__ == "__main__":
    test_new_feature()
```

## Best Practices

1. **Error Handling**: Always use try-except blocks for external operations
2. **User Feedback**: Update the UI to show progress during long operations
3. **API Keys**: Never hardcode API keys; always use environment variables
4. **Large Files**: Implement appropriate truncation for very large documents
5. **Threading**: Keep UI responsive by offloading heavy tasks to threads

## Environment Variables

- `GOOGLE_API_KEY`: Required for Google Gemini API access
- `OPENAI_API_KEY`: Optional, for OpenAI integration if implemented

## Dependencies

- `beautifulsoup4`: HTML parsing
- `chardet`: Character encoding detection
- `python-docx`: Word document parsing
- `google-generativeai`: Google Gemini API client
- `pandas`, `openpyxl`: Excel and CSV handling
- `numpy`: Numerical computations
- `openai`: Optional, for OpenAI integration

## AI Service Integration

The application supports multiple AI services through a flexible architecture:

### AI Service Factory

The `AIServiceFactory` class provides a centralized way to create AI analyzers:

```python
from src.ai_service_factory import AIServiceFactory
from src.settings_manager import SettingsManager

# Create a settings manager
settings_manager = SettingsManager()

# Create an analyzer based on settings
analyzer = AIServiceFactory.create_analyzer(None, settings_manager)
```

### Adding a New AI Service

To add support for a new AI service:

1. Create a new analyzer class (e.g., `NewServiceAnalyzer`) that implements:
   - `__init__(self, settings_manager=None)` - Constructor that initializes the service
   - `analyze_content(self, text, file_type)` - Method to analyze document content
   - `get_available_models(self)` - Method to return available models
   - `set_model(self, model_name)` - Method to set the current model

2. Update `AIServiceFactory` to support the new service:
   - Add the new service to the `get_available_services()` method
   - Update the `create_analyzer()` method to create your new analyzer

3. Update the GUI to include the new service:
   - Add the service to the service selection dropdown
   - Add model selection for the new service
   - Add API key input for the new service

### Model Selection

The application supports selecting different models for each AI service:

```python
# Get available models
models = analyzer.get_available_models()

# Set a specific model
analyzer.set_model(model_name)
```

### API Key Management

API keys can be managed through the `SettingsManager`:

```python
# Get an API key
api_key = settings_manager.get_api_key(service_type)

# Set an API key
settings_manager.set_api_key(service_type, api_key)
```

## Rate Limiting and Error Handling

The application implements several strategies to handle API rate limits:

1. **Configurable Batch Size**: Process fewer files at once
2. **Batch Delay**: Add a delay between batches
3. **Exponential Backoff**: Retry failed requests with increasing delays
4. **Request Rate Limiting**: Limit the number of requests per minute

Example implementation in `AIAnalyzer`:

```python
def _apply_rate_limit(self):
    """Apply rate limiting to avoid 429 errors"""
    current_time = time.time()
    time_since_last_request = current_time - self.last_request_time

    # If we've made a request too recently, wait
    if time_since_last_request < self.min_request_interval:
        sleep_time = self.min_request_interval - time_since_last_request
        logger.debug(f"Rate limiting: Sleeping for {sleep_time:.2f} seconds")
        time.sleep(sleep_time)

    # Update the last request time
    self.last_request_time = time.time()
```
