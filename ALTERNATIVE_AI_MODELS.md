# Using Alternative AI Models with the Document Organizer

This guide explains how to modify the AI Document Organizer to work with alternative AI models such as OpenAI's GPT-4o.

## Using OpenAI Instead of Google Gemini

### Step 1: Create an OpenAI API Key

1. Go to [OpenAI's website](https://platform.openai.com/)
2. Create an account or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and save your API key securely

### Step 2: Set Up Environment Variable

#### Windows:
```
setx OPENAI_API_KEY "your-openai-api-key-here"
```

#### macOS/Linux:
```
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Step 3: Create OpenAI Analyzer File

Create a new file named `openai_analyzer.py` with the following content:

```python
import os
import json
from openai import OpenAI

class OpenAIAnalyzer:
    """
    Class for analyzing document content using OpenAI API
    """
    def __init__(self):
        # Get API key from environment variable
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            print("Warning: OPENAI_API_KEY environment variable not set.")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=api_key)
        
        # Use GPT-4o (the newest OpenAI model as of 2024)
        self.model = "gpt-4o"
        print(f"Using OpenAI model: {self.model}")
    
    def analyze_content(self, text, file_type):
        """
        Analyze document content using AI
        
        Args:
            text: The document text content
            file_type: The type of document (CSV, Excel, HTML, etc.)
            
        Returns:
            Dictionary with analysis results
        """
        # Truncate text if too long
        max_text_length = 25000  # Characters
        truncated_text = text[:max_text_length]
        if len(text) > max_text_length:
            truncated_text += f"\n\n[Content truncated. Original length: {len(text)} characters]"
        
        try:
            analysis = self._get_content_analysis(truncated_text, file_type)
            return analysis
        except Exception as e:
            print(f"Error in OpenAI analysis: {str(e)}")
            # Return basic analysis if AI fails
            return {
                "category": "Unclassified",
                "keywords": ["document"],
                "summary": "Error analyzing document content."
            }
    
    def _get_content_analysis(self, text, file_type):
        """
        Get AI analysis of document content using OpenAI
        
        Args:
            text: The document text
            file_type: The type of document
            
        Returns:
            Dictionary with analysis results
        """
        # Construct the prompt
        prompt = f"""
        Please analyze the following {file_type} document content and provide:
        1. A category for document organization (choose the most specific appropriate category)
        2. 3-5 keywords that represent the main topics in the document
        3. A brief summary of the document content (max 2-3 sentences)
        
        Content:
        {text}
        
        Return your analysis in JSON format with the following structure:
        {{
            "category": "Category name",
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "summary": "Brief summary of the content"
        }}
        
        Make sure to return ONLY valid JSON without any additional text or explanation.
        """
        
        try:
            # Generate content with OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=800
            )
            
            # Extract the text response
            response_text = response.choices[0].message.content
            print(f"OpenAI response received: {response_text[:100]}...")
            
            # Parse the JSON response
            result = json.loads(response_text)
            
            # Ensure all expected fields are present
            if not all(k in result for k in ["category", "keywords", "summary"]):
                raise ValueError("Missing required fields in AI response")
            
            return result
        except Exception as e:
            print(f"OpenAI analysis exception: {e}")
            raise Exception(f"OpenAI analysis failed: {str(e)}")
```

### Step 4: Modify File Analyzer

Update `file_analyzer.py` to use the OpenAI analyzer:

1. Open `file_analyzer.py`
2. Add the following import at the top:
   ```python
   from openai_analyzer import OpenAIAnalyzer
   ```
3. In the `FileAnalyzer.__init__` method, modify the code to check for OpenAI API key:
   ```python
   def __init__(self):
       self.parser = FileParser()
       
       # Check if OpenAI API key is set
       if os.environ.get("OPENAI_API_KEY"):
           print("Using OpenAI for document analysis")
           self.ai_analyzer = OpenAIAnalyzer()
       else:
           print("Using Google Gemini for document analysis")
           self.ai_analyzer = AIAnalyzer()
   ```

### Step 5: Update Main Application

Update `main.py` to change the window title:

1. Open `main.py`
2. Find the line that sets the window title:
   ```python
   root.title("AI Document Organizer - Powered by Google Gemini")
   ```
3. Replace it with a dynamic title based on which API is used:
   ```python
   if os.environ.get("OPENAI_API_KEY"):
       root.title("AI Document Organizer - Powered by OpenAI")
   else:
       root.title("AI Document Organizer - Powered by Google Gemini")
   ```

## Using Azure OpenAI Service

### Step 1: Get Azure OpenAI API Access

1. Set up Azure OpenAI Service in your Azure account
2. Deploy a model and get your API endpoint, API key, and deployment name

### Step 2: Set Environment Variables

```
setx AZURE_OPENAI_KEY "your-azure-api-key"
setx AZURE_OPENAI_ENDPOINT "https://your-resource-name.openai.azure.com"
setx AZURE_OPENAI_DEPLOYMENT "your-deployment-name"
```

### Step 3: Create Azure OpenAI Analyzer File

Create a new file named `azure_analyzer.py` with the following content:

```python
import os
import json
from openai import AzureOpenAI

