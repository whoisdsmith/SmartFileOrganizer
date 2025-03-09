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
        4. The primary theme or subject of the document (1-2 words)
        
        Content:
        {text}
        
        Return your analysis in JSON format with the following structure:
        {{
            "category": "Category name",
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "summary": "Brief summary of the content",
            "theme": "Primary theme"
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
            
            # If theme is missing, derive it from keywords
            if "theme" not in result and "keywords" in result and result["keywords"]:
                result["theme"] = result["keywords"][0]
            
            return result
        except Exception as e:
            print(f"AI analysis exception: {e}")
            raise Exception(f"AI analysis failed: {str(e)}")
            
    def find_similar_documents(self, target_doc, document_list, max_results=5):
        """
        Find documents similar to the target document
        
        Args:
            target_doc: Target document info dictionary (must contain 'keywords', 'category', and/or 'theme')
            document_list: List of document info dictionaries to compare against
            max_results: Maximum number of similar documents to return
            
        Returns:
            List of similar document dictionaries with similarity scores
        """
        if not target_doc or not document_list:
            return []
            
        # Extract key information from target document
        target_keywords = set(target_doc.get("keywords", []))
        target_category = target_doc.get("category", "").lower()
        target_theme = target_doc.get("theme", "").lower()
        
        # Calculate similarity scores for each document
        similarity_scores = []
        
        for doc in document_list:
            # Skip the target document itself
            if doc.get("filename") == target_doc.get("filename") and doc.get("path") == target_doc.get("path"):
                continue
                
            # Extract key information from comparison document
            doc_keywords = set(doc.get("keywords", []))
            doc_category = doc.get("category", "").lower()
            doc_theme = doc.get("theme", "").lower()
            
            # Initialize score
            score = 0
            
            # Calculate keyword overlap (0-5 points)
            if target_keywords and doc_keywords:
                keyword_overlap = len(target_keywords.intersection(doc_keywords))
                score += keyword_overlap * 2  # Each matching keyword is worth 2 points
            
            # Check category match (0-3 points)
            if target_category and doc_category and target_category == doc_category:
                score += 3
            
            # Check theme match (0-2 points)
            if target_theme and doc_theme and target_theme == doc_theme:
                score += 2
                
            # Only include documents with some similarity
            if score > 0:
                similarity_scores.append((doc, score))
        
        # Sort by similarity score (highest first)
        similarity_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return the top N similar documents with their scores
        result = []
        for doc, score in similarity_scores[:max_results]:
            # Add similarity score to the document dictionary
            doc_copy = doc.copy()
            doc_copy["similarity_score"] = score
            result.append(doc_copy)
            
        return result
        
    def find_related_content(self, target_doc, document_list, max_results=5):
        """
        Find documents related to the target document using AI comparison
        
        Args:
            target_doc: Target document info dictionary with content analysis
            document_list: List of document info dictionaries to compare against
            max_results: Maximum number of related documents to return
            
        Returns:
            Dictionary with relationship information and related documents
        """
        # First use the similarity scoring method
        similar_docs = self.find_similar_documents(target_doc, document_list, max_results)
        
        # If we have enough results, return them
        if len(similar_docs) >= max_results:
            return {
                "related_documents": similar_docs,
                "relationship_type": "content_similarity",
                "relationship_strength": "high" if similar_docs and similar_docs[0].get("similarity_score", 0) > 5 else "medium"
            }
            
        # If we have few or no results, use AI to find deeper relationships
        # Get the target document summary and key information
        target_summary = target_doc.get("summary", "")
        target_category = target_doc.get("category", "")
        target_filename = target_doc.get("filename", "")
        
        if not target_summary:
            return {
                "related_documents": similar_docs,
                "relationship_type": "keyword_match",
                "relationship_strength": "low"
            }
            
        # Prepare document info for AI analysis
        doc_info_list = []
        for doc in document_list:
            # Skip the target document itself
            if doc.get("filename") == target_filename:
                continue
                
            # Create a simple representation of each document
            doc_info = {
                "id": len(doc_info_list),
                "filename": doc.get("filename", ""),
                "category": doc.get("category", ""),
                "summary": doc.get("summary", ""),
                "keywords": doc.get("keywords", [])
            }
            doc_info_list.append(doc_info)
            
            # Limit to 10 documents for the AI prompt to avoid token limits
            if len(doc_info_list) >= 10:
                break
                
        # If no documents to compare, return simple results
        if not doc_info_list:
            return {
                "related_documents": similar_docs,
                "relationship_type": "keyword_match",
                "relationship_strength": "low"
            }
            
        try:
            # Format document info for the prompt
            docs_text = "\n\n".join([
                f"Document {doc['id']}: {doc['filename']}\n"
                f"Category: {doc['category']}\n"
                f"Keywords: {', '.join(doc['keywords'])}\n"
                f"Summary: {doc['summary']}"
                for doc in doc_info_list
            ])
            
            # Create the prompt for finding relationships
            prompt = f"""
            Analyze the relationship between the target document and the collection of other documents.
            Identify which documents are most closely related to the target and explain the relationship.

            Target Document: {target_filename}
            Category: {target_category}
            Summary: {target_summary}

            Other documents in the collection:
            {docs_text}

            Based on the content and themes, identify up to {max_results} documents from the collection
            that are most closely related to the target document. For each related document:
            1. The document ID
            2. The relationship strength (high, medium, or low)
            3. A brief explanation of the relationship (max 1 sentence)

            Return your analysis in JSON format:
            {{
                "related_documents": [
                    {{
                        "id": document_id,
                        "relationship_strength": "high|medium|low",
                        "relationship_explanation": "Brief explanation"
                    }},
                    ...
                ]
            }}

            Provide ONLY the JSON object, no other text.
            """
            
            # Call the AI to analyze relationships
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "max_output_tokens": 1000,
                    }
                )
                
                # Extract the response text
                if hasattr(response, 'text'):
                    response_text = response.text
                else:
                    response_text = response.candidates[0].content.parts[0].text
                
                # Clean up the response to ensure valid JSON
                response_text = response_text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                # Parse the JSON response
                relation_data = json.loads(response_text)
                
                # Map the document IDs back to the actual documents
                related_docs = []
                for rel_doc in relation_data.get("related_documents", []):
                    doc_id = rel_doc.get("id")
                    if 0 <= doc_id < len(doc_info_list):
                        # Get the filename from the doc_info_list
                        rel_filename = doc_info_list[doc_id]["filename"]
                        
                        # Find the full document info from document_list
                        for doc in document_list:
                            if doc.get("filename") == rel_filename:
                                # Add the relationship information to the document
                                doc_copy = doc.copy()
                                doc_copy["relationship_strength"] = rel_doc.get("relationship_strength", "medium")
                                doc_copy["relationship_explanation"] = rel_doc.get("relationship_explanation", "")
                                related_docs.append(doc_copy)
                                break
                
                return {
                    "related_documents": related_docs or similar_docs,  # Fallback to simple similarity if AI returns nothing
                    "relationship_type": "content_relationship",
                    "relationship_strength": "high"
                }
                
            except Exception as e:
                print(f"Error in AI relationship analysis: {str(e)}")
                # Fallback to simpler matching
                return {
                    "related_documents": similar_docs,
                    "relationship_type": "keyword_match",
                    "relationship_strength": "medium"
                }
                
        except Exception as e:
            print(f"Error finding related content: {str(e)}")
            return {
                "related_documents": similar_docs,
                "relationship_type": "basic_match",
                "relationship_strength": "low"
            }
