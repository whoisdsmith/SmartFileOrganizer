import os
import json
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

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
        self.model = "gpt-4-turbo-preview"  # Using the latest model
        print(f"Using OpenAI model: {self.model}")
    
    def analyze_content(self, text, file_type):
        """
        Analyze document content using OpenAI
        
        Args:
            text: The document text content
            file_type: The type of document (CSV, Excel, HTML, etc.)
            
        Returns:
            Dictionary with analysis results
        """
        # Truncate text if too long
        max_text_length = 20000  # Characters (more conservative limit for OpenAI)
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
            # Generate content with OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            # Extract the text response
            response_text = response.choices[0].message.content
            print(f"OpenAI response received: {response_text[:100]}...")
            
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
            print(f"OpenAI analysis exception: {e}")
            raise Exception(f"OpenAI analysis failed: {str(e)}")
    
    def find_similar_documents(self, target_doc, document_list, max_results=5):
        """
        Find documents similar to the target document
        
        Args:
            target_doc: Target document info dictionary (must contain 'keywords', 'category', and/or 'theme')
            document_list: List of document info dictionaries to compare against
            max_results: Maximum number of similar documents to return
            
        Returns:
            List of similar document dictionaries with similarity scores and relationship explanations
        """
        if not target_doc or not document_list:
            return []
            
        # Extract key information from target document
        target_keywords = set(target_doc.get("keywords", []))
        target_category = target_doc.get("category", "").lower()
        target_theme = target_doc.get("theme", "").lower()
        target_summary = target_doc.get("summary", "")
        target_filename = target_doc.get("filename", "")
        
        # Calculate similarity scores for each document
        similarity_scores = []
        
        for doc in document_list:
            # Skip the target document itself
            if doc.get("filename") == target_filename and doc.get("path") == target_doc.get("path"):
                continue
                
            # Extract key information from comparison document
            doc_keywords = set(doc.get("keywords", []))
            doc_category = doc.get("category", "").lower()
            doc_theme = doc.get("theme", "").lower()
            doc_filename = doc.get("filename", "")
            
            # Initialize score and relationship attributes
            score = 0
            relationship_factors = []
            
            # Calculate keyword overlap (0-6 points)
            if target_keywords and doc_keywords:
                matching_keywords = target_keywords.intersection(doc_keywords)
                keyword_overlap = len(matching_keywords)
                if keyword_overlap > 0:
                    keyword_points = min(6, keyword_overlap * 2)  # Each matching keyword is worth 2 points, max 6
                    score += keyword_points
                    
                    # Record the factor for explanation
                    if keyword_overlap == 1:
                        relationship_factors.append(f"shared keyword '{list(matching_keywords)[0]}'")
                    else:
                        relationship_factors.append(f"{keyword_overlap} shared keywords")
            
            # Check category match (0-3 points)
            if target_category and doc_category:
                if target_category == doc_category:
                    score += 3
                    relationship_factors.append("same category")
                elif target_category in doc_category or doc_category in target_category:
                    # Partial category match (e.g. "Finance" and "Finance Reports")
                    score += 1
                    relationship_factors.append("related category")
            
            # Check theme match (0-3 points)
            if target_theme and doc_theme:
                if target_theme == doc_theme:
                    score += 3
                    relationship_factors.append("same theme")
                elif target_theme in doc_theme or doc_theme in target_theme:
                    # Partial theme match
                    score += 1
                    relationship_factors.append("related theme")
            
            # Check file type similarity (0-2 points)
            target_ext = os.path.splitext(target_filename)[1].lower() if target_filename else ""
            doc_ext = os.path.splitext(doc_filename)[1].lower() if doc_filename else ""
            if target_ext and doc_ext and target_ext == doc_ext:
                score += 2
                relationship_factors.append(f"same file type ({target_ext})")
                
            # Generate relationship explanation
            relationship_explanation = ""
            if relationship_factors:
                relationship_explanation = f"Documents have {' and '.join(relationship_factors)}"
                
            # Determine relationship strength
            relationship_strength = "low"
            if score >= 6:
                relationship_strength = "high"
            elif score >= 3:
                relationship_strength = "medium"
                
            # Only include documents with some similarity
            if score > 0:
                similarity_scores.append((doc, score, relationship_explanation, relationship_strength))
        
        # Sort by similarity score (highest first)
        similarity_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return the top N similar documents with their scores and explanations
        result = []
        for doc, score, explanation, strength in similarity_scores[:max_results]:
            # Add similarity information to the document dictionary
            doc_copy = doc.copy()
            doc_copy["similarity_score"] = score
            doc_copy["relationship_explanation"] = explanation
            doc_copy["relationship_strength"] = strength
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
        # First use the similarity scoring method which includes relationship explanations
        similar_docs = self.find_similar_documents(target_doc, document_list, max_results)
        
        # Check if we have good quality matches (with high scores)
        high_quality_matches = sum(1 for doc in similar_docs if doc.get("similarity_score", 0) >= 5)
        
        # If we have enough high-quality results, return them
        if high_quality_matches >= min(2, max_results):
            return {
                "related_documents": similar_docs,
                "relationship_type": "content_similarity",
                "relationship_strength": "high" if similar_docs and similar_docs[0].get("similarity_score", 0) >= 6 else "medium"
            }
            
        # Get the target document summary and key information
        target_summary = target_doc.get("summary", "")
        target_category = target_doc.get("category", "")
        target_filename = target_doc.get("filename", "")
        target_keywords = target_doc.get("keywords", [])
        
        # Convert keywords to string if it's a list
        if isinstance(target_keywords, list):
            target_keywords = ", ".join(target_keywords)
        
        if not target_summary:
            return {
                "related_documents": similar_docs,
                "relationship_type": "keyword_match",
                "relationship_strength": "medium" if similar_docs else "low"
            }
            
        # Prepare document info for AI analysis - include more documents than needed
        # to give the AI more options to find meaningful relationships
        doc_info_list = []
        for doc in document_list:
            # Skip the target document itself
            if doc.get("filename") == target_filename:
                continue
                
            # Skip documents with no summary
            if not doc.get("summary"):
                continue
                
            # Create a simple representation of each document
            doc_info = {
                "id": len(doc_info_list),
                "filename": doc.get("filename", ""),
                "category": doc.get("category", ""),
                "summary": doc.get("summary", ""),
                "keywords": doc.get("keywords", [])
            }
            
            # Convert keywords to string if it's a list
            if isinstance(doc_info["keywords"], list):
                doc_info["keywords"] = ", ".join(doc_info["keywords"])
                
            doc_info_list.append(doc_info)
            
            # Limit to 15 documents for the AI prompt to avoid token limits
            # but still give enough options to find meaningful relationships
            if len(doc_info_list) >= 15:
                break
                
        # If no documents to compare, return simple results
        if not doc_info_list:
            return {
                "related_documents": similar_docs,
                "relationship_type": "keyword_match",
                "relationship_strength": "medium" if similar_docs else "low"
            }
            
        # Create a prompt for the AI to analyze document relationships
        prompt = f"""
        I have a main document and several other documents. I need to identify which documents are most closely related to the main document and what type of relationship they have.

        Main Document:
        - Filename: {target_filename}
        - Category: {target_category}
        - Keywords: {target_keywords}
        - Summary: {target_summary}

        Other Documents:
        {json.dumps(doc_info_list, indent=2)}

        For each relationship, assign one of these relationship types:
        1. "prerequisite" - Content that should be understood before the main document
        2. "sequential" - Content that follows as the next step after the main document
        3. "contextual" - Content that provides supporting information for the main document
        4. "extension" - Content that builds upon or extends the concepts in the main document

        Identify the TOP {max_results} most closely related documents and describe their relationship to the main document.
        For each document, provide:
        1. The document ID
        2. The relationship strength (high, medium, or low)
        3. The relationship type (prerequisite, sequential, contextual, or extension)
        4. A brief explanation of why they are related

        Return only a JSON array of relationships in this format:
        [
            {{
                "id": document_id,
                "relationship_strength": "high|medium|low",
                "relationship_type": "relationship type",
                "relationship_explanation": "Specific explanation of the relationship"
            }},
            ...
        ]
        """
        
        try:
            # Generate content with OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # Extract the text response
            response_text = response.choices[0].message.content
            print(f"OpenAI relationship response received")
            
            try:
                # Parse the JSON response
                relationships = json.loads(response_text)
                
                # Response could be wrapped in an outer object or be a direct array
                if isinstance(relationships, dict):
                    if "relationships" in relationships:
                        relationships = relationships["relationships"]
                    elif len(relationships) == 1 and isinstance(next(iter(relationships.values())), list):
                        # Handle case where response is like {"results": [...]}
                        relationships = next(iter(relationships.values()))
                
                # Ensure we have a list of relationships
                if not isinstance(relationships, list):
                    print(f"Unexpected relationship format: {type(relationships)}")
                    relationships = []
                
                # Normalize the results
                related_docs = []
                for rel_doc in relationships:
                    if "id" not in rel_doc:
                        continue
                        
                    # Find the document by ID
                    doc_id = rel_doc["id"]
                    if isinstance(doc_id, str) and doc_id.isdigit():
                        doc_id = int(doc_id)
                        
                    doc = None
                    for d in doc_info_list:
                        if d["id"] == doc_id:
                            # Find the actual document in our document list
                            for original_doc in document_list:
                                if original_doc.get("filename") == d["filename"]:
                                    doc = original_doc
                                    break
                            break
                    
                    if doc:
                        # Add the relationship information to the document
                        doc_copy = doc.copy()
                        doc_copy["relationship_strength"] = rel_doc.get("relationship_strength", "medium")
                        doc_copy["relationship_type"] = rel_doc.get("relationship_type", "related content")
                        doc_copy["relationship_explanation"] = rel_doc.get("relationship_explanation", "")
                        
                        # Convert relationship to a similarity score for consistency
                        # with the similar_documents approach
                        strength_map = {"high": 7, "medium": 5, "low": 3}
                        doc_copy["similarity_score"] = strength_map.get(doc_copy["relationship_strength"], 4)
                        
                        related_docs.append(doc_copy)
                
                # If we didn't get any results, fall back to similarity scores
                if not related_docs:
                    return {
                        "related_documents": similar_docs,
                        "relationship_type": "keyword_similarity",
                        "relationship_strength": "medium" if similar_docs else "low"
                    }
                
                # Combine AI results with simple similarity results, prioritizing AI results
                final_docs = related_docs[:max_results]
                
                # If we need more results, add from simple similarity list
                # avoiding duplicates
                if len(final_docs) < max_results:
                    seen_filenames = set(doc.get("filename", "") for doc in final_docs)
                    for doc in similar_docs:
                        if doc.get("filename") not in seen_filenames:
                            final_docs.append(doc)
                            seen_filenames.add(doc.get("filename", ""))
                            if len(final_docs) >= max_results:
                                break
                
                return {
                    "related_documents": final_docs,
                    "relationship_type": "content_relationship",
                    "relationship_strength": "high" if final_docs and (
                        final_docs[0].get("similarity_score", 0) >= 6 or 
                        final_docs[0].get("relationship_strength") == "high"
                    ) else "medium"
                }
                
            except Exception as e:
                print(f"Error parsing OpenAI relationship response: {str(e)}")
                print(f"Response was: {response_text[:200]}...")
                
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