class AzureOpenAIAnalyzer:
    """
    Class for analyzing document content using Azure OpenAI Service
    """
    def __init__(self):
        # Get Azure OpenAI credentials from environment variables
        api_key = os.environ.get("AZURE_OPENAI_KEY", "")
        api_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
        
        if not all([api_key, api_endpoint, deployment]):
            print("Warning: Azure OpenAI environment variables not set properly.")
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-02-01",
            azure_endpoint=api_endpoint
        )
        
        self.deployment = deployment
        print(f"Using Azure OpenAI deployment: {self.deployment}")
    
    def analyze_content(self, text, file_type):
        """Similar to OpenAIAnalyzer.analyze_content()"""
        # Implementation similar to OpenAIAnalyzer
        # ...
    
    def _get_content_analysis(self, text, file_type):
        """Similar to OpenAIAnalyzer._get_content_analysis()"""
        # Use Azure-specific API calls
        response = self.client.chat.completions.create(
            model=self.deployment,  # Use deployment name instead of model name
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=800
        )
        # Rest of implementation similar to OpenAIAnalyzer
        # ...
```

### Step 4: Update File Analyzer for Azure Support

Extend the `FileAnalyzer.__init__` method to check for Azure credentials:

```python
def __init__(self):
    self.parser = FileParser()
    
    # Check for Azure OpenAI first (it's more specific)
    if all([
        os.environ.get("AZURE_OPENAI_KEY"),
        os.environ.get("AZURE_OPENAI_ENDPOINT"),
        os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    ]):
        print("Using Azure OpenAI for document analysis")
        self.ai_analyzer = AzureOpenAIAnalyzer()
    # Then check for regular OpenAI
    elif os.environ.get("OPENAI_API_KEY"):
        print("Using OpenAI for document analysis")
        self.ai_analyzer = OpenAIAnalyzer()
    # Fall back to Google Gemini
    else:
        print("Using Google Gemini for document analysis")
        self.ai_analyzer = AIAnalyzer()
```

## Using Anthropic's Claude

For Anthropic Claude integration, follow a similar pattern:

1. Obtain an Anthropic API key
2. Set it as an environment variable (`ANTHROPIC_API_KEY`)
3. Create a `claude_analyzer.py` file implementing the same interface
4. Update `file_analyzer.py` to check for the Anthropic API key

See the DEVELOPER_GUIDE.md for more detailed information on extending the application with alternative AI models.

## Comparing AI Model Performance

Each AI model has different strengths for document analysis:

| Model | Strengths | Limitations |
|-------|-----------|-------------|
| Google Gemini 2.0 Flash | Fast processing, excellent categorization | Limited token context |
| OpenAI GPT-4o | Nuanced analysis, high accuracy | Higher cost |
| Azure OpenAI | Enterprise security, data residency | Configuration complexity |
| Anthropic Claude | Long context windows | May require format adjustment |

## Performance Considerations

When switching AI models, consider these factors:

1. **Cost**: Different providers have different pricing models
2. **Speed**: Processing time varies by model
3. **Accuracy**: Some models may be better for specific document types
4. **Token limits**: Maximum document size varies by model
5. **API reliability**: Uptime and rate limits differ between providers

## Fallback Strategy

For production use, consider implementing a fallback strategy that tries multiple AI providers if the primary one fails:

```python
def analyze_with_fallback(self, text, file_type):
    # Try primary AI service
    try:
        return self.primary_analyzer.analyze_content(text, file_type)
    except Exception as primary_error:
        print(f"Primary AI service failed: {primary_error}")
        
        # Try backup service
        try:
            return self.backup_analyzer.analyze_content(text, file_type)
        except Exception as backup_error:
            print(f"Backup AI service failed: {backup_error}")
            
            # Last resort - basic analysis
            return {
                "category": "Unclassified",
                "keywords": ["document"],
                "summary": "Error analyzing document content."
            }
```