import os
import io
import logging
import tempfile
from pathlib import Path
from PIL import Image
import requests
import json
import base64
from typing import Dict, List, Tuple, Optional, Union

logger = logging.getLogger("AIDocumentOrganizer")


class ImageAnalyzer:
    """
    Class for analyzing images, extracting features, and generating thumbnails
    """

    def __init__(self, api_key=None, vision_api_provider=None):
        """
        Initialize the ImageAnalyzer

        Args:
            api_key: Optional API key for vision services
            vision_api_provider: Optional provider name ('google', 'azure', etc.)
        """
        self.api_key = api_key
        self.vision_api_provider = vision_api_provider
        self.thumbnail_size = (200, 200)  # Default thumbnail size

    def analyze_image(self, image_path: str) -> Dict:
        """
        Analyze an image and return its properties and features

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with image analysis results
        """
        results = {}

        try:
            # Basic image properties
            with Image.open(image_path) as img:
                results['dimensions'] = img.size
                results['format'] = img.format
                results['mode'] = img.mode
                results['has_transparency'] = self._has_transparency(img)
                results['is_animated'] = self._is_animated(img)

                # Generate color palette
                results['dominant_colors'] = self._extract_dominant_colors(img)

                # Generate thumbnail path
                thumbnail_path = self._generate_thumbnail(image_path, img)
                if thumbnail_path:
                    results['thumbnail_path'] = thumbnail_path

            # If vision API is configured, analyze image content
            if self.api_key and self.vision_api_provider:
                vision_results = self._analyze_with_vision_api(image_path)
                if vision_results:
                    results.update(vision_results)

        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {str(e)}")
            results['error'] = str(e)

        return results

    def _has_transparency(self, img: Image.Image) -> bool:
        """
        Check if the image has transparency

        Args:
            img: PIL Image object

        Returns:
            True if the image has transparency, False otherwise
        """
        if img.mode == 'RGBA':
            return True
        if img.mode == 'P':
            return 'transparency' in img.info
        return False

    def _is_animated(self, img: Image.Image) -> bool:
        """
        Check if the image is animated (GIF)

        Args:
            img: PIL Image object

        Returns:
            True if the image is animated, False otherwise
        """
        try:
            return hasattr(img, 'is_animated') and img.is_animated
        except:
            return False

    def _extract_dominant_colors(self, img: Image.Image, num_colors: int = 5) -> List[Tuple[int, int, int]]:
        """
        Extract dominant colors from the image

        Args:
            img: PIL Image object
            num_colors: Number of dominant colors to extract

        Returns:
            List of RGB color tuples
        """
        try:
            # Resize image for faster processing
            img_small = img.copy()
            img_small.thumbnail((100, 100))

            # Convert to RGB if needed
            if img_small.mode != 'RGB':
                img_small = img_small.convert('RGB')

            # Quantize to get dominant colors
            quantized = img_small.quantize(colors=num_colors)
            palette = quantized.getpalette()

            # Extract RGB values from palette
            colors = []
            for i in range(num_colors):
                if i*3+2 < len(palette):
                    colors.append(
                        (palette[i*3], palette[i*3+1], palette[i*3+2]))

            return colors
        except Exception as e:
            logger.warning(f"Error extracting dominant colors: {str(e)}")
            return []

    def _generate_thumbnail(self, image_path: str, img: Optional[Image.Image] = None,
                            size: Tuple[int, int] = None) -> Optional[str]:
        """
        Generate a thumbnail for the image

        Args:
            image_path: Path to the original image
            img: Optional PIL Image object (to avoid reopening)
            size: Optional custom thumbnail size

        Returns:
            Path to the generated thumbnail or None if failed
        """
        if size is None:
            size = self.thumbnail_size

        try:
            # Create thumbnails directory if it doesn't exist
            thumbnails_dir = os.path.join(os.path.dirname(
                os.path.dirname(image_path)), '.thumbnails')
            os.makedirs(thumbnails_dir, exist_ok=True)

            # Generate thumbnail filename
            base_name = os.path.basename(image_path)
            thumbnail_name = f"thumb_{base_name}"
            if not thumbnail_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                thumbnail_name += '.jpg'
            thumbnail_path = os.path.join(thumbnails_dir, thumbnail_name)

            # Generate thumbnail
            if img is None:
                img = Image.open(image_path)

            # Create a copy to avoid modifying the original
            thumb = img.copy()
            thumb.thumbnail(size)

            # Convert to RGB if needed (for saving as JPEG)
            if thumb.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', thumb.size, (255, 255, 255))
                background.paste(thumb, mask=thumb.split()[
                                 3] if thumb.mode == 'RGBA' else None)
                thumb = background

            # Save thumbnail
            thumb.save(thumbnail_path, 'JPEG', quality=85)
            return thumbnail_path

        except Exception as e:
            logger.warning(
                f"Error generating thumbnail for {image_path}: {str(e)}")
            return None

    def _analyze_with_vision_api(self, image_path: str) -> Dict:
        """
        Analyze image using a vision API service

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with vision API analysis results
        """
        results = {}

        if not self.api_key or not self.vision_api_provider:
            return results

        try:
            if self.vision_api_provider.lower() == 'google':
                results = self._analyze_with_google_vision(image_path)
            elif self.vision_api_provider.lower() == 'azure':
                results = self._analyze_with_azure_vision(image_path)
            # Add more providers as needed
        except Exception as e:
            logger.error(f"Error with vision API analysis: {str(e)}")
            results['vision_api_error'] = str(e)

        return results

    def _analyze_with_google_vision(self, image_path: str) -> Dict:
        """
        Analyze image using Google Vision API

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with Google Vision API results
        """
        # This is a placeholder implementation
        # In a real implementation, you would use the Google Vision API client

        results = {
            'vision_api': 'google',
            'labels': [],
            'objects': [],
            'faces': [],
            'text': '',
            'safe_search': {},
            'web_entities': []
        }

        # Placeholder for actual API implementation
        logger.info(
            f"Google Vision API analysis would be performed on {image_path}")

        return results

    def _analyze_with_azure_vision(self, image_path: str) -> Dict:
        """
        Analyze image using Azure Computer Vision API

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with Azure Vision API results
        """
        # This is a placeholder implementation
        # In a real implementation, you would use the Azure Vision API client

        results = {
            'vision_api': 'azure',
            'tags': [],
            'objects': [],
            'faces': [],
            'text': '',
            'adult_content': {},
            'categories': []
        }

        # Placeholder for actual API implementation
        logger.info(
            f"Azure Vision API analysis would be performed on {image_path}")

        return results

    def set_thumbnail_size(self, width: int, height: int):
        """
        Set the default thumbnail size

        Args:
            width: Thumbnail width in pixels
            height: Thumbnail height in pixels
        """
        self.thumbnail_size = (width, height)

    def set_vision_api(self, provider: str, api_key: str):
        """
        Set the vision API provider and key

        Args:
            provider: Vision API provider name ('google', 'azure', etc.)
            api_key: API key for the vision service
        """
        self.vision_api_provider = provider
        self.api_key = api_key
