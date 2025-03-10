import os
import json
import google.generativeai as genai
import time
import random
import logging

logger = logging.getLogger("AIDocumentOrganizer")


class AIAnalyzer:
    """
    Class for analyzing document content using Google Gemini API
    """

    def __init__(self, settings_manager=None):
        # Get API key from environment variable or settings
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key and settings_manager:
            api_key = settings_manager.get_setting(
                "ai_service.google_api_key", "")
            if api_key:
                os.environ["GOOGLE_API_KEY"] = api_key

        if not api_key:
            logger.warning("GOOGLE_API_KEY environment variable not set.")

        # Configure the Gemini API
        genai.configure(api_key=api_key)

        # Rate limiting settings
        # More conservative limit (reduced from 60)
        self.requests_per_minute = 30
        if settings_manager:
            self.requests_per_minute = settings_manager.get_setting(
                "ai_service.requests_per_minute", 30)

        self.min_request_interval = 60.0 / \
            self.requests_per_minute  # seconds between requests
        self.last_request_time = 0
        self.max_retries = 5
        if settings_manager:
            self.max_retries = settings_manager.get_setting(
                "ai_service.max_retries", 5)

        self.base_delay = 2  # Base delay in seconds for exponential backoff
        self.settings_manager = settings_manager

        # Get available models
        try:
            self.available_models = [m.name for m in genai.list_models()]
            logger.info(f"Available Gemini models: {self.available_models}")

            # Get the selected model from settings if available
            selected_model = None
            if settings_manager:
                selected_model = settings_manager.get_selected_model("google")

            # Check if the selected model is available
            if selected_model and selected_model in self.available_models:
                model_name = selected_model
                logger.info(
                    f"Using selected model from settings: {model_name}")
            else:
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
                    if preferred in self.available_models:
                        model_name = preferred
                        break

                # If none of our preferred models are available, use the first model that has "gemini" in the name
                if not model_name:
                    for m in self.available_models:
                        if 'gemini' in m.lower():
                            model_name = m
                            break

                # If we still don't have a model, use the first available model
                if not model_name and self.available_models:
                    model_name = self.available_models[0]

                if not model_name:
                    raise ValueError("No suitable Gemini models available")

                # Save the selected model to settings
                if settings_manager and model_name:
                    settings_manager.set_selected_model("google", model_name)

            logger.info(f"Using model: {model_name}")
            self.model = genai.GenerativeModel(model_name)
            self.model_name = model_name
        except Exception as e:
            logger.error(f"Error getting Gemini models: {e}")
            # Fallback to a common model format if there's an error
            fallback_model = "models/gemini-1.5-pro"
            logger.warning(f"Falling back to {fallback_model} model")
            self.model = genai.GenerativeModel(fallback_model)
            self.model_name = fallback_model
            self.available_models = [fallback_model]

    def get_available_models(self):
        """
        Get list of available Gemini models

        Returns:
            List of model names
        """
        return self.available_models

    def set_model(self, model_name):
        """
        Set the model to use for analysis

        Args:
            model_name: Name of the model to use

        Returns:
            True if successful, False otherwise
        """
        try:
            if model_name in self.available_models:
                self.model = genai.GenerativeModel(model_name)
                self.model_name = model_name

                # Save to settings if available
                if self.settings_manager:
                    self.settings_manager.set_selected_model(
                        "google", model_name)

                logger.info(f"Switched to model: {model_name}")
                return True
            else:
                logger.warning(f"Model {model_name} not available")
                return False
        except Exception as e:
            logger.error(f"Error setting model: {e}")
            return False

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
        # Characters (Gemini can handle more text than OpenAI)
        max_text_length = 30000
        truncated_text = text[:max_text_length]
        if len(text) > max_text_length:
            truncated_text += f"\n\n[Content truncated. Original length: {len(text)} characters]"

        try:
            analysis = self._get_content_analysis(truncated_text, file_type)
            return analysis
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
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

        # Implement rate limiting and exponential backoff
        for attempt in range(self.max_retries):
            try:
                # Apply rate limiting
                self._apply_rate_limit()

                # Try the newer API format first
                try:
                    response = self.model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0.2,
                            "max_output_tokens": 800,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"First API attempt failed: {e}, trying alternative format")
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

                logger.info(f"AI response received: {response_text[:100]}...")

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
                error_message = str(e).lower()

                # Check if this is a rate limit error (429)
                if "429" in error_message or "resource exhausted" in error_message or "quota" in error_message:
                    if attempt < self.max_retries - 1:  # Don't sleep on the last attempt
                        # Calculate exponential backoff delay with jitter
                        delay = self.base_delay * \
                            (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"Rate limit exceeded (429). Retrying in {delay:.2f} seconds (attempt {attempt+1}/{self.max_retries})")
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Rate limit exceeded (429). Max retries reached.")
                        raise Exception(
                            "AI analysis failed: Rate limit exceeded (429)")
                else:
                    # For other errors, don't retry
                    logger.error(f"AI analysis exception: {e}")
                    raise Exception(f"AI analysis failed: {str(e)}")

        # If we get here, all retries failed
        raise Exception("AI analysis failed after multiple retries")

    def _apply_rate_limit(self):
        """Apply rate limiting to avoid 429 errors"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        # If we've made a request too recently, wait
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.debug(
                f"Rate limiting: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        # Update the last request time
        self.last_request_time = time.time()

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
                    # Each matching keyword is worth 2 points, max 6
                    keyword_points = min(6, keyword_overlap * 2)
                    score += keyword_points

                    # Record the factor for explanation
                    if keyword_overlap == 1:
                        relationship_factors.append(
                            f"shared keyword '{list(matching_keywords)[0]}'")
                    else:
                        relationship_factors.append(
                            f"{keyword_overlap} shared keywords")

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
            target_ext = os.path.splitext(target_filename)[
                1].lower() if target_filename else ""
            doc_ext = os.path.splitext(doc_filename)[
                1].lower() if doc_filename else ""
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
                similarity_scores.append(
                    (doc, score, relationship_explanation, relationship_strength))

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
        # First use the similarity scoring method which now includes relationship explanations
        similar_docs = self.find_similar_documents(
            target_doc, document_list, max_results)

        # Check if we have good quality matches (with high scores)
        high_quality_matches = sum(
            1 for doc in similar_docs if doc.get("similarity_score", 0) >= 5)

        # If we have enough high-quality results, return them
        if high_quality_matches >= min(2, max_results):
            return {
                "related_documents": similar_docs,
                "relationship_type": "content_similarity",
                "relationship_strength": "high" if similar_docs and similar_docs[0].get("similarity_score", 0) >= 6 else "medium"
            }

        # If we have some results but want to try for more specific relationships, use AI
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

        try:
            # Format document info for the prompt
            docs_text = "\n\n".join([
                f"Document {doc['id']}: {doc['filename']}\n"
                f"Category: {doc['category']}\n"
                f"Keywords: {doc['keywords']}\n"
                f"Summary: {doc['summary']}"
                for doc in doc_info_list
            ])

            # Create the prompt for finding relationships - enhanced to look for more specific relationships
            prompt = f"""
            Analyze the relationship between the target document and the collection of other documents.
            Look for contextual connections, complementary information, sequential relationships,
            and topical relevance beyond simple keyword matching.

            Target Document: {target_filename}
            Category: {target_category}
            Keywords: {target_keywords}
            Summary: {target_summary}

            Other documents in the collection:
            {docs_text}

            Based on deep content analysis, identify up to {max_results} documents from the collection
            that are most meaningfully related to the target document. Consider:
            - Documents that complement or extend the target's information
            - Documents that represent previous/next steps in a process
            - Documents that provide context or background for the target
            - Documents covering related aspects of the same topic

            For each related document:
            1. The document ID
            2. The relationship strength (high, medium, or low)
            3. The relationship type (e.g., "complementary", "prerequisite", "extension", "contextual", etc.)
            4. A specific explanation of how the documents relate (1-2 sentences)

            Return your analysis in JSON format:
            {{
                "related_documents": [
                    {{
                        "id": document_id,
                        "relationship_strength": "high|medium|low",
                        "relationship_type": "relationship type",
                        "relationship_explanation": "Specific explanation of the relationship"
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
                        "temperature": 0.4,  # Slightly higher temperature for more creative connections
                        "max_output_tokens": 1200,
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
                                doc_copy["relationship_strength"] = rel_doc.get(
                                    "relationship_strength", "medium")
                                doc_copy["relationship_type"] = rel_doc.get(
                                    "relationship_type", "related content")
                                doc_copy["relationship_explanation"] = rel_doc.get(
                                    "relationship_explanation", "")

                                # Convert relationship to a similarity score for consistency
                                rel_strength = doc_copy["relationship_strength"].lower(
                                )
                                doc_copy["similarity_score"] = 7 if rel_strength == "high" else 4 if rel_strength == "medium" else 2

                                related_docs.append(doc_copy)
                                break

                # Combine AI results with similarity results if needed
                if not related_docs:
                    return {
                        "related_documents": similar_docs,
                        "relationship_type": "keyword_similarity",
                        "relationship_strength": "medium" if similar_docs else "low"
                    }

                # If we have both types of results, prioritize higher quality matches
                combined_docs = []
                # First add high-quality AI-determined relationships
                for doc in related_docs:
                    if doc.get("relationship_strength") == "high":
                        combined_docs.append(doc)

                # Then add high-scoring similarity matches that aren't already included
                for doc in similar_docs:
                    if doc.get("similarity_score", 0) >= 5:
                        # Check if this document is already included
                        if not any(d.get("filename") == doc.get("filename") for d in combined_docs):
                            combined_docs.append(doc)

                # Fill in with remaining AI relationships
                for doc in related_docs:
                    if doc.get("relationship_strength") != "high":
                        if not any(d.get("filename") == doc.get("filename") for d in combined_docs):
                            combined_docs.append(doc)

                # Finally, add any remaining similarity matches
                for doc in similar_docs:
                    if doc.get("similarity_score", 0) < 5:
                        if not any(d.get("filename") == doc.get("filename") for d in combined_docs):
                            combined_docs.append(doc)

                # Limit to the requested number of results
                final_docs = combined_docs[:max_results]

                return {
                    "related_documents": final_docs,
                    "relationship_type": "content_relationship",
                    "relationship_strength": "high" if final_docs and (
                        final_docs[0].get("similarity_score", 0) >= 6 or
                        final_docs[0].get("relationship_strength") == "high"
                    ) else "medium"
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
