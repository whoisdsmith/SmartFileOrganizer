"""
AI Service Factory - Creates the appropriate AI analyzer based on configuration
"""

import os
import logging
from src.ai_analyzer import AIAnalyzer
from src.openai_analyzer import OpenAIAnalyzer

logger = logging.getLogger("AIDocumentOrganizer")

class AIServiceFactory:
    """
    Factory class to create the appropriate AI service based on configuration.
    Supports both Google Gemini and OpenAI models.
    """
    
    @staticmethod
    def create_analyzer(ai_service_type=None, settings_manager=None):
        """
        Create an AI analyzer instance based on the provided service type or configuration.
        
        Args:
            ai_service_type: String specifying which AI service to use ('google' or 'openai')
                             If None, will use settings or environment variables
            settings_manager: Optional SettingsManager instance to retrieve configuration
        
        Returns:
            An instance of AIAnalyzer or OpenAIAnalyzer
        """
        # Initialize API keys
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        
        # If no specific service type is provided, check settings or environment
        if ai_service_type is None:
            # First check if we have a settings manager
            if settings_manager:
                ai_service_type = settings_manager.get_setting("ai_service.service_type", "").lower()
                
                # If API keys are not in environment, check settings
                if not openai_api_key and settings_manager.get_setting("ai_service.openai_api_key"):
                    openai_api_key = settings_manager.get_setting("ai_service.openai_api_key")
                    os.environ["OPENAI_API_KEY"] = openai_api_key
                
                if not google_api_key and settings_manager.get_setting("ai_service.google_api_key"):
                    google_api_key = settings_manager.get_setting("ai_service.google_api_key")
                    os.environ["GOOGLE_API_KEY"] = google_api_key
            
            # If still not set, check environment variable
            if not ai_service_type:
                ai_service_type = os.environ.get("AI_SERVICE_TYPE", "").lower()
        else:
            ai_service_type = ai_service_type.lower()
        
        # Decide which service to use based on config and available keys
        if ai_service_type == "openai" and openai_api_key:
            logger.info("Using OpenAI for document analysis")
            return OpenAIAnalyzer()
        elif ai_service_type == "google" and google_api_key:
            logger.info("Using Google Gemini for document analysis")
            return AIAnalyzer()
        else:
            # Default logic: Use what's available
            if google_api_key:
                logger.info("Using Google Gemini for document analysis (default)")
                return AIAnalyzer()
            elif openai_api_key:
                logger.info("Using OpenAI for document analysis (default)")
                return OpenAIAnalyzer()
            else:
                # No keys available, use Google as default but it will show warnings
                logger.warning("No API keys found. Using Google Gemini (will show warnings)")
                return AIAnalyzer()