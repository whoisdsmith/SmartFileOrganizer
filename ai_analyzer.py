import os
import json
import google.generativeai as genai

class AIAnalyzer:
    """
    Class for analyzing document content using Google Gemini API
    """
    def __init__(self):
        # Get API key from environment variable
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            print("Warning: GOOGLE_API_KEY environment variable not set.")
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Get available models
        try:
            models = [m.name for m in genai.list_models()]
            print(f"Available Gemini models: {models}")
            
            # Find the most suitable model from available models
            preferred_models = [
                'models/gemini-2.0-flash',
                'models/gemini-1.5-flash',
                'models/gemini-1.5-pro',
                'models/gemini-1.0-pro',
                'gemini-pro'  # backwards compatibility format
            ]
            
            # Find the first available preferred model
            model_name = None
            for preferred in preferred_models:
                if preferred in models:
                    model_name = preferred
                    break
            
            # If none of our preferred models are available, use the first model that has "gemini" in the name
            if not model_name:
                for m in models:
                    if 'gemini' in m.lower():
                        model_name = m
                        break
            
            # If we still don't have a model, use the first available model
            if not model_name and models:
                model_name = models[0]
            
            if not model_name:
                raise ValueError("No suitable Gemini models available")
                
            print(f"Using model: {model_name}")
            self.model = genai.GenerativeModel(model_name)
        except Exception as e:
            print(f"Error getting Gemini models: {e}")
            # Fallback to a common model format if there's an error
            fallback_model = "models/gemini-1.5-pro"
            print(f"Falling back to {fallback_model} model")
            self.model = genai.GenerativeModel(fallback_model)
    
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
        max_text_length = 30000  # Characters (Gemini can handle more text than OpenAI)
        truncated_text = text[:max_text_length]
        if len(text) > max_text_length:
            truncated_text += f"\n\n[Content truncated. Original length: {len(text)} characters]"
        
        try:
            analysis = self._get_content_analysis(truncated_text, file_type)
            return analysis
        except Exception as e:
            print(f"Error in AI analysis: {str(e)}")
            # Return basic analysis if AI fails
            return {
                "category": "Unclassified",
                "keywords": ["document"],
                "summary": "Error analyzing document content."
            }
    
    def _get_content_analysis(self, text, file_type):
        """
        Get AI analysis of document content using Google Gemini
        
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
            # Generate content with Gemini - handle different API versions
            try:
                # Try the newer API format first
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": 800,
                    }
                )
            except Exception as e:
                print(f"First API attempt failed: {e}, trying alternative format")
                # Try the alternative API format
                response = self.model.generate_content(
                    contents=[
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": 800,
                    }
                )
            
            # Extract the text response and parse as JSON
            if hasattr(response, 'text'):
                response_text = response.text
            else:
                # Handle alternative response format
                response_text = response.candidates[0].content.parts[0].text
            
            print(f"AI response received: {response_text[:100]}...")
            
            # Clean up response to ensure it's valid JSON
            # Sometimes Gemini might add backticks or other formatting
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Parse the JSON response
            result = json.loads(response_text)
            
            # Ensure all expected fields are present
            if not all(k in result for k in ["category", "keywords", "summary"]):
                raise ValueError("Missing required fields in AI response")
            
            return result
        except Exception as e:
            print(f"AI analysis exception: {e}")
            raise Exception(f"AI analysis failed: {str(e)}")
