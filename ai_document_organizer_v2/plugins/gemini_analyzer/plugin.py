"""
Google Gemini AI Analyzer Plugin for AI Document Organizer.

This plugin provides AI document analysis using Google's Gemini models.
It supports content categorization, theme extraction, keyword generation,
and document similarity comparison.
"""

import logging
import os
import time
from typing import Dict, List, Any, Optional, Tuple

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from ai_document_organizer_v2.core.plugin_base import BasePlugin

logger = logging.getLogger("AIDocumentOrganizer")


class GeminiAnalyzerPlugin(BasePlugin):
    """Plugin for analyzing documents using Google's Gemini AI models."""
    
    # Set plugin_type class attribute for proper registration
    plugin_type = "ai_analyzer"
    name = "Google Gemini AI Analyzer"
    version = "1.0.0"
    description = "Analyzes documents using Google's Gemini AI models"
    
    def __init__(self, plugin_id="gemini_analyzer", name=None, version=None, description=None):
        """Initialize the plugin."""
        super().__init__(plugin_id, name, version, description)
        # Additional configuration
        self._config_schema = {
            "api_key": {
                "type": "string",
                "description": "Google AI API Key"
            },
            "model": {
                "type": "string",
                "description": "Gemini model to use",
                "default": "models/gemini-2.0-flash"
            },
            "requests_per_minute": {
                "type": "integer",
                "description": "Maximum API requests per minute",
                "default": 30
            },
            "max_retries": {
                "type": "integer",
                "description": "Maximum number of retries for rate limit errors",
                "default": 3
            }
        }
        self.model = None
        self.last_request_time = 0
        self.gemini_available = GEMINI_AVAILABLE
        
        # Settings manager will be set during initialization
        self.settings_manager = None
        
    def initialize(self) -> bool:
        """
        Initialize the plugin. Called after plugin is loaded.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Skip if Gemini is not available
        if not self.gemini_available:
            logger.error("Google Generative AI library is not available. Install with 'pip install google-generativeai'")
            return False
        
        # Get API key from settings or environment
        api_key = self._get_api_key()
        if not api_key:
            logger.error("Google AI API key not found in settings or environment variables")
            return False
        
        # Configure the Gemini API
        try:
            genai.configure(api_key=api_key)
            
            # Get model name from settings
            model_name = self.get_setting(
                "ai_service.google_model", 
                "models/gemini-2.0-flash"
            )
            
            # Set the model
            self.set_model(model_name)
            
            return True
        except Exception as e:
            logger.error(f"Error initializing Google Gemini AI: {e}")
            return False
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin. Called before plugin is unloaded.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        self.model = None
        return True
    
    def _get_api_key(self) -> Optional[str]:
        """
        Get Google AI API key from settings or environment.
        
        Returns:
            API key or None if not found
        """
        # Try settings first
        api_key = self.get_setting("ai_service.google_api_key", None)
        
        # Fall back to environment variables if not in settings
        if not api_key:
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        
        return api_key
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available Gemini models.

        Returns:
            List of model names
        """
        if not self.gemini_available:
            return []
            
        try:
            models = [model.name for model in genai.list_models()]
            return models
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    def set_model(self, model_name: str) -> bool:
        """
        Set the model to use for analysis.

        Args:
            model_name: Name of the model to use

        Returns:
            True if successful, False otherwise
        """
        if not self.gemini_available:
            return False
            
        try:
            # First check if the model exists
            available_models = self.get_available_models()
            if model_name not in available_models:
                logger.warning(f"Model {model_name} not found. Available models: {available_models}")
                # Try to use a default model
                if "models/gemini-2.0-flash" in available_models:
                    model_name = "models/gemini-2.0-flash"
                elif len(available_models) > 0:
                    model_name = available_models[0]
                else:
                    logger.error("No available models found")
                    return False
            
            # Update settings
            self.set_setting("ai_service.google_model", model_name)
            
            # Get the model configuration
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"Using model: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Error setting model: {e}")
            return False
    
    def analyze_content(self, text: str, file_type: str) -> Dict[str, Any]:
        """
        Analyze document content using Gemini AI.

        Args:
            text: The document text content
            file_type: The type of document

        Returns:
            Dictionary with analysis results
        """
        if not self.gemini_available or not self.model:
            return {
                "error": "Google Gemini AI is not available or not initialized"
            }
            
        try:
            # Apply rate limiting
            self._apply_rate_limit()
            
            # Get content analysis
            analysis = self._get_content_analysis(text, file_type)
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return {
                "error": f"Error analyzing content: {e}"
            }
    
    def _get_content_analysis(self, text: str, file_type: str) -> Dict[str, Any]:
        """
        Get AI analysis of document content using Google Gemini.

        Args:
            text: The document text
            file_type: The type of document

        Returns:
            Dictionary with analysis results
        """
        # Truncate text if too long (Gemini has token limits)
        MAX_TEXT_LENGTH = 10000
        if len(text) > MAX_TEXT_LENGTH:
            truncated_text = text[:MAX_TEXT_LENGTH] + "... [TRUNCATED]"
        else:
            truncated_text = text
        
        # Create a prompt for the AI
        prompt = f"""
        Analyze the following {file_type} document content and extract key information:

        {truncated_text}

        Based on the content, provide the following in JSON format:
        1. Main category (single most appropriate category)
        2. Subcategories (up to 3)
        3. Primary theme or topic
        4. Key concepts (up to 5)
        5. Important keywords (up to 10)
        6. Brief summary (3-5 sentences)
        7. Document type (e.g., report, article, manual, etc.)
        8. Audience (who this document appears to be written for)
        9. Content quality assessment (poor, average, good, excellent)
        10. Tone (formal, informal, technical, casual, etc.)

        Format your response as a JSON object like this:
        {{
            "category": "string",
            "subcategories": ["string", "string", "string"],
            "theme": "string",
            "concepts": ["string", "string", "string", "string", "string"],
            "keywords": ["string", "string", "string", "string", "string", "string", "string", "string", "string", "string"],
            "summary": "string",
            "document_type": "string",
            "audience": "string",
            "quality": "string",
            "tone": "string"
        }}

        Only respond with the JSON object, nothing else.
        """
        
        # Send to Gemini AI
        max_retries = self.get_setting("ai_service.max_retries", 3)
        retries = 0
        
        while retries <= max_retries:
            try:
                response = self.model.generate_content(prompt)
                
                # Try to parse the JSON from the response
                import json
                try:
                    # Extract the JSON part from the response
                    if hasattr(response, 'text'):
                        result_text = response.text
                    else:
                        result_text = str(response)
                    
                    # Clean up the text to extract just the JSON
                    if "```json" in result_text:
                        # Extract content between ```json and ```
                        json_start = result_text.find("```json") + 7
                        json_end = result_text.find("```", json_start)
                        if json_end > json_start:
                            result_text = result_text[json_start:json_end].strip()
                    
                    # Remove any markdown backticks
                    result_text = result_text.replace("```", "").strip()
                    
                    # Parse the JSON
                    analysis_result = json.loads(result_text)
                    
                    # Add file_type to the result
                    analysis_result["file_type"] = file_type
                    
                    return analysis_result
                except json.JSONDecodeError as je:
                    logger.error(f"JSON decode error: {je}. Raw response: {result_text}")
                    # Try again with a simpler approach
                    retries += 1
                    continue
                    
            except Exception as e:
                logger.error(f"Error calling Gemini API: {e}")
                if "429" in str(e) or "rate limit" in str(e).lower():
                    # Rate limit error, wait and retry
                    wait_time = 2 ** retries  # Exponential backoff
                    logger.info(f"Rate limit exceeded, retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    # Other error, don't retry
                    break
        
        # If we get here, we've either exhausted retries or hit a non-rate-limit error
        return {
            "category": "Unknown",
            "subcategories": ["Unknown"],
            "theme": "Unknown",
            "concepts": ["Unknown"],
            "keywords": ["Unknown"],
            "summary": "Could not analyze document content",
            "document_type": file_type,
            "audience": "Unknown",
            "quality": "Unknown",
            "tone": "Unknown",
            "file_type": file_type,
            "error": "Failed to analyze document after multiple attempts"
        }
    
    def _apply_rate_limit(self):
        """Apply rate limiting to avoid 429 errors."""
        # Get rate limit from settings
        requests_per_minute = self.get_setting(
            "ai_service.requests_per_minute", 
            30
        )
        
        # Calculate minimum time between requests in seconds
        min_interval = 60.0 / requests_per_minute
        
        # Check if we need to wait
        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            # Wait the remaining time
            wait_time = min_interval - elapsed
            time.sleep(wait_time)
        
        # Update last request time
        self.last_request_time = time.time()
    
    def find_similar_documents(self, target_doc: Dict[str, Any], document_list: List[Dict[str, Any]], 
                               max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Find documents similar to the target document.

        Args:
            target_doc: Target document info dictionary (must contain 'keywords', 'category', and/or 'theme')
            document_list: List of document info dictionaries to compare against
            max_results: Maximum number of similar documents to return

        Returns:
            List of similar document dictionaries with similarity scores and relationship explanations
        """
        if not target_doc or not document_list:
            return []
        
        # Extract target document features for comparison
        target_keywords = target_doc.get('keywords', [])
        target_category = target_doc.get('category', '')
        target_theme = target_doc.get('theme', '')
        
        # Calculate similarity scores for each document
        similarity_results = []
        
        for doc in document_list:
            # Skip comparing to itself
            if doc.get('file_path') == target_doc.get('file_path'):
                continue
                
            # Get document features
            doc_keywords = doc.get('keywords', [])
            doc_category = doc.get('category', '')
            doc_theme = doc.get('theme', '')
            
            # Calculate keyword overlap
            keyword_overlap = len(set(target_keywords) & set(doc_keywords))
            
            # Calculate category match (1 if same, 0 if different)
            category_match = 1 if target_category.lower() == doc_category.lower() else 0
            
            # Calculate theme similarity (simple string matching for now)
            theme_similarity = 0
            if target_theme and doc_theme:
                # Count word overlap in themes
                target_theme_words = set(target_theme.lower().split())
                doc_theme_words = set(doc_theme.lower().split())
                theme_overlap = len(target_theme_words & doc_theme_words)
                
                # Normalize by the average number of words
                avg_word_count = (len(target_theme_words) + len(doc_theme_words)) / 2
                if avg_word_count > 0:
                    theme_similarity = theme_overlap / avg_word_count
            
            # Weighted similarity score (weights can be adjusted)
            similarity_score = (
                0.5 * keyword_overlap / max(len(target_keywords), 1) +
                0.3 * category_match +
                0.2 * theme_similarity
            )
            
            # Generate relationship explanation
            relationship = []
            if keyword_overlap > 0:
                common_keywords = list(set(target_keywords) & set(doc_keywords))
                relationship.append(f"Shares {keyword_overlap} keywords: {', '.join(common_keywords[:3])}")
                
            if category_match:
                relationship.append(f"Same category: {doc_category}")
                
            if theme_similarity > 0.3:
                relationship.append(f"Similar theme")
            
            similarity_results.append({
                'document': doc,
                'similarity_score': similarity_score,
                'relationship': '. '.join(relationship) if relationship else "Low similarity"
            })
        
        # Sort by similarity score (descending) and take top results
        similarity_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similarity_results[:max_results]
    
    def find_related_content(self, target_doc: Dict[str, Any], document_list: List[Dict[str, Any]], 
                            max_results: int = 5) -> Dict[str, Any]:
        """
        Find documents related to the target document using AI comparison.

        Args:
            target_doc: Target document info dictionary with content analysis
            document_list: List of document info dictionaries to compare against
            max_results: Maximum number of related documents to return

        Returns:
            Dictionary with relationship information and related documents
        """
        # First use the simpler similarity algorithm
        similar_docs = self.find_similar_documents(target_doc, document_list, max_results)
        
        # For highly similar documents, enhance with AI insights
        if self.gemini_available and self.model and similar_docs and len(similar_docs) > 0:
            try:
                # Only process top 2 similar documents with AI for efficiency
                top_similar = similar_docs[:min(2, len(similar_docs))]
                
                for similar_doc in top_similar:
                    doc = similar_doc['document']
                    
                    # Skip if similarity is too low (not worth AI processing)
                    if similar_doc['similarity_score'] < 0.3:
                        continue
                    
                    # Get detailed AI comparison
                    self._apply_rate_limit()
                    
                    target_summary = target_doc.get('summary', '')
                    doc_summary = doc.get('summary', '')
                    
                    # Prepare prompt for comparing the documents
                    prompt = f"""
                    Compare these two document summaries and explain the relationship between them:
                    
                    Document A: {target_summary}
                    
                    Document B: {doc_summary}
                    
                    Explain in 1-2 sentences how these documents relate to each other.
                    Focus on thematic connections, complementary information, or potential dependencies.
                    """
                    
                    # Get AI response
                    response = self.model.generate_content(prompt)
                    
                    # Extract the text
                    if hasattr(response, 'text'):
                        ai_relationship = response.text.strip()
                    else:
                        ai_relationship = str(response).strip()
                    
                    # Update the relationship explanation
                    similar_doc['ai_relationship'] = ai_relationship
            
            except Exception as e:
                logger.error(f"Error getting AI-enhanced relationships: {e}")
                # Continue with the algorithmic results if AI enhancement fails
        
        # Return results in the expected format
        return {
            'target_document': target_doc,
            'related_documents': similar_docs,
            'relationship_type': 'ai_enhanced' if self.gemini_available and self.model else 'algorithmic'
        }